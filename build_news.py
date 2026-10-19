"""
The Daily Signal — automated news builder
Configure RSS_FEEDS as a JSON array of objects:
[{"category":"World","url":"https://...rss.xml"}, ...]
If RSS_FEEDS is not set, a small set of BBC RSS feeds is used.
"""
import os, json, re, hashlib, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
OUT.mkdir(exist_ok=True)
MAX_PER_FEED = int(os.getenv("MAX_PER_FEED", "8"))
SITE_NAME = "The Daily Signal"
TAGLINE = "The World. Clearly Delivered."
AI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

DEFAULT_FEEDS = [
    {"category": "World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"category": "India", "url": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml"},
    {"category": "Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"category": "Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"category": "Football", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml"},
    {"category": "Cricket", "url": "https://feeds.bbci.co.uk/sport/cricket/rss.xml"},
]

def get_feeds():
    raw = os.getenv("RSS_FEEDS", "").strip()
    if raw:
        try:
            feeds = json.loads(raw)
            if isinstance(feeds, list) and feeds:
                return feeds
        except json.JSONDecodeError:
            print("WARNING: RSS_FEEDS was not valid JSON; using default feeds.")
    return DEFAULT_FEEDS

def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def source_name(url):
    host = urlparse(url).netloc.lower().replace("www.", "")
    names = {"bbc.co.uk": "BBC News", "bbc.com": "BBC News", "apnews.com": "The Associated Press"}
    return next((v for k, v in names.items() if host.endswith(k)), host or "Original source")

def safe_id(url, title):
    return hashlib.sha256((url + "|" + title).encode("utf-8")).hexdigest()[:14]

def ai_summary(title, description, category, source):
    # If no API key is configured, use a clearly attributed short feed summary.
    # The pipeline still runs, but summaries will not be AI-generated.
    if not AI_API_KEY:
        fallback = description or "Open the original report for the full story and latest updates."
        return fallback[:650], "Feed summary"
    prompt = (
        "Write a concise, neutral news brief in original wording based only on the supplied title "
        "and feed description. Do not add facts, speculate, or claim independent verification. "
        "Use 2 short paragraphs, maximum 120 words total. If the description lacks detail, say "
        "that readers should consult the original source. Do not reproduce distinctive phrasing. "
        "Return only the brief.\n\n"
        f"Category: {category}\nSource: {source}\nTitle: {title}\nFeed description: {description}"
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2, "max_tokens": 220},
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        result = data["choices"][0]["message"]["content"].strip()
        return result[:1400], f"AI-assisted summary ({AI_MODEL})"
    except Exception as exc:
        print(f"AI summary failed; using feed description: {exc}")
        return (description or "Open the original report for the full story.")[:650], "Feed summary (AI unavailable)"

def fetch_stories():
    stories, seen = [], set()
    for feed_cfg in get_feeds():
        url = feed_cfg.get("url", "").strip()
        category = feed_cfg.get("category", "News").strip()
        if not url:
            continue
        print(f"Fetching {category}: {url}")
        try:
            feed = feedparser.parse(url)
            if getattr(feed, "bozo", False) and not feed.entries:
                print(f"WARNING: Feed could not be parsed: {url}")
                continue
            for entry in feed.entries[:MAX_PER_FEED]:
                title = clean_text(entry.get("title", ""))
                link = entry.get("link", "").strip()
                description = clean_text(entry.get("summary", "") or entry.get("description", ""))
                if not title or not link or link in seen:
                    continue
                seen.add(link)
                source = source_name(link)
                published = clean_text(entry.get("published", "") or entry.get("updated", ""))
                summary, method = ai_summary(title, description, category, source)
                stories.append({
                    "id": safe_id(link, title), "category": category, "title": title,
                    "url": link, "description": description, "summary": summary,
                    "source": source, "published": published, "method": method,
                })
        except Exception as exc:
            print(f"WARNING: feed failed {url}: {exc}")
    # Newest feed items first; preserve feed ordering when dates cannot be parsed.
    return stories

def esc(s):
    return html.escape(str(s or ""), quote=True)

def page_shell(title, body, current_date):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="The Daily Signal — clear, responsible news summaries linked to original reporting.">
<title>{esc(title)} | The Daily Signal</title>
<style>
:root{{--ink:#17191d;--muted:#666d78;--paper:#f6f5f2;--red:#d82732;--navy:#172235;--line:#e6e4df}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 Arial,sans-serif}}
.top{{background:var(--navy);color:#fff;padding:8px 5%;font-size:12px;display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}}
header{{text-align:center;background:#fff;padding:26px 5% 18px;border-bottom:1px solid var(--line)}}
.brand{{font:900 clamp(32px,5vw,52px)/1 Georgia,serif;letter-spacing:-1.5px}}.brand span{{color:var(--red)}}
.tag{{font-size:11px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin:10px 0 0}}
nav{{display:flex;justify-content:center;gap:4px;flex-wrap:wrap;background:#fff;border-bottom:3px solid var(--red);padding:8px}}
nav a{{padding:8px 12px;font-size:12px;text-transform:uppercase;font-weight:800;text-decoration:none}}nav a:hover{{color:var(--red)}}
main{{width:min(1120px,92%);margin:24px auto}}.notice{{padding:12px 14px;background:#fff6e5;border:1px solid #efd8a7;font-size:12px;color:#644c20;margin-bottom:20px}}
h1{{font:900 clamp(28px,4vw,42px)/1.15 Georgia,serif;margin:8px 0 16px}}.section{{border-bottom:2px solid var(--ink);padding-bottom:8px;margin:24px 0 16px;display:flex;justify-content:space-between;gap:10px;align-items:center}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}.card{{background:#fff;border:1px solid var(--line);padding:18px;min-width:0}}
.cat{{color:var(--red);font-weight:900;font-size:11px;letter-spacing:1px;text-transform:uppercase}}
.card h2{{font:700 22px/1.2 Georgia,serif;margin:9px 0}}.card p{{font-size:13px;color:var(--muted)}}.meta{{font-size:11px;color:#81858d}}
a.read{{color:var(--red);font-size:12px;font-weight:900;text-decoration:none;display:inline-block;margin-top:10px}}
.article{{background:#fff;border:1px solid var(--line);padding:clamp(20px,5vw,46px)}}.article .summary{{font-size:17px;line-height:1.8;max-width:780px;white-space:pre-line}}
.sourcebox{{border-top:1px solid var(--line);padding-top:16px;margin-top:25px;font-size:13px;color:var(--muted)}}footer{{background:#111820;color:#aab2bc;padding:25px 5%;font-size:12px;margin-top:36px}}footer strong{{color:#fff}}
@media(max-width:760px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:500px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<div class="top"><span>{esc(current_date)}</span><span>INDEPENDENT • CLEAR • RESPONSIBLE</span></div>
<header><div class="brand">THE DAILY <span>SIGNAL</span></div><p class="tag">{esc(TAGLINE)}</p></header>
<nav><a href="index.html">Top Stories</a><a href="index.html#World">World</a><a href="index.html#India">India</a><a href="index.html#Football">Football</a><a href="index.html#Cricket">Cricket</a><a href="index.html#Technology">Technology</a><a href="index.html#Business">Business</a></nav>
<main>{body}</main>
<footer><strong>THE DAILY SIGNAL</strong><br>The World. Clearly Delivered.<br>Summaries are automatically generated from linked feeds and may contain errors or omissions. Open the original publisher's report for full context and updates. Publisher names and links are provided for attribution. This site is not affiliated with the listed publishers.</footer>
</body></html>"""

def build_site(stories):
    now = datetime.now(timezone.utc).astimezone()
    current_date = now.strftime("%A, %d %B %Y · %H:%M %Z")
    cards = []
    # Save a small manifest for debugging / later integrations.
    (OUT / "articles").mkdir(exist_ok=True)
    for s in stories:
        article_path = OUT / "articles" / f"{s['id']}.html"
        body = f"""<article class="article"><div class="cat">{esc(s['category'])} · {esc(s['source'])}</div>
<h1>{esc(s['title'])}</h1><p class="meta">Feed date: {esc(s['published'] or 'Not provided')} · Generated: {esc(current_date)}</p>
<div class="summary">{esc(s['summary'])}</div>
<div class="sourcebox"><strong>Original reporting:</strong><br><a class="read" href="{esc(s['url'])}" target="_blank" rel="noopener noreferrer">Read the original report at {esc(s['source'])} ↗</a>
<p>Summary method: {esc(s['method'])}. This is an automated summary, not a substitute for the original article. Please check the source for corrections or newer information.</p></div></article>"""
        article_path.write_text(page_shell(s["title"], body, current_date), encoding="utf-8")
        cards.append(f"""<article class="card" id="{esc(s['category'])}"><div class="cat">{esc(s['category'])} · {esc(s['source'])}</div>
<h2>{esc(s['title'])}</h2><p>{esc(s['summary'][:260])}</p><div class="meta">{esc(s['published'] or 'Recent feed item')}</div>
<a class="read" href="articles/{esc(s['id'])}.html">READ SUMMARY →</a></article>""")
    if cards:
        listing = '<div class="grid">' + "\n".join(cards) + '</div>'
    else:
        listing = '<div class="card"><h2>No stories could be loaded</h2><p>Check feed URLs in the workflow settings and run the workflow again.</p></div>'
    body = f"""<div class="notice"><strong>Automation notice:</strong> Stories are collected from RSS feeds on a schedule. Summaries may be AI-assisted if an API key is configured. This is an automated edition; verify important details with the original source.</div>
<div class="section"><h1>Latest Reports</h1><span class="cat">Auto-updated edition</span></div>{listing}"""
    (OUT / "index.html").write_text(page_shell("Latest Reports", body, current_date), encoding="utf-8")
    (OUT / "articles.json").write_text(json.dumps({"generated_at": current_date, "count": len(stories), "articles": stories}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Built site with {len(stories)} story summaries.")

if __name__ == "__main__":
    build_site(fetch_stories())

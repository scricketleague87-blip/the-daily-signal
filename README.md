# The Daily Signal — Automated News Website Starter

This starter automatically collects items from RSS feeds, builds individual article-summary pages, and deploys the static site to GitHub Pages on a schedule (every four hours) after the first setup.

## What it does
- Collects headlines and summaries from configured RSS feeds.
- Creates a homepage and a page per story, with links to the original publisher.
- Removes duplicate source URLs within a run.
- Deploys the refreshed website using GitHub Actions + GitHub Pages.
- If `OPENAI_API_KEY` is configured, requests a short, neutral summary based only on the feed title/description. If not, it uses the feed description and labels it as a feed summary.

## Important limitations
- Automated summaries can be wrong or incomplete. This starter publishes without human approval because it is intended to demonstrate the requested fully automatic workflow. For a real newsroom, consider adding review for sensitive, breaking, medical, financial, election, conflict, or casualty reports.
- RSS feeds may fail, change format, limit excerpts, or have terms of use. Respect each publisher's RSS terms and link to the original report. Do not republish full articles, publisher photos, or copied text without permission.
- AI API usage may cost money. GitHub Actions and hosting limits can change. Check each provider's current terms, age rules, and usage limits.
- The code is a starter, not a guarantee of factual accuracy, legal compliance, or uninterrupted uptime.

## Setup overview (Android-friendly, but easiest with a trusted adult helping)
1. Create a GitHub account/repository. Because you're 14, involve a parent/guardian if a service's age rules, account management, or payment requirements call for it.
2. Upload the files in this ZIP to the repository, preserving folder names.
3. In repository Settings → Pages, choose GitHub Actions as the build/deployment source.
4. Go to Actions and run **Update The Daily Signal** once manually. The scheduled run is every four hours (UTC).
5. To enable AI summaries, add an `OPENAI_API_KEY` repository secret under Settings → Secrets and variables → Actions → Secrets. Never paste your key into website files, a public repository, or a chat. You can leave it unset; then the pipeline uses feed descriptions.
6. Optional: add repository variable `OPENAI_MODEL` (for example `gpt-4.1-mini`, if available to your API account).
7. Optional: set repository variable `RSS_FEEDS` to a JSON array, e.g.
   [{"category":"World","url":"https://feeds.bbci.co.uk/news/world/rss.xml"},{"category":"Football","url":"https://feeds.bbci.co.uk/sport/football/rss.xml"}]
   Leave unset to use the defaults in `scripts/build_news.py`.
8. After the first successful workflow, open the Pages URL shown in the deployment step.

## Edit categories and feeds
Edit `DEFAULT_FEEDS` in `scripts/build_news.py`, or set the `RSS_FEEDS` repository variable. Use feed URLs that publishers explicitly provide for reuse, and check their current terms.

## Before calling it a real newsroom
- Verify source feed rights and attribution rules.
- Add a corrections/contact process and an editorial policy.
- Add monitoring for broken feeds, failed deployments, duplicates and misleading summaries.
- Avoid unattended publishing of high-stakes claims without review.
- Add persistent history / deduplication across runs if you need to prevent old stories from returning. This starter only deduplicates within each run.

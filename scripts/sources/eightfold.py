"""Generic Eightfold.ai fetcher, driven by companies.json.

Best-effort: this is the least reliable of the five ATS platforms. The
query-param API pattern the page itself references (`/api/apply/v2/jobs?
domain=...`) returned "Not authorized" during research even with a matching
Referer header, which suggests the real page does some session/token
handshake before calling it. Documented here rather than silently guessing:
if this stops returning results for all three companies (Microsoft, Netflix,
Qualcomm), it needs re-investigation with an actual browser, not another
curl variant. Kept isolated so its failure doesn't affect other sources.
"""

from . import common

URL = "https://{subdomain}.eightfold.ai/api/apply/v2/jobs?domain={domain}&start={start}&num=50"
PAGE_SIZE = 50
MAX_RESULTS = 200


def fetch_company(company, subdomain, domain):
    entries = []
    start = 0
    while start < MAX_RESULTS:
        data = common.fetch_json(
            URL.format(subdomain=subdomain, domain=domain, start=start),
            headers={"Referer": f"https://{subdomain}.eightfold.ai/careers"},
        )
        postings = data.get("positions", [])
        if not postings:
            break
        for job in postings:
            title = job.get("name", "")
            if not common.is_internship_title(title):
                continue
            location = job.get("location") or ""
            entries.append({
                "company": company,
                "title": title,
                "url": job.get("canonicalPositionUrl"),
                "locations": [location] if location else [],
                "date_posted": None,
                "source": f"{company} (Eightfold)",
            })
        start += PAGE_SIZE
        common.polite_delay()
    return entries

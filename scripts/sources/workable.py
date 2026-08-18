"""Generic Workable widget fetcher, driven by companies.json.

https://apply.workable.com/api/v1/widget/accounts/{account}
"""

from . import common

URL = "https://apply.workable.com/api/v1/widget/accounts/{account}"


def fetch_company(company, account):
    data = common.fetch_json(URL.format(account=account))
    entries = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if not common.is_internship_title(title):
            continue
        location = ", ".join(p for p in (job.get("city"), job.get("country")) if p)
        entries.append({
            "company": company,
            "title": title,
            "url": job.get("url"),
            "locations": [location] if location else [],
            "date_posted": job.get("published_on"),
            "source": f"{company} (Workable)",
        })
    return entries

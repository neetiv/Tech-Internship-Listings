"""Generic Lever job-board fetcher, driven by companies.json.

Public documented API: https://api.lever.co/v0/postings/{company}?mode=json
"""

import datetime

from . import common

URL = "https://api.lever.co/v0/postings/{company}?mode=json"


def fetch_company(company, slug):
    postings = common.fetch_json(URL.format(company=slug))
    entries = []
    for job in postings:
        title = job.get("text", "")
        if not common.is_internship_title(title):
            continue
        categories = job.get("categories", {}) or {}
        location = categories.get("location", "")
        created_ms = job.get("createdAt")
        date_posted = (
            datetime.datetime.fromtimestamp(created_ms / 1000, tz=datetime.timezone.utc).isoformat()
            if created_ms else None
        )
        entries.append({
            "company": company,
            "title": title,
            "url": job.get("hostedUrl"),
            "locations": [location] if location else [],
            "date_posted": date_posted,
            "source": f"{company} (Lever)",
        })
    return entries

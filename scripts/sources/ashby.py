"""Generic Ashby job-board fetcher, driven by companies.json.

Public documented API: https://api.ashbyhq.com/posting-api/job-board/{board}
"""

from . import common

URL = "https://api.ashbyhq.com/posting-api/job-board/{board}"


def fetch_company(company, board):
    data = common.fetch_json(URL.format(board=board))
    entries = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if not job.get("isListed", True) or not common.is_internship_title(title):
            continue
        entries.append({
            "company": company,
            "title": title,
            "url": job.get("jobUrl"),
            "locations": [job["location"]] if job.get("location") else [],
            "date_posted": job.get("publishedAt") or None,
            "source": f"{company} (Ashby)",
        })
    return entries

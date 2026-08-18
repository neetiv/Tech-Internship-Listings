"""Generic Greenhouse job-board fetcher, driven by companies.json.

Public documented API: https://boards-api.greenhouse.io/v1/boards/{token}/jobs
"""

from . import common

URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=false"


def fetch_company(company, token):
    data = common.fetch_json(URL.format(token=token))
    entries = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if not common.is_internship_title(title):
            continue
        entries.append({
            "company": company,
            "title": title,
            "url": job.get("absolute_url"),
            "locations": [job["location"]["name"]] if job.get("location", {}).get("name") else [],
            "date_posted": job.get("first_published") or job.get("updated_at") or None,
            "source": f"{company} (Greenhouse)",
        })
    return entries

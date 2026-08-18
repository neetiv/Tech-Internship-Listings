"""Generic Workday job-board fetcher, driven by companies.json.

Undocumented but unauthenticated JSON endpoint the site itself uses:
POST https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
"""

from . import common

PAGE_SIZE = 20
MAX_RESULTS = 200  # safety cap so one huge tenant can't blow up the run


def fetch_company(company, tenant, site, host="wd5"):
    base = f"https://{tenant}.{host}.myworkdayjobs.com"
    url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    entries = []
    offset = 0
    while offset < MAX_RESULTS:
        data = common.fetch_json(
            url,
            method="POST",
            data={"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": "intern"},
        )
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for job in postings:
            title = job.get("title", "")
            if not common.is_internship_title(title):
                continue
            path = job.get("externalPath", "")
            entries.append({
                "company": company,
                "title": title,
                "url": f"{base}/{site}{path}",
                "locations": [job["locationsText"]] if job.get("locationsText") else [],
                "date_posted": common.parse_workday_posted(job.get("postedOn")),
                "source": f"{company} (Workday)",
            })
        offset += PAGE_SIZE
        if offset >= data.get("total", 0):
            break
        common.polite_delay()
    return entries

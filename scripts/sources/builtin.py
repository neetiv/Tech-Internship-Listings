"""Built In Seattle: paginated listing JSON-LD -> per-job JSON-LD.

Listing pages embed an HTML-entity-escaped <script type="application/ld&#x2B;json">
block with a schema.org ItemList (title + url per job, ~10-12/page). Each individual
job page then has a full JobPosting block (datePosted, employmentType, jobLocation)
plus a BreadcrumbList that reliably names the hiring company.
"""

import html as htmlmod
import json
import re

from . import common

BASE = "https://www.builtinseattle.com"
LD_JSON_RE = re.compile(r'<script type="application/ld&#x2B;json">(.*?)</script>', re.S)
MAX_PAGES = 8


def _ld_json_graph(page_html):
    m = LD_JSON_RE.search(page_html)
    if not m:
        return []
    data = json.loads(htmlmod.unescape(m.group(1)))
    return data.get("@graph", [])


def _listing_job_urls():
    urls = []
    for page in range(1, MAX_PAGES + 1):
        html = common.fetch(f"{BASE}/jobs/internship?page={page}")
        item_list = next((n for n in _ld_json_graph(html) if n.get("@type") == "ItemList"), None)
        items = item_list.get("itemListElement", []) if item_list else []
        if not items:
            break
        urls.extend(item["url"] for item in items if item.get("url"))
        common.polite_delay(1.5)
    return urls


def _fetch_job(url):
    html = common.fetch(url)
    graph = _ld_json_graph(html)
    posting = next((n for n in graph if n.get("@type") == "JobPosting"), None)
    if not posting:
        return None
    breadcrumb = next((n for n in graph if n.get("@type") == "BreadcrumbList"), None)
    company = common.as_dict(posting.get("hiringOrganization")).get("name")
    if not company and breadcrumb:
        items = breadcrumb.get("itemListElement", [])
        if items:
            company = common.as_dict(items[0]).get("name")

    address = common.as_dict(common.as_dict(posting.get("jobLocation")).get("address"))
    location = ", ".join(
        p for p in (address.get("addressLocality"), address.get("addressRegion")) if p
    ) or address.get("addressCountry", "")

    title = posting.get("title", "")
    is_intern = posting.get("employmentType") == "INTERN" or common.is_internship_title(title)
    if not is_intern:
        return None

    return {
        "company": company or "",
        "title": title,
        "url": url,
        "locations": [location] if location else [],
        "date_posted": posting.get("datePosted"),
        "source": "Built In Seattle",
    }


def fetch_all():
    entries = []
    for url in _listing_job_urls():
        try:
            entry = _fetch_job(url)
        except Exception as e:  # noqa: BLE001 - one bad job page shouldn't kill the run
            print(f"[warn] builtin job page failed ({url}): {e}")
            entry = None
        if entry:
            entries.append(entry)
        common.polite_delay(1.5)
    return entries

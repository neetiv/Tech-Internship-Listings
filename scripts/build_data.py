#!/usr/bin/env python3
"""Fetch internship listings from every source, normalize, dedupe, and write:
  - docs/data.json   (full list, consumed by the site)
  - README.md        (most recent ~50 rows, between marker comments)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sources import ashby, builtin, common, eightfold, github_repos, greenhouse, lever, workable, workday  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JSON_PATH = os.path.join(REPO_ROOT, "docs", "data.json")
README_PATH = os.path.join(REPO_ROOT, "README.md")
README_TABLE_ROWS = 50

# Prefer company-direct on conflict (closest to source of truth), then Built In, then tracker repos.
ORIGIN_PRIORITY = {"company-direct": 0, "builtin": 1, "tracker": 2}

PLATFORM_FETCHERS = {
    "greenhouse": lambda c: greenhouse.fetch_company(c["company"], c["token"]),
    "ashby": lambda c: ashby.fetch_company(c["company"], c["board"]),
    "lever": lambda c: lever.fetch_company(c["company"], c["slug"]),
    "workday": lambda c: workday.fetch_company(c["company"], c["tenant"], c["site"], c.get("host", "wd5")),
    "eightfold": lambda c: eightfold.fetch_company(c["company"], c["subdomain"], c["domain"]),
    "workable": lambda c: workable.fetch_company(c["company"], c["account"]),
}


def fetch_company_direct():
    with open(os.path.join(os.path.dirname(__file__), "companies.json")) as f:
        companies = json.load(f)

    entries = []
    for cfg in companies:
        fetcher = PLATFORM_FETCHERS[cfg["platform"]]
        label = f"{cfg['company']} ({cfg['platform']})"
        result = common.safe_source(lambda cfg=cfg: fetcher(cfg), label)
        print(f"[info] {label}: {len(result)} internship postings")
        entries.extend(result)
        common.polite_delay()
    return entries


def normalize(entry, origin):
    return {
        "company": (entry.get("company") or "").strip(),
        "title": (entry.get("title") or "").strip(),
        "url": entry.get("url"),
        "locations": entry.get("locations") or [],
        "date_posted": entry.get("date_posted"),
        "source": entry.get("source", ""),
        "origin": origin,
    }


def dedupe(entries):
    best = {}
    for e in entries:
        if not e["url"]:
            continue
        key = common.normalize_url(e["url"])
        existing = best.get(key)
        if existing is None or ORIGIN_PRIORITY[e["origin"]] < ORIGIN_PRIORITY[existing["origin"]]:
            best[key] = e
    return list(best.values())


def recover_truncated_titles(entries):
    """Some tracker repos truncate long titles (ending in '...') in their own
    README tables. Re-fetch just those job pages to recover the real title."""
    fixed = 0
    for e in entries:
        title = e["title"].rstrip()
        if not (title.endswith("...") or title.endswith("…")) or not e["url"]:
            continue
        full_title = common.recover_full_title(e["url"])
        if full_title:
            e["title"] = full_title
            fixed += 1
        common.polite_delay(0.2)
    print(f"[info] recovered {fixed} truncated titles")


def sort_key(entry):
    # Entries with no parseable date sort last, not first.
    return entry["date_posted"] or "0000-00-00"


def rewrite_readme(entries):
    with open(README_PATH, encoding="utf-8") as f:
        readme = f.read()

    lines = ["| Company | Role | Location | Source | Posted |", "|---|---|---|---|---|"]
    for e in entries[:README_TABLE_ROWS]:
        location = "; ".join(e["locations"]) or "—"
        lines.append(
            f"| {e['company']} | [{e['title']}]({e['url']}) | {location} | {e['source']} | {e['date_posted'] or '—'} |"
        )
    table = "\n".join(lines)

    start_marker = "<!-- JOBS_TABLE_START -->"
    end_marker = "<!-- JOBS_TABLE_END -->"
    before = readme.split(start_marker, 1)[0]
    after = readme.split(end_marker, 1)[1]
    new_readme = f"{before}{start_marker}\n{table}\n{end_marker}{after}"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_readme)


def main():
    tracker_entries = [normalize(e, "tracker") for e in github_repos.fetch_all()]
    builtin_entries = [normalize(e, "builtin") for e in common.safe_source(builtin.fetch_all, "builtin")]
    direct_entries = [normalize(e, "company-direct") for e in fetch_company_direct()]

    all_entries = tracker_entries + builtin_entries + direct_entries
    deduped = dedupe(all_entries)
    recover_truncated_titles(deduped)
    deduped.sort(key=sort_key, reverse=True)

    os.makedirs(os.path.dirname(DATA_JSON_PATH), exist_ok=True)
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2)

    rewrite_readme(deduped)

    print(f"[info] wrote {len(deduped)} internships to docs/data.json "
          f"(from {len(all_entries)} raw, {len(all_entries) - len(deduped)} deduped away)")


if __name__ == "__main__":
    main()

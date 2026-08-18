"""Parsers for the four community tracker repos' README tables.

Each repo formats its table slightly differently (HTML <table> vs markdown
pipe tables, different column sets, different apply-link markup), so each
gets its own small row-mapper on top of two shared low-level extractors.
"""

import re

from . import common

RAW = "https://raw.githubusercontent.com/{repo}/{branch}/README.md"


def _fetch_readme(repo, branch):
    return common.fetch(RAW.format(repo=repo, branch=branch))


def _split_locations(text):
    parts = re.split(r"<br\s*/?>|</br>", text)
    return [common.strip_html(p).strip() for p in parts if common.strip_html(p).strip()]


def _pipe_table_rows(text, min_cells):
    """Yield cell-lists for every markdown pipe-table data row in `text`."""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        inner = line.strip("|")
        if set(inner.replace("|", "").strip()) <= set("-: "):
            continue  # separator row
        cells = [c.strip() for c in inner.split("|")]
        if len(cells) < min_cells:
            continue
        if cells[0].strip().lower() in ("company",):
            continue  # header row
        yield cells


def _between_markers(text, start_word, end_word):
    """Slice `text` to the region after the first line containing `start_word`
    and before the first line (after that point) containing `end_word`.
    Robust to markers embedded in longer boilerplate comment lines."""
    lines = text.splitlines()
    start_idx = next((i for i, l in enumerate(lines) if start_word in l), None)
    if start_idx is None:
        raise ValueError(f"marker {start_word!r} not found")
    end_idx = next(
        (i for i in range(start_idx + 1, len(lines)) if end_word in lines[i]), None
    )
    if end_idx is None:
        raise ValueError(f"marker {end_word!r} not found after {start_word!r}")
    return "\n".join(lines[start_idx + 1:end_idx])


def _html_table_rows(html):
    """Yield <td> cell-content-lists for every row in every <table> block."""
    for table in re.findall(r"<table>(.*?)</table>", html, re.S):
        for row in re.findall(r"<tr>(.*?)</tr>", table, re.S):
            cells = re.findall(r"<td>(.*?)</td>", row, re.S)
            if cells:
                yield cells


def parse_vanshb03():
    text = _fetch_readme("vanshb03/Summer2027-Internships", "main")
    marker = _between_markers(text, "TABLE_START", "TABLE_END")
    entries = []
    for cells in _pipe_table_rows(marker, min_cells=5):
        company, role, location, apply_cell, posted = cells[:5]
        url = common.extract_link(apply_cell)
        if not url:
            continue
        entries.append({
            "company": common.strip_html(company),
            "title": common.strip_html(role),
            "url": url,
            "locations": _split_locations(location),
            "date_posted": common.parse_posted_date(common.strip_html(posted)),
            "source": "vanshb03/Summer2027-Internships",
        })
    return entries


def parse_speedyapply():
    text = _fetch_readme("speedyapply/2027-SWE-College-Jobs", "main")
    entries = []
    for start, end in (
        ("TABLE_FAANG_START", "TABLE_FAANG_END"),
        ("TABLE_QUANT_START", "TABLE_QUANT_END"),
        ("TABLE_START", "TABLE_END"),
    ):
        try:
            section = _between_markers(text, start, end)
        except ValueError:
            continue
        for cells in _pipe_table_rows(section, min_cells=6):
            company_cell, position, location, _salary, apply_cell, age = cells[:6]
            url = common.extract_link(apply_cell)
            if not url:
                continue
            entries.append({
                "company": common.strip_html(company_cell),
                "title": common.strip_html(position),
                "url": url,
                "locations": _split_locations(location),
                "date_posted": common.parse_posted_date(common.strip_html(age)),
                "source": "speedyapply/2027-SWE-College-Jobs",
            })
    return entries


def parse_zapplyjobs():
    text = _fetch_readme("zapplyjobs/Internships-2027", "main")
    entries = []
    for cells in _pipe_table_rows(text, min_cells=6):
        if cells[0].strip().lower().startswith("**company"):
            continue
        company, role, location, posted, _visa, apply_cell = cells[:6]
        url = common.extract_link(apply_cell)
        if not url:
            continue
        entries.append({
            "company": common.strip_html(company).strip("*").strip(),
            "title": common.strip_html(role),
            "url": url,
            "locations": _split_locations(location),
            "date_posted": common.parse_posted_date(common.strip_html(posted)),
            "source": "zapplyjobs/Internships-2027",
        })
    return entries


def parse_simplifyjobs():
    text = _fetch_readme("SimplifyJobs/Summer2027-Internships", "dev")
    try:
        section = text.split("TABLE_START", 1)[1].split("TABLE_END", 1)[0]
    except IndexError:
        return []
    entries = []
    for cells in _html_table_rows(section):
        if len(cells) < 5:
            continue
        company_cell, role, location, apply_cell, age = cells[:5]
        url = common.extract_link(apply_cell)
        if not url:
            continue
        entries.append({
            "company": common.strip_html(company_cell),
            "title": common.strip_html(role),
            "url": url,
            "locations": _split_locations(location),
            "date_posted": common.parse_posted_date(common.strip_html(age)),
            "source": "SimplifyJobs/Summer2027-Internships",
        })
    return entries


def fetch_all():
    entries = []
    for name, fn in (
        ("vanshb03", parse_vanshb03),
        ("speedyapply", parse_speedyapply),
        ("zapplyjobs", parse_zapplyjobs),
        ("simplifyjobs", parse_simplifyjobs),
    ):
        result = common.safe_source(fn, name)
        print(f"[info] {name}: {len(result)} rows")
        entries.extend(result)
    return entries

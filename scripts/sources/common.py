"""Shared helpers used by every source fetcher."""

import datetime
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = (
    "TechInternshipListings-Bot/1.0 "
    "(+https://github.com/neetiv/Tech-Internship-Listings)"
)

# Word-boundary match so "international" / "internal" don't false-positive.
_INTERN_RE = re.compile(r"\bintern(ship)?s?\b", re.IGNORECASE)


def is_internship_title(title):
    if not title:
        return False
    return bool(_INTERN_RE.search(title))


def fetch(url, method="GET", data=None, headers=None, timeout=20, retries=3):
    """Fetch a URL, returning decoded text. Raises on non-2xx (after retrying 429s)."""
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                wait = float(e.headers.get("Retry-After", 2 * (attempt + 1)))
                time.sleep(wait)
                continue
            raise


def fetch_json(url, method="GET", data=None, headers=None, timeout=20):
    return json.loads(fetch(url, method=method, data=data, headers=headers, timeout=timeout))


def polite_delay(seconds=0.3):
    time.sleep(seconds)


def as_dict(value):
    """Some JSON-LD producers emit a single object where schema.org allows a
    list of them (e.g. hiringOrganization, jobLocation). Normalize to a dict."""
    if isinstance(value, list):
        return value[0] if value else {}
    return value or {}


def strip_html(text):
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


_HTML_HREF_RE = re.compile(r'href="([^"]+)"')
_MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")


def first_html_href(fragment):
    m = _HTML_HREF_RE.search(fragment or "")
    return m.group(1) if m else None


def first_markdown_link(fragment):
    m = _MD_LINK_RE.search(fragment or "")
    return m.group(1) if m else None


def extract_link(fragment):
    """Apply-cell link, trying raw HTML anchors then markdown link syntax."""
    return first_html_href(fragment) or first_markdown_link(fragment)


_MONTH_ABBR = {
    m: i
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1
    )
}
_RELATIVE_RE = re.compile(r"^(\d+)\s*(mo|d|h|m)$", re.IGNORECASE)
_ABS_DATE_RE = re.compile(r"^([A-Za-z]{3})\s+(\d{1,2})$")


def parse_posted_date(text, now=None):
    """Best-effort parse of a tracker repo's 'age'/'posted' cell into an ISO date.

    Handles: "0d"/"3d" (age in days), "13m"/"2h"/"1mo" (relative), "Aug 06"
    (absolute, year inferred). Returns None if the format isn't recognized —
    callers should treat None as "unknown, sort last" rather than guessing.
    """
    if not text:
        return None
    text = text.strip()
    now = now or datetime.datetime.now(datetime.timezone.utc)

    m = _RELATIVE_RE.match(text)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        delta = {
            "m": datetime.timedelta(minutes=n),
            "h": datetime.timedelta(hours=n),
            "d": datetime.timedelta(days=n),
            "mo": datetime.timedelta(days=n * 30),
        }[unit]
        return (now - delta).date().isoformat()

    m = _ABS_DATE_RE.match(text)
    if m:
        month = _MONTH_ABBR.get(m.group(1).capitalize())
        day = int(m.group(2))
        if month:
            year = now.year
            try:
                candidate = datetime.date(year, month, day)
            except ValueError:
                return None
            if candidate > now.date():
                candidate = datetime.date(year - 1, month, day)
            return candidate.isoformat()

    return None


_WORKDAY_DAYS_RE = re.compile(r"Posted\s+(\d+)\+?\s+Days?\s+Ago", re.IGNORECASE)


def parse_workday_posted(text, now=None):
    """Workday's postedOn is fuzzy text: 'Posted Today', 'Posted Yesterday',
    'Posted N Days Ago', 'Posted 30+ Days Ago'. Approximate to a date."""
    if not text:
        return None
    now = now or datetime.datetime.now(datetime.timezone.utc)
    text = text.strip()
    if text.lower() == "posted today":
        return now.date().isoformat()
    if text.lower() == "posted yesterday":
        return (now - datetime.timedelta(days=1)).date().isoformat()
    m = _WORKDAY_DAYS_RE.match(text)
    if m:
        return (now - datetime.timedelta(days=int(m.group(1)))).date().isoformat()
    return None


_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "ref", "jr_id"}


def normalize_url(url):
    """Strip known referral-tracking query params (utm_*, ref, jr_id) so the
    same underlying posting dedupes across sources, while leaving
    ATS-specific job-id params (gh_jid, etc.) intact."""
    if not url:
        return url
    parts = urllib.parse.urlsplit(url)
    kept = [
        (k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS
    ]
    query = urllib.parse.urlencode(kept)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


_TITLE_TAG_RE = re.compile(r"<title>([^<]*)</title>", re.I)
_H1_ITEMPROP_TITLE_RE = re.compile(r'<h1[^>]*itemprop="title"[^>]*>([^<]*)</h1>', re.I)


def recover_full_title(url):
    """Some tracker repos truncate long titles (ending in '...') when they
    generate their own README table. We have the real job URL, so re-fetch
    it and pull the untruncated title from the page itself. Best-effort:
    returns None on any failure so callers just keep the truncated original."""
    try:
        html = fetch(url, timeout=10, retries=1)
    except (urllib.error.URLError, TimeoutError):
        return None
    m = _H1_ITEMPROP_TITLE_RE.search(html)
    if m:
        return strip_html(m.group(1)).strip() or None
    m = _TITLE_TAG_RE.search(html)
    if m:
        return strip_html(m.group(1)).split("|")[0].strip() or None
    return None


def safe_source(fn, source_name, default=None):
    """Run a fetcher, catching+logging errors so one broken source doesn't kill the build."""
    try:
        return fn()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"[warn] source '{source_name}' failed: {e}")
        return default if default is not None else []

(function () {
  "use strict";

  var state = { jobs: [], search: "", company: "", location: "", term: "", postedWithin: "", sort: "date_desc" };

  var tbody = document.getElementById("jobs-body");
  var emptyState = document.getElementById("empty-state");
  var countEl = document.getElementById("result-count");
  var searchEl = document.getElementById("search");
  var companyEl = document.getElementById("company-filter");
  var locationEl = document.getElementById("location-filter");
  var termEl = document.getElementById("term-filter");
  var postedEl = document.getElementById("posted-filter");
  var sortEl = document.getElementById("sort-by");
  var lastUpdatedEl = document.getElementById("last-updated");

  // Dates are stored UTC-referenced in data.json (the site is built once,
  // by a script with no notion of who'll be viewing it). But every viewer
  // has their own local calendar day, and "today"/"3d ago" only makes
  // sense relative to THAT — so all day-math here uses the viewer's local
  // getters, not UTC ones. (Using UTC here was the bug that made postings
  // show as "tomorrow" for anyone west of UTC, especially late in the day.)
  function localDateString(dt) {
    var y = dt.getFullYear();
    var m = String(dt.getMonth() + 1).padStart(2, "0");
    var d = String(dt.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + d;
  }

  function daysAgo(dateStr) {
    if (!dateStr) return null;
    var posted = new Date(dateStr);
    if (isNaN(posted.getTime())) return null;
    var postedLocalDay = new Date(posted.getFullYear(), posted.getMonth(), posted.getDate()).getTime();
    var today = new Date();
    var todayLocalDay = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
    return Math.round((todayLocalDay - postedLocalDay) / 86400000);
  }

  function formatPosted(dateStr) {
    if (!dateStr) return "—";
    var dt = new Date(dateStr);
    if (isNaN(dt.getTime())) return "—";
    var d = daysAgo(dateStr);
    var rel = d <= 0 ? "today" : d === 1 ? "1d ago" : d + "d ago";
    var datePart = localDateString(dt);
    var hasTime = dateStr.indexOf("T") !== -1;
    if (!hasTime) return datePart + " · " + rel;
    var timePart = dt.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
    return datePart + " " + timePart + " · " + rel;
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function render() {
    var q = state.search.trim().toLowerCase();
    var filtered = state.jobs.filter(function (j) {
      if (state.company && j.company !== state.company) return false;
      if (state.location && j.locations.indexOf(state.location) === -1) return false;
      if (state.term && j.term !== state.term) return false;
      if (state.postedWithin !== "") {
        var d = daysAgo(j.date_posted);
        if (d === null || d > Number(state.postedWithin)) return false;
      }
      if (!q) return true;
      return (j.company + " " + j.title).toLowerCase().indexOf(q) !== -1;
    });

    filtered.sort(function (a, b) {
      if (state.sort === "company") return a.company.localeCompare(b.company);
      var ad = a.date_posted || "0000-00-00";
      var bd = b.date_posted || "0000-00-00";
      return state.sort === "date_asc" ? ad.localeCompare(bd) : bd.localeCompare(ad);
    });

    var display = filtered;

    tbody.innerHTML = display.map(function (j) {
      var locations = (j.locations || []).join("; ") || "—";
      return (
        "<tr>" +
        '<td class="company-cell truncate" title="' + escapeHtml(j.company) + '">' + escapeHtml(j.company) + "</td>" +
        '<td class="role-cell truncate" title="' + escapeHtml(j.title) + '">' + escapeHtml(j.title) + "</td>" +
        '<td class="location-cell truncate" title="' + escapeHtml(locations) + '">' + escapeHtml(locations) + "</td>" +
        '<td class="term-cell truncate">' + escapeHtml(j.term || "—") + "</td>" +
        '<td class="posted-cell truncate">' + escapeHtml(formatPosted(j.date_posted)) + "</td>" +
        '<td><a class="apply-btn" href="' + escapeHtml(j.url) + '" target="_blank" rel="noopener">apply →</a></td>' +
        "</tr>"
      );
    }).join("");

    emptyState.hidden = display.length !== 0;
    countEl.textContent = display.length + " / " + state.jobs.length + " internships";
  }

  function populateOptions(selectEl, values) {
    values.forEach(function (v) {
      var opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      selectEl.appendChild(opt);
    });
  }

  var SEASON_ORDER = { Spring: 0, Summer: 1, Fall: 2, Winter: 3 };

  function compareTerm(a, b) {
    var ap = a.split(" "), bp = b.split(" ");
    var ay = Number(ap[1]), by = Number(bp[1]);
    if (ay !== by) return ay - by;
    return SEASON_ORDER[ap[0]] - SEASON_ORDER[bp[0]];
  }

  function populateFilters(jobs) {
    var locationSet = new Set();
    var companySet = new Set();
    var termSet = new Set();
    jobs.forEach(function (j) {
      if (j.company) companySet.add(j.company);
      if (j.term) termSet.add(j.term);
      (j.locations || []).forEach(function (l) {
        if (l) locationSet.add(l);
      });
    });
    populateOptions(locationEl, Array.from(locationSet).sort());
    populateOptions(companyEl, Array.from(companySet).sort());
    populateOptions(termEl, Array.from(termSet).sort(compareTerm));
  }

  function setLastUpdated(jobs) {
    var newest = jobs.reduce(function (max, j) {
      return j.date_posted && j.date_posted > max ? j.date_posted : max;
    }, "");
    var dt = newest ? new Date(newest) : null;
    lastUpdatedEl.textContent = dt && !isNaN(dt.getTime())
      ? "most recent posting: " + localDateString(dt) + " · refreshed daily"
      : "refreshed daily";
  }

  function initTheme() {
    var saved = localStorage.getItem("theme");
    if (saved === "light") document.body.classList.add("light");
    document.getElementById("theme-toggle").addEventListener("click", function () {
      document.body.classList.toggle("light");
      localStorage.setItem("theme", document.body.classList.contains("light") ? "light" : "dark");
    });
  }

  function init() {
    initTheme();
    searchEl.addEventListener("input", function () {
      state.search = searchEl.value;
      render();
    });
    companyEl.addEventListener("change", function () {
      state.company = companyEl.value;
      render();
    });
    locationEl.addEventListener("change", function () {
      state.location = locationEl.value;
      render();
    });
    termEl.addEventListener("change", function () {
      state.term = termEl.value;
      render();
    });
    postedEl.addEventListener("change", function () {
      state.postedWithin = postedEl.value;
      render();
    });
    sortEl.addEventListener("change", function () {
      state.sort = sortEl.value;
      render();
    });

    // Bypass caching at every layer: data.json changes several times a day,
    // but a plain reload will otherwise happily reuse whatever the browser
    // cached (cache: "no-store" fixes that), and GitHub Pages' own CDN can
    // still serve an edge-cached copy on top of that for its own TTL window
    // — the timestamp query param forces a true cache-miss there too, since
    // it makes every request a different URL.
    fetch("data.json?t=" + Date.now(), { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (jobs) {
        state.jobs = jobs;
        populateFilters(jobs);
        setLastUpdated(jobs);
        render();
      })
      .catch(function (err) {
        tbody.innerHTML = "";
        emptyState.hidden = false;
        emptyState.textContent = "couldn't load listings — try refreshing";
        console.error(err);
      });
  }

  init();
})();

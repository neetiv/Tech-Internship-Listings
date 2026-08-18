(function () {
  "use strict";

  var state = { jobs: [], search: "", company: "", location: "", postedWithin: "", sort: "date_desc" };

  var tbody = document.getElementById("jobs-body");
  var emptyState = document.getElementById("empty-state");
  var countEl = document.getElementById("result-count");
  var searchEl = document.getElementById("search");
  var companyEl = document.getElementById("company-filter");
  var locationEl = document.getElementById("location-filter");
  var postedEl = document.getElementById("posted-filter");
  var sortEl = document.getElementById("sort-by");
  var lastUpdatedEl = document.getElementById("last-updated");

  function daysAgo(dateStr) {
    if (!dateStr) return null;
    var posted = new Date(dateStr);
    if (isNaN(posted.getTime())) return null;
    var postedUTCDay = Date.UTC(posted.getUTCFullYear(), posted.getUTCMonth(), posted.getUTCDate());
    var today = new Date();
    var utcToday = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
    return Math.round((utcToday - postedUTCDay) / 86400000);
  }

  function formatPosted(dateStr) {
    if (!dateStr) return "—";
    var d = daysAgo(dateStr);
    if (d === null) return "—";
    var rel = d <= 0 ? "today" : d === 1 ? "1d ago" : d + "d ago";
    var hasTime = dateStr.indexOf("T") !== -1;
    if (!hasTime) return dateStr + " · " + rel;
    var dt = new Date(dateStr);
    var datePart = dt.toISOString().slice(0, 10);
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

  function populateFilters(jobs) {
    var locationSet = new Set();
    var companySet = new Set();
    jobs.forEach(function (j) {
      if (j.company) companySet.add(j.company);
      (j.locations || []).forEach(function (l) {
        if (l) locationSet.add(l);
      });
    });
    populateOptions(locationEl, Array.from(locationSet).sort());
    populateOptions(companyEl, Array.from(companySet).sort());
  }

  function setLastUpdated(jobs) {
    var newest = jobs.reduce(function (max, j) {
      return j.date_posted && j.date_posted > max ? j.date_posted : max;
    }, "");
    lastUpdatedEl.textContent = newest
      ? "most recent posting: " + newest + " · refreshed daily"
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
    postedEl.addEventListener("change", function () {
      state.postedWithin = postedEl.value;
      render();
    });
    sortEl.addEventListener("change", function () {
      state.sort = sortEl.value;
      render();
    });

    fetch("data.json")
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

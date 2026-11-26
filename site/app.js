"use strict";
/* Amsterdam Agenda – plain JS, no build step. Reads data/events.json + data/status.json. */

const TZ = "Europe/Amsterdam";
const CATS = { film: "Film", music: "Muziek", club: "Club", talk: "Talk", theatre: "Theater", jazz: "Jazz", food: "Eten", other: "Overig" };
const STATUS = { sold_out: "Uitverkocht", cancelled: "Afgelast", moved: "Verplaatst" };
const WEEKS_AHEAD = 6;

// ---------------------------------------------------------------- storage (never trust it)
const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem("agenda." + key); return v ? JSON.parse(v) : fallback; }
    catch { return fallback; }
  },
  set(key, value) { try { localStorage.setItem("agenda." + key, JSON.stringify(value)); } catch { /* private mode */ } },
};

const URL_VIEWS = { lijst: "list", week: "week", kaart: "map" };
const urlParams = new URLSearchParams(location.search);

const state = {
  events: [],
  view: URL_VIEWS[urlParams.get("view")] || store.get("view", "list"),
  quick: "all",
  cats: new Set(store.get("cats", [])),          // empty = all categories
  hiddenVenues: new Set(store.get("hiddenVenues", [])),
  favEvents: new Set(store.get("favEvents", [])),
  favVenues: new Set(store.get("favVenues", [])),
  search: "",
  clubMode: store.get("clubMode", "on"),          // on | only | off
  freeOnly: store.get("freeOnly", false),
  design: "standaard",
  weekOffset: 0,
  mapDay: /^\d{4}-\d{2}-\d{2}$/.test(urlParams.get("dag") || "") ? urlParams.get("dag") : null,  // null = today
  mapRange: "day",                                  // day | weekend | week
};

// ---------------------------------------------------------------- date helpers (all in Amsterdam time)
const fmtKey = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
const fmtTime = new Intl.DateTimeFormat("nl-NL", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
const fmtDay = new Intl.DateTimeFormat("nl-NL", { timeZone: "UTC", weekday: "long", day: "numeric", month: "long" });
const fmtShort = new Intl.DateTimeFormat("nl-NL", { timeZone: "UTC", weekday: "short", day: "numeric", month: "short" });
const fmtWeekday = new Intl.DateTimeFormat("nl-NL", { timeZone: "UTC", weekday: "short" });
const fmtStamp = new Intl.DateTimeFormat("nl-NL", { timeZone: TZ, weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

const dayKey = (d) => fmtKey.format(d);                       // "2026-11-23"
const keyToDate = (k) => new Date(k + "T12:00:00Z");           // noon UTC: safe for weekday/format
const addDays = (k, n) => { const d = keyToDate(k); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const weekday = (k) => (keyToDate(k).getUTCDay() + 6) % 7;     // 0 = maandag
const mondayOf = (k) => addDays(k, -weekday(k));

function todayKey() { return dayKey(new Date()); }

function quickRange(quick) {
  const t = todayKey();
  const wd = weekday(t);
  if (quick === "today") return [t, t];
  if (quick === "weekend") return wd >= 4 ? [t, addDays(t, 6 - wd)] : [addDays(t, 4 - wd), addDays(t, 6 - wd)];
  if (quick === "week") return wd === 6 ? [t, addDays(t, 7)] : [t, addDays(t, 6 - wd)];
  return null;
}

function relLabel(k) {
  const t = todayKey();
  if (k === t) return "Vandaag";
  if (k === addDays(t, 1)) return "Morgen";
  return "";
}

// ---------------------------------------------------------------- filtering
function isFav(ev) { return state.favEvents.has(ev.id) || state.favVenues.has(ev.venue); }

function matches(ev, { ignoreQuick = false } = {}) {
  if (state.freeOnly && !ev.free) return false;
  if (state.clubMode === "off" && ev.category === "club") return false;
  if (state.clubMode === "only" && ev.category !== "club") return false;
  if (state.cats.size && !state.cats.has(ev.category)) return false;
  if (state.hiddenVenues.has(ev.venue)) return false;
  if (state.search) {
    const hay = (ev.title + " " + ev.venue + " " + (ev.subtitle || "")).toLowerCase();
    if (!state.search.split(/\s+/).every((w) => hay.includes(w))) return false;
  }
  if (!ignoreQuick) {
    if (state.quick === "fav" && !isFav(ev)) return false;
    const range = quickRange(state.quick);
    if (range) {
      // only themed periods span days; a club night ending at 04:00 belongs to its start day
      const first = ev._day, last = ev.kind === "series" ? (ev._endDay || ev._day) : ev._day;
      if (last < range[0] || first > range[1]) return false;
    }
  }
  return true;
}

// ---------------------------------------------------------------- rendering
const $ = (sel) => document.querySelector(sel);
const tpl = $("#event-tpl");

function starButton(btn, ev) {
  const on = state.favEvents.has(ev.id);
  btn.textContent = on ? "★" : "☆";
  btn.setAttribute("aria-pressed", String(on));
  btn.setAttribute("aria-label", on ? "Verwijder uit favorieten" : "Markeer als favoriet");
  btn.dataset.id = ev.id;
}

function eventNode(ev) {
  const node = tpl.content.firstElementChild.cloneNode(true);
  node.dataset.cat = ev.category;
  const time = node.querySelector(".ev-time");
  time.textContent = ev.all_day ? "–" : fmtTime.format(ev._start);
  if (ev.all_day) time.title = "Tijd onbekend";
  time.dateTime = ev.start;
  const a = node.querySelector(".ev-title");
  a.textContent = ev.title;
  a.href = ev.url;
  node.querySelector(".ev-venue").textContent = ev.venue + (state.favVenues.has(ev.venue) ? " ★" : "");
  node.querySelector(".ev-cat").textContent = CATS[ev.category] || ev.category;
  const st = node.querySelector(".ev-status");
  st.textContent = STATUS[ev.status] || "";
  st.className = "ev-status " + (ev.status || "");
  const price = ev.free && !/gratis|free|donat/i.test(ev.price || "") ? (ev.price ? `${ev.price} (gratis/donatie)` : "gratis") : ev.price;
  node.querySelector(".ev-sub").textContent = [ev.subtitle, price].filter(Boolean).join(" · ");
  if (ev.status === "cancelled" || (!ev.all_day && ev._start < Date.now() - 3 * 3600e3)) node.classList.add("dim");
  starButton(node.querySelector(".star"), ev);
  const img = node.querySelector(".ev-img");
  if (state.design === "beeld") {
    if (ev.image) { img.src = ev.image; img.hidden = false; img.onerror = () => { img.hidden = true; node.classList.add("no-img"); }; }
    else node.classList.add("no-img");
  }
  return node;
}

function seriesCard(ev, text, label) {
  const a = document.createElement("a");
  a.className = "series-card";
  a.href = ev.url; a.target = "_blank"; a.rel = "noopener";
  a.dataset.cat = ev.category;
  if (label) {
    const l = document.createElement("span");
    l.className = "when";
    l.textContent = label;
    a.append(l);
  }
  const strong = document.createElement("strong");
  strong.textContent = ev.title;
  const small = document.createElement("small");
  small.textContent = text;
  const star = document.createElement("button");
  star.className = "star";
  starButton(star, ev);
  a.append(strong, small, star);
  return a;
}

function renderSeries() {
  const t = todayKey();
  const ignoreQuick = state.quick !== "fav";
  const running = state.events.filter((e) => e.kind === "series" && matches(e, { ignoreQuick })
    && e._day <= addDays(t, 14) && (e._endDay || e._day) >= t);
  const box = $("#series-list");
  box.replaceChildren();
  $("#series").hidden = running.length === 0;
  $("#series-count").textContent = running.length ? `${running.length} ${running.length === 1 ? "reeks" : "reeksen"}` : "";
  for (const ev of running) {
    const until = ev._endDay ? "t/m " + fmtShort.format(keyToDate(ev._endDay)) : "";
    const from = ev._day > t ? "vanaf " + fmtShort.format(keyToDate(ev._day)) + " " : "";
    box.append(seriesCard(ev, `${ev.venue} · ${from}${until}`));
  }
  const weekly = state.events.filter((e) => e.kind === "weekly" && matches(e, { ignoreQuick }));
  renderWeekly(weekly);
}

const DAY_NAMES = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"];

function renderWeekly(weekly) {
  const box = $("#weekly-list");
  box.replaceChildren();
  $("#weekly").hidden = weekly.length === 0;
  $("#weekly-count").textContent = weekly.length ? `${weekly.length} × per week` : "";
  const byDay = DAY_NAMES.map(() => []);
  for (const ev of weekly) {
    const w = parseWeekly(ev);
    for (const d of w.days) byDay[d].push({ ev, ...w });
  }
  const today = weekday(todayKey());
  byDay.forEach((items, d) => {
    if (!items.length) return;
    items.sort((a, b) => a.time.localeCompare(b.time) || a.ev.title.localeCompare(b.ev.title, "nl"));
    const group = document.createElement("div");
    group.className = "wk-day" + (d === today ? " today" : "");
    const h = document.createElement("h3");
    h.textContent = DAY_NAMES[d] + (d === today ? " · vandaag" : "");
    group.append(h);
    for (const { ev, time, rest } of items) {
      const row = document.createElement("a");
      row.className = "wk-row";
      row.href = ev.url; row.target = "_blank"; row.rel = "noopener";
      row.dataset.cat = ev.category;
      const t = document.createElement("b"); t.textContent = time;
      const body = document.createElement("span");
      const title = document.createElement("span"); title.className = "wk-title"; title.textContent = ev.title;
      const meta = document.createElement("small"); meta.textContent = [ev.venue, rest].filter(Boolean).join(" · ");
      body.append(title, meta);
      const star = document.createElement("button"); star.className = "star"; starButton(star, ev);
      row.append(t, body, star);
      group.append(row);
    }
    box.append(group);
  });
}

// "Elke wo, do, vr, za 12:00–14:00 · Café Gilde" → label "wo–za 12:00–14:00", rest "Café Gilde", firstDay 2
const DAYS = ["ma", "di", "wo", "do", "vr", "za", "zo"];
function parseWeekly(ev) {
  const m = /^Elke ([a-z, ]+?)\s+(\d{1,2}:\d{2}(?:[–-]\d{1,2}:\d{2})?)\s*(?:·\s*(.*))?$/.exec(ev.subtitle || "");
  if (!m) {
    const t = fmtTime.format(ev._start);
    return { days: [weekday(ev._day)], firstDay: weekday(ev._day), time: t, label: `${DAYS[weekday(ev._day)]} ${t}`, rest: ev.subtitle || "" };
  }
  const days = m[1].split(/,\s*/).map((d) => DAYS.indexOf(d.trim())).filter((d) => d >= 0).sort((a, b) => a - b);
  // compress consecutive days: [0,1,2,3,4,5] → "ma–za"; [4,5] → "vr, za"
  const parts = [];
  for (let i = 0; i < days.length; ) {
    let j = i;
    while (j + 1 < days.length && days[j + 1] === days[j] + 1) j++;
    parts.push(j - i >= 2 ? `${DAYS[days[i]]}–${DAYS[days[j]]}` : days.slice(i, j + 1).map((d) => DAYS[d]).join(", "));
    i = j + 1;
  }
  return { days, firstDay: days[0] ?? 7, time: m[2], label: `${parts.join(", ")} ${m[2]}`, rest: m[3] || "" };
}

function renderList() {
  const list = $("#list");
  const days = new Map();
  for (const ev of state.events) {
    if (ev.kind !== "event" && ev.kind !== undefined || !matches(ev)) continue;
    if (!days.has(ev._day)) days.set(ev._day, []);
    days.get(ev._day).push(ev);
  }
  const frag = document.createDocumentFragment();
  let count = 0;
  for (const [k, evs] of days) {
    const sec = document.createElement("section");
    sec.className = "day";
    sec.id = "d-" + k;
    const h = document.createElement("h2");
    const rel = relLabel(k);
    if (rel) { const r = document.createElement("span"); r.className = "rel"; r.textContent = rel; h.append(r); }
    const label = document.createElement("span");
    label.textContent = fmtDay.format(keyToDate(k));
    const n = document.createElement("span");
    n.className = "n"; n.textContent = evs.length;
    h.append(label, n);
    sec.append(h);
    for (const ev of evs) sec.append(eventNode(ev));
    frag.append(sec);
    count += evs.length;
  }
  list.replaceChildren(frag);
  renderDayStrip([...days.keys()]);
  if (!count) list.innerHTML = '<p class="empty">Geen events gevonden met deze filters.</p>';
  $("#summary").textContent = `${count} event${count === 1 ? "" : "s"}`;
}

function renderDayStrip(keys) {
  const strip = $("#daystrip");
  strip.replaceChildren();
  const t = todayKey();
  for (const k of keys.slice(0, 42)) {
    const b = document.createElement("button");
    const d = keyToDate(k);
    b.innerHTML = `<small>${k === t ? "vandaag" : fmtWeekday.format(d)}</small><b>${d.getUTCDate()}</b>`;
    b.addEventListener("click", () => {
      const sec = document.getElementById("d-" + k);
      if (!sec) return;
      const top = sec.getBoundingClientRect().top + window.scrollY - document.querySelector(".top").offsetHeight - 52;
      window.scrollTo({ top, behavior: "smooth" });
    });
    strip.append(b);
  }
}

function setDesign(name) {
  const ok = ["standaard", "poster", "compact", "beeld"];
  state.design = ok.includes(name) ? name : "standaard";
  document.documentElement.dataset.design = state.design;
  document.querySelectorAll(".design-pick button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.design === state.design)));
  store.set("design", state.design);
}

function renderWeek() {
  const t = todayKey();
  const monday = addDays(mondayOf(t), 7 * state.weekOffset);
  const sunday = addDays(monday, 6);
  $("#week-label").textContent = `${fmtShort.format(keyToDate(monday))} – ${fmtShort.format(keyToDate(sunday))}`;
  $("#prev-week").disabled = state.weekOffset <= 0;
  $("#next-week").disabled = state.weekOffset >= WEEKS_AHEAD - 1;
  const grid = $("#week-grid");
  grid.replaceChildren();
  let count = 0;
  for (let i = 0; i < 7; i++) {
    const k = addDays(monday, i);
    const col = document.createElement("div");
    col.className = "wday" + (k === t ? " today" : "");
    const h = document.createElement("h3");
    h.textContent = fmtShort.format(keyToDate(k));
    col.append(h);
    for (const ev of state.events) {
      if (ev._day !== k || (ev.kind && ev.kind !== "event") || !matches(ev, { ignoreQuick: state.quick !== "fav" })) continue;
      const a = document.createElement("a");
      a.className = "wev" + (isFav(ev) ? " fav" : "") + (ev.status === "cancelled" ? " dim" : "");
      a.dataset.cat = ev.category;
      a.href = ev.url; a.target = "_blank"; a.rel = "noopener";
      const b = document.createElement("b"); b.textContent = (ev.all_day ? "–" : fmtTime.format(ev._start)) + (STATUS[ev.status] ? " · " + STATUS[ev.status] : "");
      const ti = document.createElement("div"); ti.textContent = ev.title;
      const v = document.createElement("span"); v.textContent = ev.venue;
      a.append(b, ti, v);
      col.append(a);
      count++;
    }
    grid.append(col);
  }
  $("#summary").textContent = `${count} event${count === 1 ? "" : "s"} deze week`;
  const todayCol = grid.querySelector(".today");
  if (todayCol && grid.scrollWidth > grid.clientWidth) grid.scrollLeft = todayCol.offsetLeft - 16;
}

function renderVenues() {
  const counts = new Map();
  for (const ev of state.events) counts.set(ev.venue, (counts.get(ev.venue) || 0) + 1);
  const names = [...counts.keys()].sort((a, b) => a.localeCompare(b, "nl"));
  const ul = $("#venue-list");
  ul.replaceChildren();
  for (const name of names) {
    const li = document.createElement("li");
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = !state.hiddenVenues.has(name); cb.dataset.venue = name;
    const span = document.createElement("span"); span.textContent = name;
    const c = document.createElement("span"); c.className = "count"; c.textContent = counts.get(name);
    label.append(cb, span, c);
    const star = document.createElement("button");
    star.className = "star"; star.dataset.favVenue = name;
    const on = state.favVenues.has(name);
    star.textContent = on ? "★" : "☆";
    star.setAttribute("aria-pressed", String(on));
    star.setAttribute("aria-label", (on ? "Verwijder " : "Markeer ") + name + " als favoriete locatie");
    li.append(label, star);
    ul.append(li);
  }
  const hidden = names.filter((n) => state.hiddenVenues.has(n)).length;
  const btn = $("#venue-btn");
  btn.textContent = hidden ? `Locaties (${names.length - hidden}/${names.length})` : "Locaties";
  btn.classList.toggle("active", hidden > 0);
}

function renderCats() {
  const box = $("#cats");
  box.replaceChildren();
  for (const [key, label] of Object.entries(CATS)) {
    if (!state.events.some((e) => e.category === key)) continue;
    const b = document.createElement("button");
    b.dataset.cat = key;
    b.className = state.cats.has(key) ? "on" : "";
    b.setAttribute("aria-pressed", String(state.cats.has(key)));
    const dot = document.createElement("span"); dot.className = "dot"; dot.style.background = "var(--c)";
    b.append(dot, label);
    box.append(b);
  }
}

function render() {
  document.querySelectorAll(".view-toggle button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.view === state.view)));
  document.documentElement.dataset.view = state.view;
  document.querySelectorAll("#quick button").forEach((b) => b.classList.toggle("on", b.dataset.quick === activeQuick()));
  document.querySelectorAll(".club-mode button[data-club]").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.club === state.clubMode)));
  $("#free-btn").setAttribute("aria-pressed", String(state.freeOnly));
  $("#list").hidden = state.view !== "list";
  $("#week").hidden = state.view !== "week";
  $("#map-view").hidden = state.view !== "map";
  syncURL();
  if (state.view === "map") { renderMapView(); return; }
  renderSeries();
  if (state.view === "list") renderList(); else renderWeek();
}

// which period chip is lit: on the map the chips drive the map's day/range
function activeQuick() {
  if (state.view !== "map" || state.quick === "fav") return state.quick;
  if (state.mapRange !== "day") return state.mapRange;
  return (state.mapDay || todayKey()) === todayKey() ? "today" : "all";
}

function syncURL() {
  const p = new URLSearchParams(location.search);
  const name = Object.keys(URL_VIEWS).find((k) => URL_VIEWS[k] === state.view);
  if (state.view === "list") p.delete("view"); else p.set("view", name);
  if (state.view === "map" && state.mapRange === "day" && state.mapDay) p.set("dag", state.mapDay); else p.delete("dag");
  const qs = p.toString();
  try { history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash); } catch { /* file:// */ }
}

// ---------------------------------------------------------------- map view (Leaflet + map.js load on first use)
const CDN = "https://cdnjs.cloudflare.com/ajax/libs/";
const MAP_ASSETS = [
  ["css", CDN + "leaflet/1.9.4/leaflet.css", "sha512-Zcn6bjR/8RZbLEpLIeOwNtzREBAJnUKESxces60Mpoj+2okopSAcSUIUOseddDm0cxnGQzxIR7vJgsLZbdLE3w=="],
  ["css", CDN + "leaflet.markercluster/1.5.3/MarkerCluster.css", "sha512-mQ77VzAakzdpWdgfL/lM1ksNy89uFgibRQANsNneSTMD/bj0Y/8+94XMwYhnbzx8eki2hrbPpDm0vD0CiT2lcg=="],
  ["js", CDN + "leaflet/1.9.4/leaflet.js", "sha512-BwHfrr4c9kmRkLw6iXFdzcdWV/PGkVgiIyIWLLlTSXzWQzxuSg4DiQUCpauz/EWjgk5TYQqX/kvn9pG1NpYfqg=="],
  ["js", CDN + "leaflet.markercluster/1.5.3/leaflet.markercluster.js", "sha512-OFs3W4DIZ5ZkrDhBFtsCP6JXtMEDGmhl0QPlmWYBJay40TT1n3gt2Xuw8Pf/iezgW9CdabjkNChRqozl/YADmg=="],
  ["js", "map.js", null],
];
let mapReady = null;
function loadAsset([kind, url, sri]) {
  return new Promise((resolve, reject) => {
    const el = document.createElement(kind === "css" ? "link" : "script");
    if (kind === "css") { el.rel = "stylesheet"; el.href = url; } else { el.src = url; el.async = false; }
    if (sri) { el.integrity = sri; el.crossOrigin = "anonymous"; el.referrerPolicy = "no-referrer"; }
    el.onload = resolve; el.onerror = () => reject(new Error("kon " + url + " niet laden"));
    document.head.append(el);
  });
}
function renderMapView() {
  if (!mapReady) {
    // scripts in order (leaflet before markercluster before map.js), styles in parallel
    mapReady = Promise.all(MAP_ASSETS.filter((a) => a[0] === "css").map(loadAsset))
      .then(() => MAP_ASSETS.filter((a) => a[0] === "js").reduce((p, a) => p.then(() => loadAsset(a)), Promise.resolve()));
    mapReady.catch((err) => {
      console.error(err);
      $("#map").innerHTML = '<p class="map-loading">Kon de kaart niet laden. Probeer het later opnieuw.</p>';
      mapReady = null;
    });
  }
  mapReady.then(() => window.AgendaMap && window.AgendaMap.render()).catch(() => {});
}

function renderStatus(status, generated) {
  const tbody = $("#status-table tbody");
  tbody.replaceChildren();
  const entries = Object.values(status.venues || {}).sort((a, b) => a.name.localeCompare(b.name, "nl"));
  const failed = entries.filter((v) => v.error);
  const disabled = entries.filter((v) => v.disabled);
  for (const v of entries) {
    const tr = document.createElement("tr");
    if (v.error) { tr.className = "fail"; tr.title = v.error; }
    const name = document.createElement("td");
    const a = document.createElement("a"); a.href = v.url; a.textContent = v.name; a.target = "_blank"; a.rel = "noopener";
    a.style.color = "inherit"; a.style.fontWeight = "400";
    name.append(a);
    const upd = document.createElement("td");
    if (v.disabled) {
      upd.textContent = "uitgeschakeld" + (v.reason ? ` (${v.reason})` : "");
    } else {
      upd.textContent = (v.error ? "⚠ mislukt · laatst ok " : "") + (v.last_success ? fmtStamp.format(new Date(v.last_success)) : "nooit");
    }
    const n = document.createElement("td");
    n.textContent = v.disabled ? "–" : v.error ? (v.stale ? `${v.events} (oud)` : "–") : v.events;
    tr.append(name, upd, n);
    tbody.append(tr);
  }
  const when = generated ? "Bijgewerkt " + fmtStamp.format(new Date(generated)) : "";
  const active = entries.length - disabled.length;
  $("#status-summary").textContent = `${when} · ${active - failed.length}/${active} bronnen ok` +
    (failed.length ? ` · ⚠ mislukt: ${failed.map((f) => f.name).join(", ")}` : "");
}

// ---------------------------------------------------------------- events
function toggleFavEvent(id) {
  state.favEvents.has(id) ? state.favEvents.delete(id) : state.favEvents.add(id);
  store.set("favEvents", [...state.favEvents]);
  render();
}

function bind() {
  document.querySelector(".view-toggle").addEventListener("click", (e) => {
    const v = e.target.closest("button")?.dataset.view;
    if (!v) return;
    state.view = v; store.set("view", v); render();
  });
  $("#quick").addEventListener("click", (e) => {
    const q = e.target.closest("button")?.dataset.quick;
    if (!q) return;
    if (state.view === "map" && q !== "fav") {
      if (state.quick === "fav") state.quick = "all";
      if (q === "today") { state.mapRange = "day"; state.mapDay = null; }
      else if (q === "all") state.mapRange = "day";
      else state.mapRange = state.mapRange === q ? "day" : q;
      render();
      return;
    }
    state.quick = state.quick === q ? "all" : q;
    if (state.view === "week") state.weekOffset = 0;
    render();
  });
  $("#design-btn").addEventListener("click", () => {
    const panel = $("#design-panel");
    panel.hidden = !panel.hidden;
    $("#design-btn").setAttribute("aria-expanded", String(!panel.hidden));
  });
  document.querySelector(".design-pick").addEventListener("click", (e) => {
    const d = e.target.closest("button")?.dataset.design;
    if (!d) return;
    setDesign(d); render();
  });
  setDesign(new URLSearchParams(location.search).get("design") || store.get("design", "standaard"));
  $("#free-btn").addEventListener("click", () => {
    state.freeOnly = !state.freeOnly; store.set("freeOnly", state.freeOnly); render();
  });
  document.querySelector(".club-mode").addEventListener("click", (e) => {
    const mode = e.target.closest("button")?.dataset.club;
    if (!mode) return;
    state.clubMode = mode; store.set("clubMode", mode); render();
  });
  $("#cats").addEventListener("click", (e) => {
    const c = e.target.closest("button")?.dataset.cat;
    if (!c) return;
    state.cats.has(c) ? state.cats.delete(c) : state.cats.add(c);
    store.set("cats", [...state.cats]);
    renderCats(); render();
  });
  let t;
  $("#search").addEventListener("input", (e) => {
    clearTimeout(t);
    t = setTimeout(() => { state.search = e.target.value.trim().toLowerCase(); render(); }, 150);
  });
  $("#venue-btn").addEventListener("click", () => {
    const panel = $("#venue-panel");
    panel.hidden = !panel.hidden;
    $("#venue-btn").setAttribute("aria-expanded", String(!panel.hidden));
  });
  $("#venue-list").addEventListener("change", (e) => {
    const name = e.target.dataset.venue;
    if (!name) return;
    e.target.checked ? state.hiddenVenues.delete(name) : state.hiddenVenues.add(name);
    store.set("hiddenVenues", [...state.hiddenVenues]);
    renderVenues(); render();
  });
  $("#venue-list").addEventListener("click", (e) => {
    const name = e.target.closest("button")?.dataset.favVenue;
    if (!name) return;
    state.favVenues.has(name) ? state.favVenues.delete(name) : state.favVenues.add(name);
    store.set("favVenues", [...state.favVenues]);
    renderVenues(); render();
  });
  document.querySelector(".venue-actions").addEventListener("click", (e) => {
    const mode = e.target.closest("button")?.dataset.venues;
    if (!mode) return;
    const all = [...new Set(state.events.map((ev) => ev.venue))];
    if (mode === "all") state.hiddenVenues.clear();
    if (mode === "none") state.hiddenVenues = new Set(all);
    if (mode === "fav") state.hiddenVenues = new Set(all.filter((v) => !state.favVenues.has(v)));
    store.set("hiddenVenues", [...state.hiddenVenues]);
    renderVenues(); render();
  });
  document.body.addEventListener("click", (e) => {
    const star = e.target.closest(".star[data-id]");
    if (!star) return;
    e.preventDefault(); e.stopPropagation();
    toggleFavEvent(star.dataset.id);
  });
  $("#prev-week").addEventListener("click", () => { state.weekOffset = Math.max(0, state.weekOffset - 1); render(); });
  $("#next-week").addEventListener("click", () => { state.weekOffset = Math.min(WEEKS_AHEAD - 1, state.weekOffset + 1); render(); });

  const wk = $("#weekly");
  wk.open = store.get("weeklyOpen", false);
  wk.addEventListener("toggle", () => store.set("weeklyOpen", wk.open));
  const sr = $("#series");
  sr.open = store.get("seriesOpen", false);
  sr.addEventListener("toggle", () => store.set("seriesOpen", sr.open));

  // keep sticky day headers just below the sticky filter bar
  const header = document.querySelector(".top");
  const setH = () => document.documentElement.style.setProperty("--header-h", header.offsetHeight + "px");
  if ("ResizeObserver" in window) new ResizeObserver(setH).observe(header); else setH();

  // subscribe link: webcal:// opens the calendar app on phones
  if (location.protocol === "https:") {
    $("#ics-link").href = "webcal://" + location.host + location.pathname.replace(/[^/]*$/, "") + "events.ics";
  }
}

async function load() {
  bind();
  try {
    const [evRes, stRes] = await Promise.all([fetch("data/events.json", { cache: "no-cache" }), fetch("data/status.json", { cache: "no-cache" })]);
    const data = await evRes.json();
    state.events = data.events.map((ev) => {
      const s = new Date(ev.start);
      return { ...ev, _start: s, _day: dayKey(s), _endDay: ev.end ? dayKey(new Date(ev.end)) : null };
    });
    if (stRes.ok) renderStatus(await stRes.json(), data.generated);
  } catch (err) {
    $("#list").innerHTML = '<p class="empty">Kon de agenda niet laden.</p>';
    console.error(err);
    return;
  }
  renderCats();
  renderVenues();
  render();
}

load();

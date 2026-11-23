"use strict";
/* Amsterdam Agenda – plain JS, no build step. Reads data/events.json + data/status.json. */

const TZ = "Europe/Amsterdam";
const CATS = { film: "Film", music: "Muziek", club: "Club", talk: "Talk", theatre: "Theater", jazz: "Jazz", other: "Overig" };
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

const state = {
  events: [],
  view: store.get("view", "list"),
  quick: "all",
  cats: new Set(store.get("cats", [])),          // empty = all categories
  hiddenVenues: new Set(store.get("hiddenVenues", [])),
  favEvents: new Set(store.get("favEvents", [])),
  favVenues: new Set(store.get("favVenues", [])),
  search: "",
  weekOffset: 0,
};

// ---------------------------------------------------------------- date helpers (all in Amsterdam time)
const fmtKey = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
const fmtTime = new Intl.DateTimeFormat("nl-NL", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
const fmtDay = new Intl.DateTimeFormat("nl-NL", { timeZone: "UTC", weekday: "long", day: "numeric", month: "long" });
const fmtShort = new Intl.DateTimeFormat("nl-NL", { timeZone: "UTC", weekday: "short", day: "numeric", month: "short" });
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
  node.querySelector(".ev-sub").textContent = [ev.subtitle, ev.price].filter(Boolean).join(" · ");
  if (ev.status === "cancelled" || ev._start < Date.now() - 3 * 3600e3) node.classList.add("dim");
  starButton(node.querySelector(".star"), ev);
  return node;
}

function renderSeries() {
  const t = todayKey();
  const items = state.events.filter((e) => e.kind === "series" && matches(e, { ignoreQuick: state.quick !== "fav" })
    && e._day <= addDays(t, 14) && (e._endDay || e._day) >= t);
  const box = $("#series-list");
  box.replaceChildren();
  $("#series").hidden = items.length === 0;
  for (const ev of items) {
    const a = document.createElement("a");
    a.className = "series-card";
    a.href = ev.url; a.target = "_blank"; a.rel = "noopener";
    a.dataset.cat = ev.category;
    const strong = document.createElement("strong");
    strong.textContent = ev.title;
    const small = document.createElement("small");
    const until = ev._endDay ? "t/m " + fmtShort.format(keyToDate(ev._endDay)) : "";
    const from = ev._day > t ? "vanaf " + fmtShort.format(keyToDate(ev._day)) + " " : "";
    small.textContent = `${ev.venue} · ${from}${until}`;
    const star = document.createElement("button");
    star.className = "star";
    starButton(star, ev);
    a.append(strong, small, star);
    box.append(a);
  }
}

function renderList() {
  const list = $("#list");
  const days = new Map();
  for (const ev of state.events) {
    if (ev.kind === "series" || !matches(ev)) continue;
    if (!days.has(ev._day)) days.set(ev._day, []);
    days.get(ev._day).push(ev);
  }
  const frag = document.createDocumentFragment();
  let count = 0;
  for (const [k, evs] of days) {
    const sec = document.createElement("section");
    sec.className = "day";
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
  if (!count) list.innerHTML = '<p class="empty">Geen events gevonden met deze filters.</p>';
  $("#summary").textContent = `${count} event${count === 1 ? "" : "s"}`;
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
      if (ev._day !== k || ev.kind === "series" || !matches(ev, { ignoreQuick: state.quick !== "fav" })) continue;
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
  document.querySelectorAll("#quick button").forEach((b) => b.classList.toggle("on", b.dataset.quick === state.quick));
  $("#list").hidden = state.view !== "list";
  $("#week").hidden = state.view !== "week";
  renderSeries();
  if (state.view === "list") renderList(); else renderWeek();
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
    const n = document.createElement("td"); n.textContent = v.error || v.disabled ? "–" : v.events;
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
    state.quick = state.quick === q ? "all" : q;
    if (state.view === "week") state.weekOffset = 0;
    render();
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

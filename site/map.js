"use strict";
/* Kaartweergave. Loaded on first use by app.js (after Leaflet + markercluster) and uses its globals:
   state, store, matches, isFav, parseWeekly, todayKey, addDays, weekday, quickRange, keyToDate, fmt*, CATS, STATUS.
   Coordinates come from data/venues.json (filled once, never geocoded here). */
(function () {
  const DAYS_AHEAD = 42;
  const CENTER = [52.3676, 4.9041];
  let map = null, tiles = null, cluster = null, meLayer = null, lookup = null, groups = new Map(), openVenue = null;
  let fitted = false;

  // ------------------------------------------------------------ data
  async function loadVenues() {
    const res = await fetch("data/venues.json", { cache: "no-cache" });
    const data = await res.json();
    lookup = new Map();
    for (const [name, v] of Object.entries(data.venues || {})) lookup.set(name.toLowerCase(), { name, ...v });
    for (const [alias, target] of Object.entries(data.aliases || {})) {
      const v = lookup.get(String(target).toLowerCase());
      if (v) lookup.set(alias.toLowerCase(), v);
    }
  }
  const placeOf = (venue) => lookup.get(venue.toLowerCase());
  const day = () => state.mapDay || todayKey();

  function range() {
    return state.mapRange === "day" ? [day(), day()] : quickRange(state.mapRange);
  }

  // the days in [from, to] on which an item shows up on the map
  function occurrences(ev, from, to) {
    if (!ev.kind || ev.kind === "event") return ev._day >= from && ev._day <= to ? [ev._day] : [];
    if (ev.kind === "series") {
      const end = ev._endDay || ev._day;
      const a = ev._day > from ? ev._day : from, b = end < to ? end : to;
      return a <= b ? [a] : [];                       // once per period, under its first visible day
    }
    if (ev.kind === "weekly") {
      const days = parseWeekly(ev).days, out = [];
      for (let k = from; k <= to; k = addDays(k, 1)) if (days.includes(weekday(k))) out.push(k);
      return out;
    }
    return [];
  }

  // same filters as the list (categories, club switch, gratis, search, hidden venues), plus "★ Favorieten"
  const passes = (ev) => matches(ev, { ignoreQuick: true }) && (state.quick !== "fav" || isFav(ev));

  function sortKey(item) {
    return item.day + (item.ev.kind === "event" || !item.ev.kind
      ? (item.ev.all_day ? "99:99" : fmtTime.format(item.ev._start))
      : item.ev.kind === "weekly" ? parseWeekly(item.ev).time : "00:00");
  }

  function collect() {
    const [from, to] = range();
    groups = new Map();
    for (const ev of state.events) {
      if (!passes(ev)) continue;
      for (const k of occurrences(ev, from, to)) {
        if (!groups.has(ev.venue)) groups.set(ev.venue, { name: ev.venue, place: placeOf(ev.venue), items: [] });
        groups.get(ev.venue).items.push({ ev, day: k });
      }
    }
    for (const g of groups.values()) g.items.sort((a, b) => sortKey(a).localeCompare(sortKey(b)));
  }

  function dayCounts() {
    const t = todayKey(), last = addDays(t, DAYS_AHEAD - 1), counts = new Map();
    for (const ev of state.events) {
      if (!passes(ev)) continue;
      for (const k of occurrences(ev, t, last)) counts.set(k, (counts.get(k) || 0) + 1);
    }
    return counts;
  }

  // ------------------------------------------------------------ map
  const isDark = () => /dark/.test(getComputedStyle(document.documentElement).colorScheme || "");

  function setTiles() {
    // OpenStreetMap's own tiles (no key; light use with attribution is within its tile policy).
    // OSM has no dark style: in dark mode / poster the tiles are inverted with a CSS filter (.map.dark).
    $("#map").classList.toggle("dark", isDark());
    if (tiles) return;
    tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-bijdragers',
    }).addTo(map);
  }

  function markerIcon(g) {
    const counts = {};
    for (const { ev } of g.items) counts[ev.category] = (counts[ev.category] || 0) + 1;
    const cats = Object.keys(counts), n = g.items.length;
    let bg;
    if (cats.length === 1) bg = `var(--${cats[0]}, var(--other))`;
    else {                                            // small pie: one slice per category
      let acc = 0;
      bg = "conic-gradient(" + cats.map((c) => {
        const a = (acc / n) * 360; acc += counts[c];
        return `var(--${c}, var(--other)) ${a.toFixed(1)}deg ${((acc / n) * 360).toFixed(1)}deg`;
      }).join(", ") + ")";
    }
    const size = n >= 10 ? 42 : n >= 4 ? 36 : 32;
    const fav = state.favVenues.has(g.name);
    return L.divIcon({
      className: "vm-wrap",
      html: `<div class="vm${fav ? " fav" : ""}" style="background:${bg};width:${size}px;height:${size}px"><span>${n}</span></div>`,
      iconSize: [size, size], iconAnchor: [size / 2, size / 2],
    });
  }

  function init() {
    const el = $("#map");
    el.replaceChildren();
    map = L.map(el, { zoomControl: true, tap: true }).setView(CENTER, 13);
    setTiles();
    cluster = L.markerClusterGroup({
      showCoverageOnHover: false, maxClusterRadius: 36, disableClusteringAtZoom: 16, spiderfyOnMaxZoom: true,
      iconCreateFunction: (c) => {
        const total = c.getAllChildMarkers().reduce((s, m) => s + m.options.count, 0);
        return L.divIcon({ className: "vm-wrap", html: `<div class="vm cl"><span>${total}</span></div>`, iconSize: [44, 44] });
      },
    });
    map.addLayer(cluster);
    map.on("click", closeSheet);
    bindControls();
  }

  function fit() {
    const pts = [...groups.values()].filter((g) => g.place).map((g) => [g.place.lat, g.place.lng]);
    if (meLayer) pts.push(meLayer.getLatLng());
    if (pts.length) map.fitBounds(pts, { padding: [36, 36], maxZoom: 15 });
    else map.setView(CENTER, 13);
  }

  // ------------------------------------------------------------ controls
  function renderDays(counts) {
    const nav = $("#map-days"), t = todayKey(), [from, to] = range();
    nav.replaceChildren();
    for (let i = 0; i < DAYS_AHEAD; i++) {
      const k = addDays(t, i), d = keyToDate(k);
      const b = document.createElement("button");
      b.dataset.day = k;
      const on = state.mapRange === "day" && k === day();
      if (on) b.className = "on";
      else if (state.mapRange !== "day" && k >= from && k <= to) b.className = "in";
      b.setAttribute("aria-pressed", String(on));
      const n = counts.get(k) || 0;
      b.setAttribute("aria-label", `${fmtDay.format(d)}: ${n} events`);
      b.innerHTML = `<small>${k === t ? "vandaag" : fmtWeekday.format(d)}</small><b>${d.getUTCDate()}</b><i>${n || "–"}</i>`;
      nav.append(b);
    }
    const sel = nav.querySelector(".on") || nav.querySelector(".in");
    if (sel) {
      const left = sel.offsetLeft - nav.clientWidth / 2 + sel.offsetWidth / 2;
      nav.scrollTo({ left: Math.max(0, left), behavior: "smooth" });
    }
    $("#map-prev").disabled = state.mapRange === "day" && day() <= t;
    $("#map-next").disabled = state.mapRange === "day" && day() >= addDays(t, DAYS_AHEAD - 1);
    document.querySelectorAll(".map-range button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.range === state.mapRange)));
  }

  function setDay(k) {
    const t = todayKey(), last = addDays(t, DAYS_AHEAD - 1);
    state.mapDay = k < t ? t : k > last ? last : k;
    if (state.mapDay === t) state.mapDay = null;
    state.mapRange = "day";
    render();                                         // app.js render(): chips, URL, then draw()
  }

  function bindControls() {
    $("#map-days").addEventListener("click", (e) => {
      const k = e.target.closest("button")?.dataset.day;
      if (k) setDay(k);
    });
    $("#map-prev").addEventListener("click", () => setDay(addDays(state.mapRange === "day" ? day() : range()[0], -1)));
    $("#map-next").addEventListener("click", () => setDay(addDays(state.mapRange === "day" ? day() : range()[1], 1)));
    document.querySelector(".map-range").addEventListener("click", (e) => {
      const r = e.target.closest("button")?.dataset.range;
      if (!r) return;
      state.mapRange = r;
      render();
    });
    $("#map-fit").addEventListener("click", fit);
    $("#map-locate").addEventListener("click", locate);
    $("#ms-close").addEventListener("click", closeSheet);
    $("#ms-all").addEventListener("click", () => {
      if (!openVenue) return;
      // locatiefilter: only this venue, then jump to the list
      const all = new Set(state.events.map((ev) => ev.venue));
      all.delete(openVenue);
      state.hiddenVenues = all;
      store.set("hiddenVenues", [...all]);
      closeSheet();
      state.view = "list"; store.set("view", "list");
      renderVenues(); render();
      window.scrollTo({ top: 0 });
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });
  }

  function locate() {
    const btn = $("#map-locate");
    if (!("geolocation" in navigator)) { btn.textContent = "◎ Niet beschikbaar"; return; }
    btn.textContent = "◎ Zoeken…";
    navigator.geolocation.getCurrentPosition((pos) => {
      const ll = [pos.coords.latitude, pos.coords.longitude];
      if (meLayer) meLayer.setLatLng(ll);
      else meLayer = L.circleMarker(ll, { radius: 8, weight: 3, color: "#fff", fillColor: "#1a73e8", fillOpacity: 1 })
        .bindTooltip("Jij bent hier").addTo(map);
      map.setView(ll, Math.max(map.getZoom(), 14));
      btn.textContent = "◎ Mijn locatie";
    }, () => { btn.textContent = "◎ Geen toegang"; setTimeout(() => (btn.textContent = "◎ Mijn locatie"), 2500); },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
  }

  // ------------------------------------------------------------ bottom sheet / side panel
  function row(item) {
    const { ev } = item;
    const a = document.createElement("div");
    a.className = "ms-row" + (ev.status === "cancelled" ? " dim" : "");
    a.dataset.cat = ev.category;
    const time = document.createElement("b");
    time.textContent = ev.kind === "series" ? "loopt" : ev.kind === "weekly" ? parseWeekly(ev).time.split(/[–-]/)[0]
      : ev.all_day ? "–" : fmtTime.format(ev._start);
    const body = document.createElement("div");
    const title = document.createElement("a");
    title.className = "ms-title"; title.href = ev.url; title.target = "_blank"; title.rel = "noopener";
    title.textContent = ev.title;
    const meta = document.createElement("small");
    const cat = document.createElement("span"); cat.className = "ms-cat"; cat.textContent = CATS[ev.category] || ev.category;
    meta.append(cat);
    if (STATUS[ev.status]) { const st = document.createElement("span"); st.className = "ev-status " + ev.status; st.textContent = STATUS[ev.status]; meta.append(" ", st); }
    const price = ev.free ? (ev.price && !/gratis|free|donat/i.test(ev.price) ? `${ev.price} (gratis/donatie)` : ev.price || "gratis") : ev.price;
    const extra = [ev.kind === "series" && ev._endDay ? "t/m " + fmtShort.format(keyToDate(ev._endDay)) : "",
      ev.kind === "weekly" ? "vaste prik" : "", price].filter(Boolean).join(" · ");
    if (extra) meta.append(" · " + extra);
    body.append(title, meta);
    const star = document.createElement("button"); star.className = "star"; starButton(star, ev);
    a.append(time, body, star);
    return a;
  }

  function openSheet(name) {
    const g = groups.get(name);
    openVenue = name;
    const sheet = $("#map-sheet");
    $("#ms-title").textContent = name + (state.favVenues.has(name) ? " ★" : "");
    $("#ms-address").textContent = g?.place?.address || "";
    const list = $("#ms-list");
    list.replaceChildren();
    if (!g || !g.items.length) {
      const p = document.createElement("p"); p.className = "empty"; p.textContent = "Geen events met deze filters.";
      list.append(p);
    } else {
      let last = null;
      for (const item of g.items) {
        if (state.mapRange !== "day" && item.day !== last) {
          const h = document.createElement("h3"); h.textContent = fmtDay.format(keyToDate(item.day)); list.append(h);
          last = item.day;
        }
        list.append(row(item));
      }
    }
    sheet.hidden = false;
  }

  function closeSheet() { openVenue = null; $("#map-sheet").hidden = true; }

  // ------------------------------------------------------------ render
  function draw() {
    if (!lookup) { loadVenues().then(draw).catch((err) => { console.error(err); $("#map").textContent = "Kon locaties niet laden."; }); return; }
    if (!map) init();
    setTiles();
    map.invalidateSize();
    collect();
    renderDays(dayCounts());

    cluster.clearLayers();
    const markers = [];
    for (const g of groups.values()) {
      if (!g.place) continue;
      const m = L.marker([g.place.lat, g.place.lng], {
        icon: markerIcon(g), title: `${g.name}: ${g.items.length}`, alt: g.name, keyboard: true, count: g.items.length,
        zIndexOffset: state.favVenues.has(g.name) ? 1000 : 0,
      });
      m.on("click", (e) => { L.DomEvent.stopPropagation(e); openSheet(g.name); });
      markers.push(m);
    }
    cluster.addLayers(markers);
    if (!fitted && markers.length) { fit(); fitted = true; }

    const total = [...groups.values()].reduce((s, g) => s + g.items.length, 0);
    const missing = [...groups.values()].filter((g) => !g.place).sort((a, b) => a.name.localeCompare(b.name, "nl"));
    const mp = $("#map-missing");
    mp.hidden = !missing.length;
    mp.textContent = missing.length ? "Niet op de kaart: " + missing.map((g) => `${g.name} (${g.items.length})`).join(", ") : "";
    const [from, to] = range();
    const when = from === to ? fmtDay.format(keyToDate(from)) : `${fmtShort.format(keyToDate(from))} – ${fmtShort.format(keyToDate(to))}`;
    $("#summary").textContent = `${total} event${total === 1 ? "" : "s"} op ${groups.size - missing.length} plekken · ${when}`;

    if (openVenue) openSheet(openVenue);
    // the map container only gets its final size after the header settled
    requestAnimationFrame(() => map.invalidateSize());
  }

  window.AgendaMap = { render: draw };
})();

const state = { origin: null, destination: null, map: null, layers: [], lastResult: null, isRouting: false };
const $ = (id) => document.getElementById(id);
const presets = { balanced: [2, 0, 20], lit: [2.5, 0, 25], short: [.5, 0, 10], transit: [1, 2, 25] };
const THEME_KEY = "herroute-theme";
const FAVORITES_KEY = "herroute-favorites";
const FEEDBACK_KEY = "herroute-feedback";

function showError(message = "") { $("error").textContent = message; }
function updateCompare() { $("compare").disabled = state.isRouting || !(state.origin && state.destination); }
function updateOutputs() { $("lighting-output").value = $("lighting").value; $("transit-output").value = $("transit").value; $("detour-output").value = `${$("detour").value}%`; }
function placeFor(endpoint) { return state[endpoint]; }

function setRoutingState(isRouting) {
  state.isRouting = isRouting;
  const button = $("compare");
  button.classList.toggle("is-loading", isRouting);
  button.querySelector(".button-label").hidden = isRouting;
  button.querySelector(".button-loading").hidden = !isRouting;
  $("route-status").textContent = isRouting ? "Finding routes and comparing mapped infrastructure…" : "";
  updateCompare();
}

function initialTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const dark = theme === "dark";
  $("theme-toggle").textContent = dark ? "Use light mode" : "Use dark mode";
  $("theme-toggle").setAttribute("aria-pressed", String(dark));
}

function addressSearch(endpoint) {
  const input = $(endpoint); const options = $(`${endpoint}-options`); let timer;
  input.addEventListener("input", () => {
    state[endpoint] = null; updateCompare(); clearTimeout(timer); options.replaceChildren(); options.classList.remove("visible");
    const query = input.value.trim(); if (query.length < 3) return;
    timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/suggest?q=${encodeURIComponent(query)}`); const suggestions = await response.json();
        if (!response.ok) throw new Error(suggestions.detail || "Address suggestions are unavailable.");
        suggestions.forEach((suggestion) => {
          const item = document.createElement("li"); const button = document.createElement("button"); button.type = "button"; button.textContent = suggestion.label;
          button.onclick = () => { state[endpoint] = suggestion; input.value = suggestion.label; options.replaceChildren(); options.classList.remove("visible"); showError(); updateCompare(); };
          item.append(button); options.append(item);
        });
        options.classList.toggle("visible", suggestions.length > 0);
      } catch (error) { showError(error.message); }
    }, 350);
  });
}

function metrics(route) {
  const m = route.metrics; const transit = m.mean_nearest_transit_stop_m == null ? "Unknown" : `${m.mean_nearest_transit_stop_m.toFixed(0)} m`;
  const coverage = m.mapped_light_coverage_pct == null ? "Unknown" : `${m.mapped_light_coverage_pct.toFixed(1)}%`;
  return `<div class="metric">Walking distance<strong>${(m.distance_m / 1000).toFixed(2)} km</strong></div><div class="metric">Estimated time<strong>${m.estimated_minutes.toFixed(1)} min</strong></div><div class="metric">Mapped-light coverage<strong>${coverage}</strong></div><div class="metric">Mean nearest mapped stop<strong>${transit}</strong></div>`;
}

function renderMap(result) {
  if (!state.map) { state.map = L.map("map"); L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "OpenStreetMap contributors" }).addTo(state.map); }
  state.layers.forEach((layer) => layer.remove()); state.layers = []; const routes = result.comparison; const bounds = [];
  const addRoute = (route, color) => { if (!route) return; const points = route.coordinates.map(([lon, lat]) => [lat, lon]); const line = L.polyline(points, { color, weight: 6, opacity: .85 }).addTo(state.map); state.layers.push(line); bounds.push(...points); };
  addRoute(routes.shortest, "#4789ff"); addRoute(routes.lighting_aware, "#d873ec");
  [[result.origin, "#37c89c", "Origin"], [result.destination, "#ff696f", "Destination"]].forEach(([place, color, name]) => { const marker = L.circleMarker([place.lat, place.lon], { color, fillColor: color, fillOpacity: 1, radius: 8 }).bindPopup(`${name}: ${place.label}`).addTo(state.map); state.layers.push(marker); bounds.push([place.lat, place.lon]); });
  state.map.fitBounds(bounds, { padding: [35, 35] });
}

function routeExplanation(comparison) {
  const candidate = comparison.lighting_aware; if (!candidate) return `<p class="delta">${comparison.alternative_unavailable_reason}</p>`;
  const shortest = comparison.shortest.metrics; const preferred = candidate.metrics;
  const detour = ((preferred.distance_m / shortest.distance_m - 1) * 100).toFixed(1); const coverage = (preferred.mapped_light_coverage_pct - shortest.mapped_light_coverage_pct).toFixed(1);
  const transit = preferred.mean_nearest_transit_stop_m - shortest.mean_nearest_transit_stop_m; const transitText = transit === 0 ? "the same mapped-stop proximity" : `${Math.abs(transit).toFixed(0)} m ${transit < 0 ? "closer to" : "farther from"} mapped stops`;
  return `<p class="delta">The recommended route is <strong>${detour}% longer</strong>, has <strong>${coverage} percentage points more mapped-light coverage</strong>, and is <strong>${transitText}</strong>. It stays within your detour limit and reflects the preference you selected.</p>`;
}

function favorites() {
  const stored = JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]");
  if (Array.isArray(stored)) return stored;
  return Object.entries(stored).map(([name, place]) => ({ name, place }));
}

function saveFavorites(saved) { localStorage.setItem(FAVORITES_KEY, JSON.stringify(saved)); }

function renderFavorites() {
  const container = $("favorites"); container.replaceChildren(); const saved = favorites();
  if (!saved.length) { container.textContent = "No saved places yet."; return; }
  saved.forEach(({ name, place }) => {
    const row = document.createElement("div"); row.className = "favorite-item";
    const label = document.createElement("span"); label.textContent = `${name}: ${place.label}`;
    const actions = document.createElement("div"); actions.className = "favorite-actions";
    ["origin", "destination"].forEach((endpoint) => { const button = document.createElement("button"); button.type = "button"; button.textContent = `Use as ${endpoint === "origin" ? "From" : "To"}`; button.onclick = () => { state[endpoint] = place; $(endpoint).value = place.label; $("favorite-status").textContent = `${name} is now your ${endpoint === "origin" ? "From" : "To"} address.`; updateCompare(); }; actions.append(button); });
    const remove = document.createElement("button"); remove.type = "button"; remove.className = "remove-place"; remove.textContent = "Remove"; remove.onclick = () => { saveFavorites(favorites().filter((item) => item.name !== name)); renderFavorites(); $("favorite-status").textContent = `${name} was removed from this browser.`; };
    actions.append(remove); row.append(label, actions); container.append(row);
  });
}

function saveFavorite() {
  const name = $("favorite-name").value.trim(); const endpoint = $("favorite-endpoint").value; const place = placeFor(endpoint);
  if (!name) { $("favorite-status").textContent = "Add a name, such as Home or Work, before saving."; return; }
  if (!place) { $("favorite-status").textContent = `Choose a ${endpoint === "origin" ? "From" : "To"} address before saving.`; return; }
  const saved = favorites().filter((item) => item.name.toLocaleLowerCase() !== name.toLocaleLowerCase());
  saved.push({ name, place }); saveFavorites(saved); $("favorite-name").value = ""; $("favorite-status").textContent = `${name} was saved only in this browser.`; renderFavorites();
}

function feedbackNotes() { return JSON.parse(localStorage.getItem(FEEDBACK_KEY) || "[]"); }
function updateFeedbackStatus(message = "") { const count = feedbackNotes().length; $("feedback-status").textContent = message || `${count} note${count === 1 ? "" : "s"} saved only on this device.`; }

function saveFeedback() {
  const notes = feedbackNotes();
  notes.push({ type: $("feedback-type").value, note: $("feedback-note").value.trim(), saved_at: new Date().toISOString() });
  localStorage.setItem(FEEDBACK_KEY, JSON.stringify(notes)); $("feedback-note").value = ""; updateFeedbackStatus("Note saved only on this device. It was not sent to HerRoute.");
}

function downloadFeedback() {
  const notes = feedbackNotes();
  if (!notes.length) { updateFeedbackStatus("There are no notes to download yet."); return; }
  const blob = new Blob([JSON.stringify(notes, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "herroute-private-notes.json"; link.click(); URL.revokeObjectURL(url); updateFeedbackStatus("Your private notes were downloaded.");
}

function clearFeedback() {
  if (!feedbackNotes().length) { updateFeedbackStatus("There are no notes to clear."); return; }
  if (window.confirm("Clear all private notes saved in this browser? This cannot be undone.")) { localStorage.removeItem(FEEDBACK_KEY); updateFeedbackStatus("All private notes were cleared from this browser."); }
}

function applySharedRoute() {
  const params = new URLSearchParams(location.search);
  ["origin", "destination"].forEach((endpoint) => { const id = params.get(`${endpoint}_id`); const label = params.get(`${endpoint}_label`); if (id && label) { state[endpoint] = { place_id: id, label }; $(endpoint).value = label; } });
  updateCompare();
}

async function copyRouteLink() {
  const url = new URL(location.href); url.search = "";
  ["origin", "destination"].forEach((endpoint) => { url.searchParams.set(`${endpoint}_id`, state[endpoint].place_id); url.searchParams.set(`${endpoint}_label`, state[endpoint].label); });
  try { await navigator.clipboard.writeText(url.toString()); $("share").textContent = "Link copied"; setTimeout(() => { $("share").textContent = "Copy route link"; }, 1800); } catch { showError("Your browser could not copy the link. Copy the address from the browser bar instead."); }
}

$("lighting").addEventListener("input", updateOutputs); $("transit").addEventListener("input", updateOutputs); $("detour").addEventListener("input", updateOutputs);
document.querySelectorAll(".preset").forEach((button) => button.onclick = () => { const [lighting, transit, detour] = presets[button.dataset.preset]; $("lighting").value = lighting; $("transit").value = transit; $("detour").value = detour; updateOutputs(); document.querySelectorAll(".preset").forEach((item) => item.classList.toggle("active", item === button)); });
$("theme-toggle").onclick = () => { const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark"; localStorage.setItem(THEME_KEY, next); applyTheme(next); };
$("save-favorite").onclick = saveFavorite;
$("save-feedback").onclick = saveFeedback;
$("download-feedback").onclick = downloadFeedback;
$("clear-feedback").onclick = clearFeedback;
$("share").onclick = copyRouteLink;
$("compare").addEventListener("click", async () => {
  showError(); setRoutingState(true);
  try {
    const response = await fetch("/api/routes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin_place_id: state.origin.place_id, destination_place_id: state.destination.place_id, lighting_penalty: Number($("lighting").value), transit_proximity_penalty: Number($("transit").value), max_detour_pct: Number($("detour").value) }) });
    const result = await response.json(); if (!response.ok) throw new Error(result.detail || "Route calculation failed."); state.lastResult = result;
    $("selected-addresses").textContent = `From: ${result.origin.label} | To: ${result.destination.label}`; $("shortest-metrics").innerHTML = metrics(result.comparison.shortest); $("lighting-metrics").innerHTML = result.comparison.lighting_aware ? metrics(result.comparison.lighting_aware) : result.comparison.alternative_unavailable_reason; $("why-route").innerHTML = routeExplanation(result.comparison);
    $("results").hidden = false; renderMap(result);
  } catch (error) { showError(error.message); } finally { setRoutingState(false); }
});
addressSearch("origin"); addressSearch("destination"); updateOutputs(); renderFavorites(); updateFeedbackStatus(); applySharedRoute(); applyTheme(initialTheme());
const clock = new Date(); const time = clock.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
$("evening-context").textContent = `Your local time is ${time}. Live lighting, disruption, and transit-service conditions are not included yet.`;

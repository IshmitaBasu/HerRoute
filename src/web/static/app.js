const state = { origin: null, destination: null, map: null, layers: [], lastResult: null };
const $ = (id) => document.getElementById(id);
const presets = { balanced: [2, 0, 20], lit: [2.5, 0, 25], short: [.5, 0, 10], transit: [1, 2, 25] };

function showError(message = "") { $("error").textContent = message; }
function updateCompare() { $("compare").disabled = !(state.origin && state.destination); }
function updateOutputs() { $("lighting-output").value = $("lighting").value; $("transit-output").value = $("transit").value; $("detour-output").value = `${$("detour").value}%`; }
function placeFor(endpoint) { return state[endpoint]; }

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

function favorites() { return JSON.parse(localStorage.getItem("herroute-favorites") || "{}"); }
function renderFavorites() {
  const container = $("favorites"); container.replaceChildren(); const saved = favorites();
  Object.entries(saved).forEach(([role, place]) => {
    const row = document.createElement("div"); row.className = "favorite-item"; const label = document.createElement("span"); label.textContent = `${role}: ${place.label}`;
    const actions = document.createElement("div"); actions.className = "favorite-actions";
    ["origin", "destination"].forEach((endpoint) => { const button = document.createElement("button"); button.textContent = `Use as ${endpoint === "origin" ? "from" : "to"}`; button.onclick = () => { state[endpoint] = place; $(endpoint).value = place.label; updateCompare(); }; actions.append(button); });
    row.append(label, actions); container.append(row);
  });
}

function saveFavorite() {
  const role = $("favorite-role").value; const endpoint = $("favorite-endpoint").value; const place = placeFor(endpoint);
  if (!place) return; const saved = favorites(); saved[role] = place; localStorage.setItem("herroute-favorites", JSON.stringify(saved)); renderFavorites();
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
$("save-favorite").onclick = saveFavorite;
$("save-feedback").onclick = () => { const feedback = JSON.parse(localStorage.getItem("herroute-feedback") || "[]"); feedback.push({ type: $("feedback-type").value, note: $("feedback-note").value.trim(), saved_at: new Date().toISOString() }); localStorage.setItem("herroute-feedback", JSON.stringify(feedback)); $("feedback-note").value = ""; $("feedback-status").textContent = "Saved in this browser."; };
$("share").onclick = copyRouteLink;
$("compare").addEventListener("click", async () => {
  showError(); $("compare").disabled = true;
  try {
    const response = await fetch("/api/routes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin_place_id: state.origin.place_id, destination_place_id: state.destination.place_id, lighting_penalty: Number($("lighting").value), transit_proximity_penalty: Number($("transit").value), max_detour_pct: Number($("detour").value) }) });
    const result = await response.json(); if (!response.ok) throw new Error(result.detail || "Route calculation failed."); state.lastResult = result;
    $("selected-addresses").textContent = `From: ${result.origin.label} | To: ${result.destination.label}`; $("shortest-metrics").innerHTML = metrics(result.comparison.shortest); $("lighting-metrics").innerHTML = result.comparison.lighting_aware ? metrics(result.comparison.lighting_aware) : result.comparison.alternative_unavailable_reason; $("why-route").innerHTML = routeExplanation(result.comparison);
    $("results").hidden = false; renderMap(result);
  } catch (error) { showError(error.message); } finally { updateCompare(); }
});
addressSearch("origin"); addressSearch("destination"); updateOutputs(); renderFavorites(); applySharedRoute();
const clock = new Date(); const time = clock.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
$("evening-context").textContent = `Your local time is ${time}. Live lighting, disruption, and transit-service conditions are not included yet.`;

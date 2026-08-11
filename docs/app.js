let FACILITIES = [];
let MAP = null;
let MARKERS = [];

function fmtNum(v, digits = 1) {
  if (v === null || v === undefined || v === "" || isNaN(v)) return "—";
  const n = Number(v);
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function isIncluded(f) {
  return !(f.status || "").toUpperCase().startsWith("EXCLUDED");
}

function primaryName(f) {
  return (f.tenants || "").split(";")[0].trim();
}

function powerMW(f) {
  const kw = parseFloat(f.power_kw);
  if (isNaN(kw)) return null;
  return kw / 1000;
}

async function init() {
  const res = await fetch("data/manifest.json");
  FACILITIES = await res.json();
  renderStats();
  renderMap();
  bindControls();
  renderGallery();
}

function renderStats() {
  const total = FACILITIES.length;
  const included = FACILITIES.filter(isIncluded);
  const totalMW = included.reduce((s, f) => s + (powerMW(f) || 0), 0);
  const totalWaterM = included.reduce((s, f) => s + (parseFloat(f.water_regional_l_yr) || 0), 0) / 1e6;
  const totalCarbon = included.reduce((s, f) => s + (parseFloat(f.carbon_tco2e_yr) || 0), 0) / 1e6;

  const stats = [
    [total, "buildings independently measured"],
    [included.length, "included in resource totals"],
    [`${fmtNum(totalMW)} MW`, "combined estimated power demand"],
    [`${fmtNum(totalWaterM)}M L/yr`, "combined estimated water use (regional WUE)"],
    [`${fmtNum(totalCarbon, 2)}M tCO₂e/yr`, "combined estimated carbon emissions"],
  ];
  document.getElementById("statsBar").innerHTML = stats.map(([num, label]) =>
    `<div class="stat-box"><div class="num">${num}</div><div class="label">${label}</div></div>`
  ).join("");
}

function renderMap() {
  MAP = L.map("map", { scrollWheelZoom: false }).setView([3.5, 102.5], 6);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(MAP);

  const bounds = [];
  FACILITIES.forEach((f) => {
    if (f.lat === null || f.lon === null) return;
    const included = isIncluded(f);
    const marker = L.circleMarker([f.lat, f.lon], {
      radius: 6,
      fillColor: included ? "#0f6e6e" : "#b23b3b",
      color: "#ffffff",
      weight: 1.5,
      fillOpacity: 0.85,
    }).addTo(MAP);
    const mw = powerMW(f);
    marker.bindPopup(`
      <strong>${primaryName(f)}</strong><br>
      ${fmtNum(f.area_m2, 0)} m&sup2; footprint<br>
      ${mw ? fmtNum(mw) + " MW estimated" : "No power estimate"}<br>
      <a href="#" data-id="${f.id}" class="popup-link">View details &rarr;</a>
    `);
    marker.on("popupopen", () => {
      const link = document.querySelector(`.popup-link[data-id="${CSS.escape(f.id)}"]`);
      if (link) link.addEventListener("click", (e) => { e.preventDefault(); openModal(f); });
    });
    MARKERS.push({ marker, facility: f });
    // Exclude out-of-country geocoding failures (e.g. Marina Bay, Metro Manila) from the
    // auto-fit bounds so a handful of bad coordinates don't zoom the map out to a useless extent.
    if (!(f.flags || "").includes("OUTSIDE_MALAYSIA") && !(f.flags || "").includes("COORDINATE_OUTSIDE")) {
      bounds.push([f.lat, f.lon]);
    }
  });

  if (bounds.length > 0) {
    MAP.fitBounds(bounds, { padding: [24, 24], maxZoom: 9 });
  }
}

function bindControls() {
  document.getElementById("searchBox").addEventListener("input", renderGallery);
  document.getElementById("statusFilter").addEventListener("change", renderGallery);
  document.getElementById("sortBy").addEventListener("change", renderGallery);
  document.getElementById("modalClose").addEventListener("click", closeModal);
  document.getElementById("modalOverlay").addEventListener("click", (e) => {
    if (e.target.id === "modalOverlay") closeModal();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
}

function getFiltered() {
  const q = document.getElementById("searchBox").value.trim().toLowerCase();
  const statusFilter = document.getElementById("statusFilter").value;
  const sortBy = document.getElementById("sortBy").value;

  let list = FACILITIES.filter((f) => {
    if (q && !f.tenants.toLowerCase().includes(q)) return false;
    if (statusFilter === "included" && !isIncluded(f)) return false;
    if (statusFilter === "excluded" && isIncluded(f)) return false;
    return true;
  });

  if (sortBy === "name") list.sort((a, b) => primaryName(a).localeCompare(primaryName(b)));
  else if (sortBy === "power") list.sort((a, b) => (powerMW(b) || 0) - (powerMW(a) || 0));
  else if (sortBy === "area") list.sort((a, b) => (parseFloat(b.area_m2) || 0) - (parseFloat(a.area_m2) || 0));
  else if (sortBy === "carbon") list.sort((a, b) => (parseFloat(b.carbon_tco2e_yr) || 0) - (parseFloat(a.carbon_tco2e_yr) || 0));

  return list;
}

function renderGallery() {
  const list = getFiltered();
  document.getElementById("resultCount").textContent = `${list.length} of ${FACILITIES.length} facilities`;

  document.getElementById("gallery").innerHTML = list.map((f) => {
    const included = isIncluded(f);
    const mw = powerMW(f);
    const img = f.thumb || "https://via.placeholder.com/300x150?text=No+image";
    return `
      <div class="card" data-id="${f.id}">
        <img src="${img}" alt="${primaryName(f)}" loading="lazy">
        <div class="card-body">
          <p class="card-title">${primaryName(f)}</p>
          <div class="card-stats">
            <span>${fmtNum(f.area_m2, 0)} m&sup2;</span>
            <span>${mw ? fmtNum(mw) + " MW" : "No power estimate"}</span>
          </div>
          <span class="badge ${included ? "included" : "excluded"}">${included ? "Included" : "Excluded"}</span>
        </div>
      </div>
    `;
  }).join("");

  document.querySelectorAll(".card").forEach((card) => {
    card.addEventListener("click", () => {
      const f = FACILITIES.find((x) => x.id === card.dataset.id);
      openModal(f);
    });
  });
}

function openModal(f) {
  if (MAP) MAP.closePopup();
  const included = isIncluded(f);
  const mw = powerMW(f);
  const img = f.image || f.thumb || "https://via.placeholder.com/700x350?text=No+image";

  const stats = [
    ["Footprint area (polygon)", `${fmtNum(f.area_m2, 0)} m²`],
    ["Footprint area (bounding box, for reference)", f.bbox_area_m2 ? `${fmtNum(f.bbox_area_m2, 0)} m²` : "—"],
    ["Estimated power", mw ? `${fmtNum(mw)} MW` : "—"],
    ["Disclosed capacity", f.disclosed_mw ? `${fmtNum(f.disclosed_mw)} MW (operator-disclosed)` : "Not disclosed (modelled)"],
    ["Estimated annual energy", f.energy_mwh_yr ? `${fmtNum(f.energy_mwh_yr / 1000, 1)} GWh/yr` : "—"],
    ["Estimated annual carbon", f.carbon_tco2e_yr ? `${fmtNum(f.carbon_tco2e_yr, 0)} tCO₂e/yr` : "—"],
    ["Estimated water (regional)", f.water_regional_l_yr ? `${fmtNum(f.water_regional_l_yr / 1e6, 1)}M L/yr` : "—"],
    ["Estimated water (optimised)", f.water_optimized_l_yr ? `${fmtNum(f.water_optimized_l_yr / 1e6, 1)}M L/yr` : "—"],
    ["Waste heat", f.waste_heat_gj_yr ? `${fmtNum(f.waste_heat_gj_yr, 0)} GJ/yr` : "—"],
    ["Power intensity", f.power_w_per_sqft ? `${fmtNum(f.power_w_per_sqft, 1)} W/sqft` : "—"],
    ["Water intensity", f.water_l_per_sqft_yr ? `${fmtNum(f.water_l_per_sqft_yr, 0)} L/sqft/yr` : "—"],
    ["Carbon intensity", f.carbon_kg_per_sqft_yr ? `${fmtNum(f.carbon_kg_per_sqft_yr, 2)} kg CO₂e/sqft/yr` : "—"],
    ["Coordinates", f.lat && f.lon ? `${f.lat.toFixed(5)}, ${f.lon.toFixed(5)}` : "—"],
  ];

  let noteHtml = "";
  if (f.fun_comparison) {
    noteHtml += `<div class="modal-note fun">${f.fun_comparison}</div>`;
  }
  if (f.qa_notes) {
    noteHtml += `<div class="modal-note danger"><strong>QA note:</strong> ${f.qa_notes}</div>`;
  }
  if (f.flags) {
    noteHtml += `<div class="modal-note"><strong>Detection flags:</strong> ${f.flags}</div>`;
  }
  if (f.qc_flag) {
    noteHtml += `<div class="modal-note"><strong>QC:</strong> ${f.qc_flag} — flagged for manual visual review, not an automatic exclusion.</div>`;
  }

  document.getElementById("modalBody").innerHTML = `
    <img src="${img}" alt="${primaryName(f)}">
    <h2>${primaryName(f)}</h2>
    <p class="modal-sub">${f.tenants}${f.n_tenants > 1 ? ` (${f.n_tenants} tenants sharing this building)` : ""} &middot;
      <span class="badge ${included ? "included" : "excluded"}">${included ? "Included in resource totals" : "Excluded from resource totals"}</span>
    </p>
    <div class="modal-grid">
      ${stats.map(([label, value]) => `<div class="modal-stat"><div class="label">${label}</div><div class="value">${value}</div></div>`).join("")}
    </div>
    ${noteHtml}
  `;
  document.getElementById("modalOverlay").classList.add("open");
}

function closeModal() {
  document.getElementById("modalOverlay").classList.remove("open");
}

init();

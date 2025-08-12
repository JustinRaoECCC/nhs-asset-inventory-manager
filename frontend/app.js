// Minimal helper to POST a file to an endpoint
async function uploadExcel(endpoint, fileInput, statusEl) {
  const file = fileInput.files[0];
  if (!file) {
    statusEl.textContent = "Please choose an Excel file first.";
    return null;
  }
  statusEl.textContent = "Uploading and parsing...";
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(endpoint, { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    statusEl.textContent = `Error: ${err.detail || res.statusText}`;
    return null;
  }
  const data = await res.json();
  statusEl.textContent = "Success.";
  return data.inventory;
}

// Render a collapsible tree: Station -> (Attributes, Assets -> Asset attrs)
function renderInventoryTree(inv, container) {
  container.innerHTML = "";
  if (!inv || !inv.stations || inv.stations.length === 0) {
    container.innerHTML = "<p class='muted'>No stations found.</p>";
    return;
  }

  const frag = document.createDocumentFragment();

  inv.stations
    .slice()
    .sort((a, b) => (a.station_id > b.station_id ? 1 : -1))
    .forEach(st => {
      const station = document.createElement("details");
      station.className = "node";
      station.open = false;

      const summary = document.createElement("summary");
      // Asset Inventory: show ONLY the station number. HYDEX: show name • id.
      const nameHeader = inv.source === "asset_inventory"
        ? `${st.station_id}`
        : `${st.station_name || "(Unnamed Station)"} • ${st.station_id}`;
      summary.innerHTML = `<strong>${nameHeader}</strong>`;
      station.appendChild(summary);

      // Attributes
      const attrWrap = document.createElement("details");
      attrWrap.className = "node inner";
      attrWrap.open = false;
      const attrSum = document.createElement("summary");
      attrSum.textContent = "Attributes";
      attrWrap.appendChild(attrSum);

      if (st.attributes && Object.keys(st.attributes).length) {
        const table = document.createElement("table");
        table.className = "kv";
        Object.entries(st.attributes).forEach(([k, v]) => {
          const tr = document.createElement("tr");
          const tdK = document.createElement("td");
          const tdV = document.createElement("td");
          tdK.textContent = k;
          tdV.textContent = String(v);
          tr.appendChild(tdK);
          tr.appendChild(tdV);
          table.appendChild(tr);
        });
        attrWrap.appendChild(table);
      } else {
        const p = document.createElement("p");
        p.className = "muted";
        p.textContent = "No attributes.";
        attrWrap.appendChild(p);
      }
      station.appendChild(attrWrap);

      // Assets
      const assetsWrap = document.createElement("details");
      assetsWrap.className = "node inner";
      assetsWrap.open = true;
      const assetsSum = document.createElement("summary");
      assetsSum.textContent = `Assets (${(st.assets || []).length})`;
      assetsWrap.appendChild(assetsSum);

      if (st.assets && st.assets.length) {
        st.assets
          .slice()
          .sort((a, b) => (a.type > b.type ? 1 : -1))
          .forEach(a => {
            const aNode = document.createElement("details");
            aNode.className = "node inner2";
            aNode.open = false;
            const aSum = document.createElement("summary");
            aSum.innerHTML = `<span class="badge">${a.type}</span>`;
            aNode.appendChild(aSum);

            const tbl = document.createElement("table");
            tbl.className = "kv";
            const attrs = a.attributes || {};
            if (Object.keys(attrs).length === 0) {
              const p = document.createElement("p");
              p.className = "muted";
              p.textContent = "No attributes for this asset.";
              aNode.appendChild(p);
            } else {
              Object.entries(attrs).forEach(([k, v]) => {
                const tr = document.createElement("tr");
                const tdK = document.createElement("td");
                const tdV = document.createElement("td");
                tdK.textContent = k;
                tdV.textContent = String(v);
                tr.appendChild(tdK);
                tr.appendChild(tdV);
                tbl.appendChild(tr);
              });
              aNode.appendChild(tbl);
            }
            assetsWrap.appendChild(aNode);
          });
      } else {
        const p = document.createElement("p");
        p.className = "muted";
        p.textContent = "No assets detected.";
        assetsWrap.appendChild(p);
      }

      station.appendChild(assetsWrap);
      frag.appendChild(station);
    });

  container.appendChild(frag);
}

function renderComparison(result, container) {
  container.innerHTML = "";
  if (!result || !result.details) {
    container.innerHTML = "<p class='muted'>No comparison available.</p>";
    return;
  }

  const summary = document.createElement("div");
  summary.className = "summary";
  summary.innerHTML = `
    <div><strong>Total stations compared:</strong> ${result.summary.stations_compared}</div>
    <div><strong>Stations with discrepancies:</strong> ${result.summary.stations_with_discrepancies}</div>
  `;
  container.appendChild(summary);

  if (result.details.length === 0) {
    container.innerHTML += "<p class='ok'>No discrepancies found 🎉</p>";
    return;
  }

  const list = document.createElement("div");
  list.className = "diff-list";

  result.details.forEach(d => {
    const card = document.createElement("div");
    card.className = "diff-card";

    const header = document.createElement("div");
    header.className = "diff-header";
    header.innerHTML = `
      <div class="id">${d.station_id}</div>
      <div class="names">
        <span title="${d.source_left}">${d.station_name_left || "—"}</span>
        <span class="sep">↔</span>
        <span title="${d.source_right}">${d.station_name_right || "—"}</span>
      </div>
    `;
    card.appendChild(header);

    const grids = document.createElement("div");
    grids.className = "diff-grids";

    const left = document.createElement("div");
    const leftHasAssets = Array.isArray(d.assets_left) && d.assets_left.length > 0;
    const leftAssetsHTML = leftHasAssets
      ? `<ul class="chips">${d.assets_left.map(a => `<li>${a}</li>`).join("")}</ul>`
      : `<div class="muted">No assets detected in ${d.source_left}.</div>`;
    const leftMissingHTML = (Array.isArray(d.missing_in_right) && d.missing_in_right.length > 0)
      ? `<div class="miss">
           <strong>Missing in ${d.source_right}:</strong>
          <ul class="chips warn">${d.missing_in_right.map(a => `<li>${a}</li>`).join("")}</ul>
         </div>`
      : "";
    left.innerHTML = `<h4>${d.source_left}</h4>${leftAssetsHTML}${leftMissingHTML}`;
    grids.appendChild(left);

    const right = document.createElement("div");
    const rightHasAssets = Array.isArray(d.assets_right) && d.assets_right.length > 0;
    const rightAssetsHTML = rightHasAssets
      ? `<ul class="chips">${d.assets_right.map(a => `<li>${a}</li>`).join("")}</ul>`
      : `<div class="muted">No assets detected in ${d.source_right}.</div>`;
    const rightMissingHTML = (Array.isArray(d.missing_in_left) && d.missing_in_left.length > 0)
      ? `<div class="miss">
           <strong>Missing in ${d.source_left}:</strong>
           <ul class="chips warn">${d.missing_in_left.map(a => `<li>${a}</li>`).join("")}</ul>
         </div>`
      : "";
    right.innerHTML = `<h4>${d.source_right}</h4>${rightAssetsHTML}${rightMissingHTML}`;
    grids.appendChild(right);

    // If both sides have no assets and no missing items, collapse the card body.
    const nothingToShow =
      !leftHasAssets && !rightHasAssets &&
      (!d.missing_in_left || d.missing_in_left.length === 0) &&
      (!d.missing_in_right || d.missing_in_right.length === 0);
    if (nothingToShow) {
      const p = document.createElement("p");
      p.className = "muted";
      p.textContent = "Neither source lists any assets for this station.";
      card.appendChild(p);
    } else {
      card.appendChild(grids);
    }
    list.appendChild(card);
  });

  container.appendChild(list);
}

window.addEventListener("DOMContentLoaded", () => {
  const fileA = document.getElementById("fileA");
  const fileB = document.getElementById("fileB");
  const uploadA = document.getElementById("uploadA");
  const uploadB = document.getElementById("uploadB");
  const missingBtn = document.getElementById("missingBtn");
  const statusA = document.getElementById("statusA");
  const statusB = document.getElementById("statusB");
  const treeA = document.getElementById("treeA");
  const treeB = document.getElementById("treeB");
  const compareBtn = document.getElementById("compareBtn");
  const compareStatus = document.getElementById("compareStatus");
  const results = document.getElementById("results");
  const missingTable = document.getElementById("missingTable");
  const exportMissingBtn = document.getElementById("exportMissingBtn");
  const tabBtnCompare = document.getElementById("tabBtnCompare");
  const tabBtnMissing = document.getElementById("tabBtnMissing");
  const resultsPane = document.getElementById("resultsPane");
  const missingPane = document.getElementById("missingPane");

  let invA = null, invB = null;
  let missingRows = [];

  function switchTab(targetId){
    // buttons
    [tabBtnCompare, tabBtnMissing].forEach(btn => btn.classList.remove("active"));
    const targetBtn = targetId === "resultsPane" ? tabBtnCompare : tabBtnMissing;
    targetBtn.classList.add("active");
    // panes
    [resultsPane, missingPane].forEach(p => p.classList.remove("active"));
    (targetId === "resultsPane" ? resultsPane : missingPane).classList.add("active");
  }

  tabBtnCompare.addEventListener("click", () => switchTab("resultsPane"));
  tabBtnMissing.addEventListener("click", () => switchTab("missingPane"));

  uploadA.addEventListener("click", async () => {
    invA = await uploadExcel("/api/upload/asset_inventory", fileA, statusA);
    if (invA) renderInventoryTree(invA, treeA);
  });

  uploadB.addEventListener("click", async () => {
    invB = await uploadExcel("/api/upload/hydex", fileB, statusB);
    if (invB) renderInventoryTree(invB, treeB);
  });

  compareBtn.addEventListener("click", async () => {
    compareStatus.textContent = "Comparing...";
    const res = await fetch("/api/compare");
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      compareStatus.textContent = `Error: ${err.detail || res.statusText}`;
      return;
    }
    compareStatus.textContent = "";
    const data = await res.json();
    renderComparison(data, results);
    results.scrollIntoView({ behavior: "smooth", block: "start" });
    switchTab("resultsPane");
  });

  function renderMissingTable(rows, container){
    container.innerHTML = "";
    if (!rows || rows.length === 0){
      container.innerHTML = "<p class='muted'>No HYDEX-only stations found.</p>";
      return;
    }
    const table = document.createElement("table");
    table.className = "data";
    const thead = document.createElement("thead");
    thead.innerHTML = `
      <tr>
        <th>Station ID</th>
        <th>Station Name</th>
        <th>Province</th>
        <th>Office</th>
        <th>Tech Name</th>
      </tr>`;
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    rows.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r.station_id || ""}</td>
        <td>${r.station_name || ""}</td>
        <td>${r.province || ""}</td>
        <td>${r.office || ""}</td>
        <td>${r.tech_name || ""}</td>`;
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    container.appendChild(table);
  }

  missingBtn.addEventListener("click", async () => {
    compareStatus.textContent = "Building HYDEX-only list...";
    const res = await fetch("/api/missing_stations");
    if (!res.ok){
      const err = await res.json().catch(()=>({}));
      compareStatus.textContent = `Error: ${err.detail || res.statusText}`;
      return;
    }
    compareStatus.textContent = "";
    const payload = await res.json();
    missingRows = payload.rows || [];
    renderMissingTable(missingRows, missingTable);
    switchTab("missingPane");
    missingPane.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  exportMissingBtn.addEventListener("click", async () => {
    // If running inside the desktop app (pywebview), use native Save As...
    if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.save_missing_stations_excel === "function") {
      try {
        const resp = await window.pywebview.api.save_missing_stations_excel();
        if (resp && resp.ok) {
          alert(`Saved to:\n${resp.path}`);
        } else if (resp && resp.cancelled) {
          // user cancelled — do nothing
        } else {
          alert(`Export failed: ${resp && resp.error ? resp.error : "Unknown error"}`);
        }
      } catch (e) {
        alert(`Export failed: ${e.message || e}`);
      }
      return;
    }

    // Fallback for normal browsers: stream from backend and trigger download
    try {
      const res = await fetch("/api/export/missing_stations.xlsx");
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Export failed: ${err.detail || res.statusText}`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "hydex_only_stations.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Export failed.");
    }
  });

});


/* Academic Pathway Copilot — prerequisite graph controller */
(() => {
  const service = {
    async openGraph(courseCode) {
      const modal = document.getElementById("prerequisite-modal");
      const loading = document.getElementById("graph-loading");
      const content = document.getElementById("graph-content");
      const error = document.getElementById("graph-error");
      const code = String(courseCode || "CS401").toUpperCase();

      modal?.classList.remove("hidden");
      loading?.classList.remove("hidden");
      content?.classList.add("hidden");
      error?.classList.add("hidden");

      const course = App.getCourse(code);
      setText("modal-course-title", `Prerequisite Knowledge Graph — ${code}`);
      setText("modal-course-subtitle", course?.name
        ? `${course.name} • Live prerequisite data from Neo4j`
        : "Live prerequisite data from Neo4j");

      try {
        const res = await fetch(`${App.API_BASE}/courses/${encodeURIComponent(code)}/prerequisites`, { cache: "no-store" });
        if (!res.ok) {
          let detail = "";
          try { detail = (await res.json())?.detail || ""; } catch {}
          throw new Error(detail || `Graph request failed (${res.status})`);
        }
        const data = await res.json();
        renderGraph(code, data?.prerequisites || []);
        loading?.classList.add("hidden");
        content?.classList.remove("hidden");
      } catch (err) {
        console.error(err);
        loading?.classList.add("hidden");
        error?.classList.remove("hidden");
        setText("graph-error-text", err?.message || "Unable to retrieve prerequisites.");
      } finally {
        lucide.createIcons();
      }
    }
  };

  window.GraphService = service;

  function renderGraph(targetCode, prerequisites) {
    const canvas = document.getElementById("graph-canvas");
    const list = document.getElementById("graph-list");
    if (!canvas || !list) return;

    const completed = App.state.completedCodes;
    const unique = [...new Set((prerequisites || []).map(String).map(x => x.toUpperCase()))]
      .filter(code => code !== targetCode);

    // The current backend returns a prerequisite code set, not edge-by-edge ordering.
    // Therefore the UI presents a readable dependency chain/set without inventing relationships.
    if (!unique.length) {
      canvas.innerHTML = `
        <div class="graph-node target">
          <div class="text-[9px] font-bold uppercase tracking-wider text-cyan-300">Target course</div>
          <div class="mt-1 font-display text-sm font-bold text-white">${App.escapeHtml(targetCode)}</div>
          <div class="mt-1 text-[9px] text-slate-500">No prerequisites returned by the graph API.</div>
        </div>
      `;
    } else {
      canvas.innerHTML = `
        ${unique.map(code => `
          <div class="graph-node ${completed.has(code) ? "completed" : "missing"}">
            <div class="flex items-center justify-center gap-2">
              <i data-lucide="${completed.has(code) ? "check-circle-2" : "circle-alert"}" class="h-3.5 w-3.5 ${completed.has(code) ? "text-emerald-300" : "text-rose-300"}"></i>
              <span class="font-display text-sm font-bold">${App.escapeHtml(code)}</span>
            </div>
            <div class="mt-1 text-[9px] ${completed.has(code) ? "text-emerald-300" : "text-rose-300"}">
              ${completed.has(code) ? "Completed / satisfied" : "Missing prerequisite"}
            </div>
          </div>
          <div class="graph-arrow"></div>
        `).join("")}
        <div class="graph-node target">
          <div class="text-[9px] font-bold uppercase tracking-wider text-cyan-300">Target course</div>
          <div class="mt-1 font-display text-sm font-bold text-white">${App.escapeHtml(targetCode)}</div>
          <div class="mt-1 text-[9px] text-cyan-200">Prerequisite requirement set</div>
        </div>
      `;
    }

    list.innerHTML = unique.length
      ? unique.map(code => {
          const isDone = completed.has(code);
          const c = App.getCourse(code);
          return `
            <div class="flex items-center justify-between rounded-lg border ${isDone ? "border-emerald-400/15 bg-emerald-400/[0.04]" : "border-rose-400/15 bg-rose-400/[0.04]"} px-3 py-2">
              <span class="text-[10px] font-semibold">${App.escapeHtml(code)}${c?.name ? ` — ${App.escapeHtml(c.name)}` : ""}</span>
              <span class="text-[9px] ${isDone ? "text-emerald-300" : "text-rose-300"}">${isDone ? "Satisfied" : "Missing"}</span>
            </div>
          `;
        }).join("")
      : `<div class="col-span-full text-center text-[10px] text-slate-500">No prerequisite records returned.</div>`;

    lucide.createIcons();
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }
})();

/* KamaraTudás — static demo UI (no build step). Vanilla JS against /api. */
"use strict";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (_) { /* no JSON body */ }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

/* ---- toast ---- */
let _toastTimer = null;
function toast(msg, kind = "ok") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast " + kind;
  t.hidden = false;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { t.hidden = true; }, 4200);
}

/* ---- scope ---- */
function getScope() {
  return {
    organization_id: $("#scope-org").value,
    department: $("#scope-dept").value,
    role: $("#scope-role").value,
  };
}

/* ---- tabs ---- */
function activateTab(name) {
  $$(".tab").forEach((b) => {
    const on = b.dataset.tab === name;
    b.classList.toggle("is-active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  });
  $$(".tab-panel").forEach((p) => {
    const on = p.id === "panel-" + name;
    p.classList.toggle("is-active", on);
    p.hidden = !on;
  });
  $("#scope-bar").style.display = name === "gaps" ? "none" : "flex";
  if (name === "gaps") loadAnalytics();
}
$$(".tab").forEach((b) => b.addEventListener("click", () => activateTab(b.dataset.tab)));

/* ---- corpus header + upload ---- */
async function refreshCorpus() {
  try {
    const docs = await api("/api/documents");
    const n = docs.length;
    $("#corpus-chip").textContent = `Korpusz: ${n} dokumentum`;
    $("#corpus-chip").title = docs.map((d) => `${d.document_name} · ${d.page_count} oldal`).join("\n");
  } catch (e) {
    $("#corpus-chip").textContent = "Korpusz: nem elérhető";
  }
}

async function uploadPdf(file) {
  const fd = new FormData();
  fd.append("file", file);
  toast("PDF feltöltése és indexelése…");
  try {
    const meta = await api("/api/documents", { method: "POST", body: fd });
    toast(`Kész: „${meta.document_name}” indexelve (${meta.page_count} oldal, ${meta.chunk_count} szegmens). Szakértő hívása nélkül.`);
    await refreshCorpus();
  } catch (e) {
    toast(`Feltöltés sikertelen: ${e.message}`, "err");
  } finally {
    $("#file-upload").value = "";
  }
}
$("#file-upload").addEventListener("change", (e) => {
  const f = e.target.files && e.target.files[0];
  if (f) uploadPdf(f);
});

/* ---- Tab 1: Kérdés ---- */
function setAskBusy(busy) {
  $("#ask-btn").disabled = busy;
  $("#ask-btn .btn-label").hidden = busy;
  $("#ask-btn .spin").hidden = !busy;
  $("#ask-input").disabled = busy;
}

async function ask(question) {
  setAskBusy(true);
  $("#ask-result").hidden = true;
  try {
    const resp = await api("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, scope: getScope() }),
    });
    renderAsk(resp);
  } catch (e) {
    toast(`Hiba a kérdezés közben: ${e.message}`, "err");
  } finally {
    setAskBusy(false);
  }
}

function statusLabel(status) {
  return {
    supported: "Megválaszolva",
    partial: "Részlegesen megválaszolva",
    insufficient_evidence: "Nincs elegendő fedezet",
  }[status] || status;
}

function renderAnswerText(text) {
  let html = esc(text).replace(/\r?\n/g, "<br>");
  html = html.replace(/\[(\d+)\]/g, '<button class="cite-chip" data-cite="$1">$1</button>');
  return html;
}

function renderWarnings(warnings) {
  return warnings.map((w) => {
    const anchors = [];
    const link = (c, label) =>
      `<button class="link-like" data-cite-doc="${esc(c.document_id)}" data-cite-page="${c.page}"
         data-cite-snippet="${esc(c.excerpt)}" data-cite-section="${esc(c.section || "")}"
         data-cite-document="${esc(c.document)}">${label}</button>`;
    if (w.older) anchors.push(link(w.older, "Régebbi »"));
    if (w.newer) anchors.push(link(w.newer, "Újabb »"));
    return `<div class="warn">
      <p class="warn-title">⚠️ Ellentmondó / eltérő hatályú források</p>
      <p class="warn-line">${esc(w.message)}${anchors.length ? (anchors.length === 2
        ? ` <span class="muted">—</span> ${anchors[0]} <span class="muted">·</span> ${anchors[1]}`
        : ` <span class="muted">—</span> ${anchors[0]}`) : ""}</p>
    </div>`;
  }).join("");
}

function renderCitations(citations) {
  return citations.map((c) => `
    <div class="evidence-item">
      <div class="evidence-doc">
        <strong>${esc(c.document)}</strong>
        ${c.section ? `<span class="doc-sect">${esc(c.section)}</span>` : ""}
        <span class="doc-page">· ${c.page}. oldal</span>
        ${c.version ? `<span class="doc-page">· v${esc(c.version)}</span>` : ""}
      </div>
      <p class="evidence-excerpt">„${esc(c.excerpt)}”</p>
      <button class="link-like" data-cite-doc="${esc(c.document_id)}" data-cite-page="${c.page}"
        data-cite-section="${esc(c.section || "")}" data-cite-document="${esc(c.document)}"
        data-cite-snippet="${esc(c.excerpt)}">Forrás megnyitása →</button>
    </div>`).join("");
}

function renderAsk(resp) {
  const panel = $("#ask-result");
  const refused = resp.status === "insufficient_evidence";

  let html = `<div class="answer-card">`;

  if (refused) {
    html += `
      <div class="answer-head">
        <span class="badge badge-none">${esc(resp.coverage_label)}</span>
        <span class="answer-status">${statusLabel(resp.status)}</span>
      </div>
      <div class="abstain">
        <p class="abstain-text"><span aria-hidden="true">⊗</span> ${esc(resp.answer)}</p>
        ${resp.suggestion ? `<p class="suggestion">${esc(resp.suggestion)}</p>` : ""}
      </div>`;
    if (resp.unsupported_parts && resp.unsupported_parts.length) {
      html += `<p class="suggestion">Akéntes részek: ${resp.unsupported_parts.map(esc).join("; ")}</p>`;
    }
  } else {
    html += `
      <div class="answer-head">
        <span class="badge badge-${esc(resp.coverage)}">${esc(resp.coverage_label)}</span>
        <span class="answer-status">${statusLabel(resp.status)}</span>
      </div>
      ${resp.warnings && resp.warnings.length ? renderWarnings(resp.warnings) : ""}
      <p class="answer-text cited">${renderAnswerText(resp.answer)}</p>`;
    if (resp.suggestion) {
      html += `<p class="suggestion">${esc(resp.suggestion)}</p>`;
    }
    if (resp.citations && resp.citations.length) {
      html += `<div class="evidence-head">Bizonyítékok — minden állítás visszavezethető</div>`;
      html += renderCitations(resp.citations);
    }
  }

  html += `<div class="trace">vizsgált: ${resp.retrieval.documents_considered} dokumentum /
            ${resp.retrieval.chunks_considered} szegmens · top score: ${resp.retrieval.top_score.toFixed(3)}
            · gate: ${esc(resp.retrieval.gate_reason)}</div>`;
  html += `</div>`;

  panel.innerHTML = html;
  panel.hidden = false;

  panel.querySelectorAll(".cite-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const c = resp.citations.find((x) => x.id === chip.dataset.cite);
      if (c) openDrawer(c);
    });
  });
  panel.querySelectorAll("[data-cite-doc]").forEach((btn) => {
    btn.addEventListener("click", () => openDrawer({
      document_id: btn.dataset.citeDoc,
      document: btn.dataset.citeDocument,
      page: Number(btn.dataset.citePage),
      section: btn.dataset.citeSection || null,
      excerpt: btn.dataset.citeSnippet || "",
    }));
  });
}

$("#ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("#ask-input").value.trim();
  if (q) ask(q);
});

/* ---- Tab 2: Válasz-ellenőrzés ---- */
function setVerifyBusy(busy) {
  $("#verify-btn").disabled = busy;
  $("#verify-btn .btn-label").hidden = busy;
  $("#verify-btn .spin").hidden = !busy;
  $("#verify-input").disabled = busy;
}

async function verify(draft) {
  setVerifyBusy(true);
  $("#verify-result").hidden = true;
  try {
    const resp = await api("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft, scope: getScope() }),
    });
    renderVerify(resp);
  } catch (e) {
    toast(`Hiba az ellenőrzés közben: ${e.message}`, "err");
  } finally {
    setVerifyBusy(false);
  }
}

function verdictLabel(v) {
  return { supported: "Alátámasztott", unsupported: "Nincs fedezet", conflicting: "Ellentmondás" }[v] || v;
}

function renderVerify(resp) {
  const panel = $("#verify-result");
  const claims = resp.claims || [];

  const citeAnchor = (c) => `
    <button class="link-like" data-cite-doc="${esc(c.document_id)}" data-cite-page="${c.page}"
      data-cite-section="${esc(c.section || "")}" data-cite-document="${esc(c.document)}"
      data-cite-snippet="${esc(c.excerpt)}">${esc(c.document)} · ${c.page}. old.</button>`;

  const claimsHtml = claims.map((cl) => `
    <div class="claim">
      <div class="claim-head">
        <span class="verdict verdict-${esc(cl.verdict)}">${verdictLabel(cl.verdict)}</span>
        <p class="claim-text">${esc(cl.claim)}</p>
      </div>
      ${cl.rationale ? `<p class="claim-rationale">${esc(cl.rationale)}</p>` : ""}
      ${cl.citations && cl.citations.length ? `
        <div class="claim-cites">
          <p class="claim-cites-summary">Források:</p>
          ${cl.citations.map(citeAnchor).join(" · ")}
        </div>` : ""}
    </div>`).join("") || `<p class="empty-state">A rendszer nem tudott tényállításokat bontani ebből a tervezetből.</p>`;

  panel.innerHTML = `
    <div class="verify-summary">${resp.summary ? esc(resp.summary)
      : "Az ellenőrzés kész — nézze át az állításonkénti minősítéseket."}</div>
    ${claimsHtml}`;
  panel.hidden = false;

  panel.querySelectorAll("[data-cite-doc]").forEach((btn) => {
    btn.addEventListener("click", () => openDrawer({
      document_id: btn.dataset.citeDoc,
      document: btn.dataset.citeDocument,
      page: Number(btn.dataset.citePage),
      section: btn.dataset.citeSection || null,
      excerpt: btn.dataset.citeSnippet || "",
    }));
  });
}

$("#verify-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const d = $("#verify-input").value.trim();
  if (d) verify(d);
});

/* ---- Tab 3: Tudáshiány-térkép ---- */
async function loadAnalytics() {
  const loading = $("#gaps-loading");
  const content = $("#gaps-content");
  loading.hidden = false;
  content.hidden = true;
  try {
    const data = await api("/api/analytics?limit=10");
    renderAnalytics(data);
    content.hidden = false;
  } catch (e) {
    toast(`Nem sikerült betölteni a tudáshiány-térképet: ${e.message}`, "err");
  } finally {
    loading.hidden = true;
  }
}

function statRow(s) {
  return `<li><span title="${esc(s.question)}">${esc(s.question)}</span>
          <span class="count-num">${s.count}×</span></li>`;
}

function renderAnalytics(data) {
  $("#gap-rate").textContent = data.total_questions ? `${(data.answer_rate * 100).toLocaleString("hu-HU", { maximumFractionDigits: 0 })}%` : "–";
  $("#gap-total").textContent = data.total_questions;
  $("#gap-nocov").textContent = data.insufficient;

  const top = $("#gap-top");
  top.innerHTML = data.top_questions && data.top_questions.length
    ? data.top_questions.map(statRow).join("")
    : `<li class="empty-state">Még nincs rögzített kérdés.</li>`;

  const unanswered = $("#gap-unanswered");
  unanswered.innerHTML = data.top_unanswered && data.top_unanswered.length
    ? data.top_unanswered.map(statRow).join("")
    : `<li class="empty-state">Minden rögzített kérdésre volt elegendő fedezet — a korpusz jól lefedi a feltett kérdéseket.</li>`;

  $("#gap-dept").innerHTML = renderDeptBars(data.by_department || {});
}

function renderDeptBars(byDept) {
  const entries = Object.entries(byDept);
  if (!entries.length) return `<p class="empty-state">Még nincs osztály szerinti adat.</p>`;
  const max = Math.max(...entries.map(([, n]) => n));
  const label = {
    altalanos: "Általános", beszerzes: "Beszerzés", penzugy: "Pénzügy", hr: "HR",
  };
  return entries.map(([dept, n]) => `
    <div class="bar-row">
      <span>${esc(label[dept] || dept)}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${max ? (100 * n / max) : 0}%"></div></div>
      <span class="bar-num">${n}</span>
    </div>`).join("");
}

/* ---- Forrás-néző drawer ---- */
function openDrawer(citation) {
  const id = citation.document_id;
  const page = citation.page;

  $("#drawer-title").textContent = citation.document || "Forrás";
  const metaBit = [];
  if (citation.section) metaBit.push(esc(citation.section));
  metaBit.push(`${page}. oldal`);
  if (citation.version) metaBit.push(`verzió: ${esc(citation.version)}`);
  $("#drawer-meta").innerHTML = metaBit.join(" · ");

  $("#drawer-loading").hidden = false;
  $("#drawer-content").hidden = true;
  document.body.classList.add("drawer-open");
  $("#drawer-backdrop").hidden = false;
  $("#drawer").setAttribute("aria-hidden", "false");

  (async () => {
    try {
      const pg = await api(`/api/documents/${encodeURIComponent(id)}/page/${page}`);
      $("#drawer-page-text").textContent = pg.text || "Az oldal indexelt szövege üres.";
      const img = $("#drawer-page-img");
      img.alt = `${pg.document} — ${page}. oldal`;
      const params = new URLSearchParams({ dpi: "140" });
      if (citation.excerpt) params.set("highlight", citation.excerpt);
      img.onload = () => { $("#drawer-loading").hidden = true; $("#drawer-content").hidden = false; };
      img.onerror = () => {
        $("#drawer-loading").hidden = true;
        $("#drawer-content").hidden = false;
        img.hidden = true;
        document.querySelector(".page-figure figcaption").textContent =
          "Az oldalkép nem renderelhető (az eredeti PDF nem elérhető?), a szöveges forrás azonban elérhető alább.";
      };
      img.src = `${pg.render_url}?${params.toString()}`;
    } catch (e) {
      $("#drawer-loading").hidden = true;
      toast(`A forrás nem nyitható meg: ${e.message}`, "err");
    }
  })();

  $("#drawer-backdrop").onclick = closeDrawer;
  $("#drawer-close").onclick = closeDrawer;
}

function closeDrawer() {
  document.body.classList.remove("drawer-open");
  $("#drawer-backdrop").hidden = true;
  $("#drawer").setAttribute("aria-hidden", "true");
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

/* ---- init ---- */
refreshCorpus();
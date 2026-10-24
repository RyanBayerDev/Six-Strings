/* Six Strings frontend */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const view = $("#view");
let api = null;          // alphaTab instance
let current = null;      // current song data
let chatHistory = [];
let libraryCache = null;

const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function md(text) {
  // tiny markdown: **bold**, `code`, numbered/bullet lists, paragraphs
  const lines = esc(text).split(/\n/);
  let html = "", list = null;
  const close = () => { if (list) { html += `</${list}>`; list = null; } };
  for (let raw of lines) {
    let l = raw.trim();
    l = l.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/^#{1,4}\s*(.*)$/, "<b>$1</b>");
    let m;
    if ((m = l.match(/^\d+[.)]\s+(.*)/))) { if (list !== "ol") { close(); html += "<ol>"; list = "ol"; } html += `<li>${m[1]}</li>`; }
    else if ((m = l.match(/^[-*•]\s+(.*)/))) { if (list !== "ul") { close(); html += "<ul>"; list = "ul"; } html += `<li>${m[1]}</li>`; }
    else if (!l) { close(); }
    else { close(); html += `<p>${l}</p>`; }
  }
  close();
  return html;
}

function meterBars(score) {
  const n = Math.round(score);
  return `<div class="frets">${Array.from({ length: 10 }, (_, i) => `<i class="${i < n ? "on" : ""}"></i>`).join("")}</div>`;
}

/* ------------------------------------------------ coach status */
async function checkCoach() {
  const pill = $("#coachPill");
  try {
    const s = await (await fetch("/api/coach/status")).json();
    pill.classList.toggle("ok", s.online && s.installed);
    pill.classList.toggle("bad", !s.online || !s.installed);
    $("#coachPillText").textContent = s.online ? (s.installed ? `Coach: ${s.model}` : `Pull ${s.model}`) : "Coach offline";
    return s;
  } catch { pill.classList.add("bad"); $("#coachPillText").textContent = "Coach offline"; return {}; }
}

/* ------------------------------------------------ router */
function destroyPlayer() { if (api) { try { api.destroy(); } catch {} api = null; } }
async function route() {
  destroyPlayer();
  const h = location.hash || "#/";
  $$("nav a").forEach(a => a.classList.toggle("on", (a.dataset.nav === "upload") === h.startsWith("#/upload")));
  if (h.startsWith("#/song/")) return showSong(decodeURIComponent(h.slice(7)));
  if (h.startsWith("#/upload")) return showUpload();
  return showLibrary();
}
window.addEventListener("hashchange", route);

/* ------------------------------------------------ library */
async function showLibrary() {
  view.innerHTML = $("#tpl-library").innerHTML;
  let level = "all", q = "";
  const draw = () => {
    const items = (libraryCache || []).filter(s => (level === "all" || s.level === level) &&
      (s.title + " " + (s.composer || "")).toLowerCase().includes(q));
    $("#grid").innerHTML = items.length ? items.map(s => `
      <a class="card-song lvl-card-${s.level}" href="#/song/${encodeURIComponent(s.id)}">
        <div class="card-top">
          <div><h3>${esc(s.title)}</h3><div class="by">${esc(s.composer || (s.source !== "library" ? "Uploaded · " + s.source : ""))}</div></div>
          <div class="num">${s.score.toFixed(1)}<small>/10</small></div>
        </div>
        ${meterBars(s.score)}
        <ul>${s.top_reasons.map(r => `<li>${esc(r)}</li>`).join("")}</ul>
        <div class="card-foot"><span class="pill lvl-${s.level}">${s.level}</span><span>${s.tempo} BPM · ${s.time_signature} · ${s.measures} bars</span></div>
        ${s.source !== "library" ? `<button class="del-btn" data-del="${esc(s.id)}" data-title="${esc(s.title)}" title="Delete this upload">Delete</button>` : ""}
      </a>`).join("") : `<div class="loading">No songs match.</div>`;
    $$("[data-del]").forEach(b => b.onclick = async e => {
      e.preventDefault(); e.stopPropagation();
      if (await deleteSong(b.dataset.del, b.dataset.title)) draw();
    });
  };
  $$(".chip").forEach(c => c.onclick = () => { $$(".chip").forEach(x => x.classList.remove("active")); c.classList.add("active"); level = c.dataset.level; draw(); });
  $("#search").oninput = e => { q = e.target.value.toLowerCase(); draw(); };
  try {
    libraryCache = await (await fetch("/api/songs")).json();
    draw();
  } catch (e) { $("#grid").innerHTML = `<div class="error">Couldn't load the library: ${esc(e)}</div>`; }
}

async function deleteSong(id, title) {
  if (!confirm(`Delete "${title}" from the library?\n\nThis removes the uploaded file. Built-in songs can't be deleted.`)) return false;
  try {
    const r = await fetch(`/api/songs/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!r.ok) throw new Error((await r.json()).detail || "Delete failed");
    if (libraryCache) libraryCache = libraryCache.filter(s => s.id !== id);
    return true;
  } catch (e) { alert("Couldn't delete: " + e.message); return false; }
}

/* ------------------------------------------------ upload */
function showUpload() {
  view.innerHTML = $("#tpl-upload").innerHTML;
  const drop = $("#drop"), input = $("#file");
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => e.dataTransfer.files[0] && doUpload(e.dataTransfer.files[0]));
  input.onchange = () => input.files[0] && doUpload(input.files[0]);
}

async function doUpload(file) {
  const isImg = /\.(png|jpe?g|webp|bmp)$/i.test(file.name);
  $("#uploadErr").classList.add("hidden");
  $("#progress").classList.remove("hidden");
  const steps = $$(".step");
  steps.forEach(s => s.className = "step");
  if (!isImg) steps[0].classList.add("hidden"); else steps[0].classList.remove("hidden");
  let i = isImg ? 0 : 1;
  steps[i].classList.add("active");
  $("#progressNote").textContent = isImg ? "oemer runs a neural network over the page. This takes about 30–90 seconds on a laptop." : "";
  const t0 = Date.now();
  const timer = setInterval(() => { if (isImg) $("#progressNote").textContent = `oemer is reading the page… ${Math.round((Date.now() - t0) / 1000)}s`; }, 1000);
  const fd = new FormData(); fd.append("file", file);
  try {
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Upload failed");
    clearInterval(timer);
    for (let k = i; k < steps.length; k++) {
      steps[k].classList.remove("active"); steps[k].classList.add("done");
      if (steps[k + 1]) steps[k + 1].classList.add("active");
      await new Promise(res => setTimeout(res, 350));
    }
    libraryCache = null;
    location.hash = "#/song/" + encodeURIComponent(data.id);
  } catch (e) {
    clearInterval(timer);
    $("#progress").classList.add("hidden");
    const err = $("#uploadErr"); err.classList.remove("hidden"); err.textContent = e.message;
  }
}

/* ------------------------------------------------ song view */
let viewMode = "both", fingerMode = "standard";

async function showSong(id, keepChat = false) {
  view.innerHTML = $("#tpl-song").innerHTML;
  if (!keepChat) chatHistory = [];
  let d;
  try {
    const r = await fetch(`/api/songs/${encodeURIComponent(id)}?mode=${fingerMode}`);
    if (!r.ok) throw new Error((await r.json()).detail);
    d = await r.json();
  } catch (e) { view.innerHTML = `<div class="error">${esc(e.message)}</div>`; return; }
  current = d;
  const diff = d.difficulty;
  $("#sTitle").textContent = d.title;
  $("#sMeta").textContent = [d.composer, `${d.tempo} BPM`, d.time_signature, `key of ${d.key}`, `${d.measures} measures`].filter(Boolean).join(" · ");
  $("#sBadge").innerHTML = `<div class="num">${diff.score.toFixed(1)}<small>/10</small></div><span class="pill lvl-${diff.level}">${diff.level}</span>`;
  if (d.source !== "library") {
    const del = document.createElement("button");
    del.className = "btn del-song"; del.textContent = "Delete upload";
    del.onclick = async () => { if (await deleteSong(d.id, d.title)) location.hash = "#/"; };
    $(".song-head").appendChild(del);
  }
  $("#sScore2").textContent = `${diff.score.toFixed(1)}/10`;
  requestAnimationFrame(() => $("#meterFill").style.width = `${diff.score * 10}%`);
  $("#sReasons").innerHTML = diff.reasons.slice(0, 6).map(r =>
    `<li><div class="bar"><i style="width:${Math.max(6, r.weight * 100)}%"></i></div><span>${esc(r.text)}</span></li>`).join("");
  $("#sHard").innerHTML = diff.hardest_measures.map(h => `
    <div class="hard"><div><b>Measure ${h.measure}</b><div class="why">${esc(h.why)}</div></div>
    <div class="acts"><button class="btn sm" data-loop="${h.measure}">Loop it</button><button class="btn sm" data-ask="${h.measure}">Ask coach</button></div></div>`).join("");
  $$("[data-loop]").forEach(b => b.onclick = () => loopMeasure(+b.dataset.loop));
  $$("[data-ask]").forEach(b => b.onclick = () => ask({ kind: "measure", measure: +b.dataset.ask }, `How do I practice measure ${b.dataset.ask}?`));

  $$("#viewSeg button").forEach(b => { b.classList.toggle("on", b.dataset.v === viewMode); b.onclick = () => { viewMode = b.dataset.v; $$("#viewSeg button").forEach(x => x.classList.toggle("on", x === b)); renderTab(); }; });
  $$("#modeSeg button").forEach(b => { b.classList.toggle("on", b.dataset.m === fingerMode); b.onclick = () => { if (fingerMode === b.dataset.m) return; fingerMode = b.dataset.m; destroyPlayer(); showSong(id, true); }; });

  // coach
  $("#btnPlan").onclick = () => ask({ kind: "plan" }, "Build my practice plan");
  $$(".coach-actions [data-q]").forEach(b => b.onclick = () => ask({ kind: "chat", question: b.dataset.q }, b.dataset.q));
  $("#chatForm").onsubmit = e => { e.preventDefault(); const q = $("#chatInput").value.trim(); if (!q) return; $("#chatInput").value = ""; ask({ kind: "chat", question: q }, q); };
  checkCoach().then(s => $("#coachModel").textContent = s.online ? `${s.model} · local` : "offline");
  chatHistory.forEach(m => addMsg(m.role === "user" ? "user" : "ai", m.content));

  setupPlayer();
  renderTab();
}

function texFor(variant) {
  if (variant === "plain") return current.alphatex_plain;
  if (viewMode === "score") return current.alphatex_score;
  if (viewMode === "tabs") return current.alphatex.replace("\\staff {score tabs}", "\\staff {tabs}");
  return current.alphatex;
}

function showAscii(reason) {
  $("#alphaTab").classList.add("hidden");
  $("#renderMsg").classList.add("hidden");
  const pre = $("#asciiTab"); pre.classList.remove("hidden");
  pre.textContent = current.ascii;
  console.warn("Using text tab fallback:", reason);
}

let triedPlain = false;
function setupPlayer() {
  triedPlain = false;
  if (!window.alphaTab) { showAscii("alphaTab script not loaded"); return; }
  const el = $("#alphaTab");
  const base = {
    core: { fontDirectory: "/vendor/font/", engine: "svg" },
    display: { scale: 1.0, layoutMode: "page" },
    notation: { elements: { scoreTitle: false, scoreWordsAndMusic: false, effectTempo: true, guitarTuning: false } },
    player: { enablePlayer: true, enableCursor: true, enableUserInteraction: true,
              soundFont: "/vendor/soundfont/sonivox.sf2", scrollElement: $("#paperWrap"), scrollOffsetY: -40 },
  };
  // dark-mode sheet colors (falls back to default black-on-light if this alphaTab version rejects them)
  const darkRes = { mainGlyphColor: "#ece8e1", secondaryGlyphColor: "#a8a29a", staffLineColor: "#4a4642",
                    barSeparatorColor: "#5a5550", barNumberColor: "#d9c7a7", scoreInfoColor: "#ece8e1" };
  try {
    api = new alphaTab.AlphaTabApi(el, { ...base, display: { ...base.display, resources: darkRes } });
  } catch (e) {
    console.warn("dark sheet colors not supported, using defaults", e);
    $("#paperWrap").classList.add("light-paper");
    try { api = new alphaTab.AlphaTabApi(el, base); } catch (e2) { showAscii(e2); return; }
  }
  api.renderFinished.on(() => $("#renderMsg").classList.add("hidden"));
  api.error.on(e => {
    console.error("alphaTab error", e);
    if (!triedPlain) { triedPlain = true; try { api.tex(texFor("plain")); return; } catch {} }
    showAscii(e);
  });
  api.soundFontLoaded && api.soundFontLoaded.on(() => {});
  api.playerReady.on(() => { $("#btnPlay").disabled = false; $("#btnStop").disabled = false; });
  api.playerStateChanged.on(e => { $("#btnPlay").textContent = e.state === 1 ? "❚❚ Pause" : "▶ Play"; });
  $("#btnPlay").onclick = () => api.playPause();
  $("#btnStop").onclick = () => api.stop();
  $("#speed").oninput = e => { const v = +e.target.value; $("#speedVal").textContent = v + "%"; api.playbackSpeed = v / 100; };
  $("#btnLoop").onclick = e => { api.isLooping = !api.isLooping; e.target.classList.toggle("on", api.isLooping); if (!api.isLooping) api.playbackRange = null; };
  $("#btnMetro").onclick = e => { const on = !e.target.classList.contains("on"); e.target.classList.toggle("on", on); api.metronomeVolume = on ? 1 : 0; api.countInVolume = on ? 1 : 0; };
}

function renderTab() {
  if (!api) return;
  $("#renderMsg").classList.remove("hidden");
  try { api.tex(texFor()); } catch (e) {
    try { api.tex(texFor("plain")); } catch (e2) { showAscii(e2); }
  }
}

function loopMeasure(m) {
  if (!api || !api.score) return;
  try {
    const mb = api.score.masterBars[m - 1];
    const start = mb.start, end = mb.start + mb.calculateDuration();
    api.playbackRange = { startTick: start, endTick: end };
    api.isLooping = true;
    $("#btnLoop").classList.add("on");
    api.tickPosition = start;
    if (api.playerState !== 1) api.playPause();
  } catch (e) { console.warn("loop failed", e); }
}

/* ------------------------------------------------ chat */
function addMsg(who, text) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  if (who === "user") div.textContent = text; else div.innerHTML = md(text);
  $("#chat").appendChild(div);
  $("#chat").scrollTop = $("#chat").scrollHeight;
  return div;
}

let busy = false;
async function ask(payload, label) {
  if (busy || !current) return;
  busy = true;
  addMsg("user", label);
  const out = addMsg("ai", ""); out.classList.add("typing");
  let text = "";
  try {
    const r = await fetch("/api/coach", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ song_id: current.id, mode: fingerMode, history: chatHistory, ...payload }),
    });
    const reader = r.body.getReader(); const dec = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      text += dec.decode(value, { stream: true });
      out.innerHTML = md(text);
      $("#chat").scrollTop = $("#chat").scrollHeight;
    }
  } catch (e) { text = "Couldn't reach the coach: " + e.message; out.innerHTML = md(text); }
  out.classList.remove("typing");
  chatHistory.push({ role: "user", content: payload.question || label }, { role: "assistant", content: text });
  busy = false;
}

checkCoach();
setInterval(checkCoach, 15000);
route();

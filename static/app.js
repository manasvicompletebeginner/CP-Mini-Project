/*
 * app.js - Frontend logic. Talks to the Flask REST API using fetch().
 *
 * UNIT V (connected frontend):
 *   GET  /api/users/<u>/rooms     -> My Rooms + Previous Rooms
 *   POST /api/rooms               -> Create Room (JSON body)
 *   POST /api/rooms/<code>/join   -> Join Room
 *   POST /api/rooms/<code>/pay    -> Paid button
 *   GET  /api/users/<u>/summary   -> Pandas/NumPy analytics
 *   GET  /api/users/<u>/chart.png -> Matplotlib chart
 *   GET  /api/users/<u>/export.csv
 *
 * sessionStorage keeps the username per browser tab, so two tabs can act as
 * two different students during the demo.
 */

const state = {
  user: sessionStorage.getItem("splitter_user"),
  ownerOnly: false,
  activeTab: "home",
  pollTimer: null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const rupee = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
const money = (n) => rupee.format(Number(n || 0));

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function prettyDate(iso) {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? iso + "T00:00:00" : iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/* ---------- fetch wrapper: every API call goes through here ---------- */
async function api(path, { method = "GET", body } = {}) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || `Request failed (${res.status})`);
  return data;
}

let toastTimer;
function toast(message, type = "") {
  const el = $("#toast");
  el.textContent = message;
  el.className = `toast ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 3500);
}

/* ---------- login ---------- */
function showApp() {
  $("#login-screen").classList.add("hidden");
  $("#app-screen").classList.remove("hidden");
  $("#user-chip").classList.remove("hidden");
  $("#user-name").textContent = state.user;
  switchTab("home");
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await api("/api/login", { method: "POST", body: { username: $("#login-username").value } });
    state.user = data.username;
    sessionStorage.setItem("splitter_user", state.user);
    toast(data.new_user ? `Welcome, ${state.user}!` : `Welcome back, ${state.user}`, "success");
    showApp();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#logout-btn").addEventListener("click", () => {
  sessionStorage.removeItem("splitter_user");
  state.user = null;
  clearInterval(state.pollTimer);
  $("#app-screen").classList.add("hidden");
  $("#user-chip").classList.add("hidden");
  $("#login-screen").classList.remove("hidden");
  $("#login-username").value = "";
});

/* ---------- navigation ---------- */
function switchTab(name) {
  state.activeTab = name;
  $("#back-bar").classList.toggle("hidden", name === "home");
  $$(".tab-panel").forEach((p) => p.classList.toggle("hidden", p.id !== `tab-${name}`));

  clearInterval(state.pollTimer);
  if (name === "home") {
    loadMyRooms();
    state.pollTimer = setInterval(loadMyRooms, 5000);   // live "2/5 paid" updates
  }
  if (name === "previous") loadPrevious();
  if (name === "join") $("#join-code").focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

$$("[data-goto]").forEach((b) =>
  b.addEventListener("click", () => {
    if (state.user) switchTab(b.dataset.goto);
  })
);

/* ---------- room card rendering ---------- */
function progressBar(room) {
  const pct = Math.round((room.paid_count / room.total_people) * 100);
  return `
    <div class="progress-label"><span>${esc(room.progress)}</span><span>${pct}%</span></div>
    <div class="progress"><span style="width:${pct}%"></span></div>`;
}

function memberChips(room) {
  const chips = (room.members || []).map((m) =>
    `<span class="member ${m.paid ? "paid" : ""}">${m.paid ? "✓" : "…"} ${esc(m.username)} · ${money(m.share)}</span>`);
  for (let i = 0; i < room.slots_left; i++) chips.push(`<span class="member slot">open seat</span>`);
  return `<div class="members">${chips.join("")}</div>`;
}

function ownerCard(room) {
  return `
    <article class="card room-card">
      <div class="room-top">
        <div><h3>${esc(room.name)}</h3><div class="room-meta">${esc(room.activity)} · ${prettyDate(room.date)}</div></div>
        <span class="badge owner">Owner</span>
      </div>
      <div>Code <span class="code-pill" data-copy="${esc(room.code)}" title="Click to copy">${esc(room.code)}</span></div>
      ${progressBar(room)}
      <div class="room-meta">Collected ${money(room.collected)} · Pending ${money(room.outstanding)} · Total ${money(room.total_amount)}</div>
      ${memberChips(room)}
    </article>`;
}

function participantCard(room) {
  return `
    <article class="card room-card">
      <div class="room-top">
        <div><h3>${esc(room.name)}</h3><div class="room-meta">${esc(room.activity)} · ${prettyDate(room.date)} · by ${esc(room.owner)}</div></div>
        <span class="badge participant">To pay</span>
      </div>
      <div class="amount">${money(room.my_share)}</div>
      <button class="btn pay" data-pay="${esc(room.code)}" data-amount="${room.my_share}">Paid</button>
    </article>`;
}

function previousCard(room) {
  const isOwner = room.role === "owner";
  return `
    <article class="card room-card">
      <div class="room-top">
        <div><h3>${esc(room.name)}</h3><div class="room-meta">${esc(room.activity)} · ${prettyDate(room.date)}</div></div>
        <span class="badge done">${isOwner ? "Owner · settled" : "Paid"}</span>
      </div>
      <div class="amount">${money(room.my_share)}</div>
      <div class="room-meta">
        ${isOwner ? `You fronted ${money(room.total_amount)} for ${room.total_people} people` : `Paid to ${esc(room.owner)}`}
        · closed ${prettyDate(room.closed_at)}
      </div>
    </article>`;
}

/* ---------- My Rooms ---------- */
async function loadMyRooms() {
  if (!state.user) return;
  try {
    const qs = state.ownerOnly ? "?owner_only=true" : "";
    const { active } = await api(`/api/users/${encodeURIComponent(state.user)}/rooms${qs}`);
    $("#my-rooms").innerHTML = active.length
      ? active.map((r) => (r.role === "owner" ? ownerCard(r) : participantCard(r))).join("")
      : `<div class="empty">${state.ownerOnly ? "You don't own any active rooms." : "No active rooms. Create one or join with a code."}</div>`;
  } catch (err) {
    toast(err.message, "error");
  }
}

$("#owner-only").addEventListener("change", (e) => {
  state.ownerOnly = e.target.checked;
  loadMyRooms();
});

/* ---------- paying (used on Home and Join) ---------- */
async function payRoom(code, amount) {
  if (!confirm(`Confirm you've paid ${money(amount)} to the room owner?`)) return;
  try {
    const data = await api(`/api/rooms/${code}/pay`, { method: "POST", body: { username: state.user } });
    toast(data.message, "success");
    $("#join-result").classList.add("hidden");
    $("#join-code").value = "";
    if (state.activeTab === "home") loadMyRooms();
    else switchTab("home");
  } catch (err) {
    toast(err.message, "error");
  }
}

// One click listener handles every Paid button and copy pill (event delegation)
document.addEventListener("click", (e) => {
  const payBtn = e.target.closest("[data-pay]");
  if (payBtn) payRoom(payBtn.dataset.pay, payBtn.dataset.amount);

  const copy = e.target.closest("[data-copy]");
  if (copy) {
    navigator.clipboard?.writeText(copy.dataset.copy);
    toast(`Copied ${copy.dataset.copy}`);
  }
});

/* ---------- Create Room ---------- */
const createForm = $("#create-form");
createForm.date.value = new Date().toISOString().slice(0, 10);

function updateSplitPreview() {
  const total = parseFloat(createForm.total_amount.value);
  const people = parseInt(createForm.total_people.value, 10);
  const custom = createForm.split_type.value === "custom";
  $("#custom-wrap").classList.toggle("hidden", !custom);

  const out = $("#split-preview");
  if (!(total > 0) || !(people >= 2)) { out.textContent = ""; return; }

  if (!custom) {
    out.textContent = `Each person pays ${money(total / people)}. ${people - 1} people will owe you.`;
    return;
  }
  const shares = createForm.custom_shares.value.split(",").map((s) => parseFloat(s)).filter((n) => !isNaN(n));
  const sum = shares.reduce((a, b) => a + b, 0);
  out.textContent = `${shares.length}/${people - 1} shares entered · others owe ${money(sum)} · your share ${money(total - sum)}`;
}
["input", "change"].forEach((evt) => createForm.addEventListener(evt, updateSplitPreview));
updateSplitPreview();

createForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(createForm);
  const body = Object.fromEntries(f.entries());
  body.username = state.user;
  try {
    const room = await api("/api/rooms", { method: "POST", body });
    $("#create-result").classList.remove("hidden");
    $("#create-result").innerHTML = `
      <h2>${esc(room.name)} is live</h2>
      <p class="muted">Share this code with your friends.</p>
      <div class="big-code" data-copy="${esc(room.code)}" title="Click to copy">${esc(room.code)}</div>
      <dl class="detail-list">
        <dt>Activity</dt><dd>${esc(room.activity)}</dd>
        <dt>Date</dt><dd>${prettyDate(room.date)}</dd>
        <dt>Total</dt><dd>${money(room.total_amount)}</dd>
        <dt>Split</dt><dd>${room.split_type === "equal" ? `${money(room.total_amount / room.total_people)} each` : "Custom"}</dd>
        <dt>Your share</dt><dd>${money(room.my_share)}</dd>
        <dt>Status</dt><dd>${esc(room.progress)}</dd>
      </dl>
      <button class="btn" type="button" data-goto-home>Go to My Rooms</button>`;
    $("#create-result [data-goto-home]").addEventListener("click", () => switchTab("home"));
    createForm.reset();
    createForm.date.value = new Date().toISOString().slice(0, 10);
    updateSplitPreview();
    toast(`Room ${room.code} created`, "success");
  } catch (err) {
    toast(err.message, "error");
  }
});

/* ---------- Join Room ---------- */
$("#join-code").addEventListener("input", (e) => {
  e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
});

$("#join-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const code = $("#join-code").value.trim();
  const box = $("#join-result");
  try {
    const room = await api(`/api/rooms/${code}/join`, { method: "POST", body: { username: state.user } });
    box.classList.remove("hidden");
    box.innerHTML = `
      <h2>${esc(room.name)}</h2>
      <dl class="detail-list">
        <dt>Room name</dt><dd>${esc(room.name)}</dd>
        <dt>Activity</dt><dd>${esc(room.activity)}</dd>
        <dt>Date</dt><dd>${prettyDate(room.date)}</dd>
        <dt>Paid by</dt><dd>${esc(room.owner)}</dd>
      </dl>
      <div class="due-box">
        <div class="muted">Amount to be paid</div>
        <div class="amount">${money(room.my_share)}</div>
      </div>
      <button class="btn pay" data-pay="${esc(room.code)}" data-amount="${room.my_share}">Paid</button>
      <p class="muted">Not paid yet? This room stays in My Rooms until you tap Paid.</p>`;
  } catch (err) {
    box.classList.add("hidden");
    toast(err.message, "error");
  }
});

/* ---------- Previous Rooms + analytics ---------- */
function statTile(label, value) {
  return `<div class="stat"><div class="label">${label}</div><div class="value">${value}</div></div>`;
}

async function loadPrevious() {
  const user = encodeURIComponent(state.user);
  try {
    const [{ previous }, s] = await Promise.all([
      api(`/api/users/${user}/rooms`),
      api(`/api/users/${user}/summary`),
    ]);

    $("#stats").innerHTML = [
      statTile("Total spent", money(s.total_spent)),
      statTile("Settled rooms", s.rooms_count),
      statTile("Average share", money(s.average_share)),
      statTile("Biggest share", money(s.max_share)),
      statTile("Fronted as owner", money(s.fronted_as_owner)),
      statTile("Still to collect", money(s.pending_to_collect)),
      statTile("Still to pay", money(s.pending_to_pay)),
      statTile("Top activity", esc(s.top_activity || "—")),
    ].join("");

    $("#activity-table").innerHTML = s.by_activity.length ? `
      <table>
        <thead><tr><th>Activity</th><th class="num">Rooms</th><th class="num">Average</th><th class="num">Total</th></tr></thead>
        <tbody>${s.by_activity.map((a) => `
          <tr><td>${esc(a.activity)}</td><td class="num">${a.rooms}</td>
              <td class="num">${money(a.average)}</td><td class="num">${money(a.total)}</td></tr>`).join("")}
        </tbody>
      </table>` : "";

    $("#chart-img").src = `/api/users/${user}/chart.png?t=${Date.now()}`;   // cache-buster
    $("#csv-link").href = `/api/users/${user}/export.csv`;

    $("#previous-rooms").innerHTML = previous.length
      ? previous.map(previousCard).join("")
      : `<div class="empty">No previous rooms yet. Rooms move here once they're settled.</div>`;
  } catch (err) {
    toast(err.message, "error");
  }
}

/* ---------- boot ---------- */
if (state.user) showApp();
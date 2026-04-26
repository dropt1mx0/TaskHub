/* ═══════════════════════════════════════════════════════════════════
   TaskHub Mini App — Frontend logic
   Modern UI + Fixed Wheel + Admin Panel
   ═══════════════════════════════════════════════════════════════════ */

// ─── Telegram WebApp ─────────────────────────────────────────────
const tg = window.Telegram?.WebApp;
let initData = "";
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor("#0a0a0a");
  tg.setBackgroundColor("#0a0a0a");
  initData = tg.initData || "";
}

// ─── Helpers ─────────────────────────────────────────────────────
const API = "/api";

async function api(path, options = {}) {
  try {
    const res = await fetch(API + path, {
      headers: {
        "Authorization": "tma " + initData,
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });
    return res.json();
  } catch (e) {
    console.error("API error:", e);
    return { error: e.message };
  }
}

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function fmt(n) {
  if (n == null) return "0";
  const r = Math.round(n * 1000) / 1000;
  return r === Math.floor(r) ? String(Math.floor(r)) : r.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
}

function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function haptic(type = "impact") {
  if (tg?.HapticFeedback) {
    if (type === "impact") tg.HapticFeedback.impactOccurred("medium");
    else if (type === "success") tg.HapticFeedback.notificationOccurred("success");
    else if (type === "error") tg.HapticFeedback.notificationOccurred("error");
  }
}

function esc(s) { const d = document.createElement("div"); d.textContent = s || ""; return d.innerHTML; }

// ─── Confetti ────────────────────────────────────────────────────
function showConfetti() {
  const colors = ["#2196F3", "#4FC3F7", "#66BB6A", "#FFD740", "#EF5350", "#7C4DFF", "#EC407A", "#26C6DA"];
  for (let i = 0; i < 40; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "vw";
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.animationDuration = (1.5 + Math.random() * 2) + "s";
    piece.style.animationDelay = Math.random() * 0.5 + "s";
    piece.style.width = (4 + Math.random() * 6) + "px";
    piece.style.height = (4 + Math.random() * 6) + "px";
    piece.style.borderRadius = Math.random() > 0.5 ? "50%" : "2px";
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), 4000);
  }
}

// ─── State ───────────────────────────────────────────────────────
let currentPage = "pageTasks";
let userData = null;
let isAdmin = false;
let wheelPrizes = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1];
let wheelSpinning = false;
let wheelAngle = 0;

// ─── Navigation ──────────────────────────────────────────────────
function showPage(pageId) {
  $$(".page").forEach((p) => p.classList.add("hidden"));
  const page = $("#" + pageId);
  if (page) {
    page.classList.remove("hidden");
    currentPage = pageId;
  }

  $$(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === pageId);
  });

  haptic();

  switch (pageId) {
    case "pageTasks":    loadTasks(); break;
    case "pageWheel":    loadWheel(); break;
    case "pageReferrals":loadReferrals(); break;
    case "pageLeaders":  loadLeaders(); break;
    case "pageWallet":   loadWallet(); break;
    case "pageProfile":  loadProfile(); break;
    case "pageAdmin":    loadAdmin(); break;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $$(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => showPage(btn.dataset.page));
  });
});

// ─── Init ────────────────────────────────────────────────────────
async function init() {
  try {
    const data = await api("/me");
    if (data.error) {
      console.error("Auth error:", data.error);
      hideSplash();
      return;
    }
    userData = data;
    isAdmin = data.is_admin || false;
    updateHeader(data);
    updateBalance(data);
    updateStats(data);

    // Show admin tab if user is admin
    if (isAdmin) {
      const navAdmin = $("#navAdmin");
      if (navAdmin) navAdmin.classList.remove("hidden");
    }

    hideSplash();
    showPage("pageTasks");
  } catch (e) {
    console.error("Init error:", e);
    hideSplash();
  }
}

function hideSplash() {
  const splash = $("#splash");
  const app = $("#app");
  splash.classList.add("fade-out");
  app.classList.remove("hidden");
  setTimeout(() => splash.remove(), 600);
}

function updateHeader(data) {
  const initial = (data.first_name || data.username || "T")[0].toUpperCase();
  $("#headerAvatar").textContent = initial;
  $("#headerName").textContent = data.first_name || data.username || "TaskHub";
  $("#headerBalance").textContent = fmt(data.balance) + " USDT";
  const streak = data.login_streak || 0;
  $("#headerStreak").innerHTML = "\uD83D\uDD25 " + streak + "d";
}

function updateStats(data) {
  const streak = data.login_streak || 0;
  const el = $("#streakVal");
  if (el) el.textContent = streak;
  const st = $("#statTasks");
  if (st) st.textContent = data.tasks_completed || 0;
  const se = $("#statEarned");
  if (se) se.textContent = fmt(data.total_earned);
  const sf = $("#statFriends");
  if (sf) sf.textContent = data.referral_count || 0;
}

function updateBalance(data) {
  $("#balanceAmount").textContent = fmt(data.balance);
  $("#balanceHold").textContent = fmt(data.on_hold);
  $("#balanceTotal").textContent = fmt(data.total_earned);
  $("#balanceTasks").textContent = data.tasks_completed || 0;
}

// ─── Tasks ───────────────────────────────────────────────────────
async function loadTasks() {
  const data = await api("/tasks");
  const list = $("#tasksList");

  if (!data.tasks || data.tasks.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <lottie-player src="https://assets2.lottiefiles.com/packages/lf20_kkflmtur.json" background="transparent" speed="1" style="width:120px;height:120px" autoplay loop></lottie-player>
        <p>No tasks available right now</p>
      </div>`;
    return;
  }

  list.innerHTML = data.tasks.map((t) => `
    <div class="task-card" onclick="openTask(${t.id})" data-task='${JSON.stringify(t).replace(/'/g, "&#39;")}'>
      <div class="task-icon">${t.type === "channel_subscription" ? "&#128226;" : "&#128279;"}</div>
      <div class="task-body">
        <div class="task-title">${esc(t.title)}</div>
        <div class="task-desc">${t.channel_username ? "@" + esc(t.channel_username) : (esc(t.description || ""))}</div>
      </div>
      <div class="task-reward">+${fmt(t.reward)}</div>
    </div>
  `).join("");
}

function openTask(taskId) {
  const card = document.querySelector(`.task-card[onclick="openTask(${taskId})"]`);
  if (!card) return;
  const task = JSON.parse(card.dataset.task);
  haptic();

  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal-sheet">
      <div class="modal-handle"></div>
      <div class="modal-title">${esc(task.title)}</div>
      <div class="modal-desc">${esc(task.description || "Subscribe to the channel to earn reward.")}</div>
      ${task.channel_username ? `<p style="font-size:14px;margin-bottom:12px">Channel: <a href="https://t.me/${esc(task.channel_username)}" target="_blank">@${esc(task.channel_username)}</a></p>` : ""}
      <div class="modal-reward">+${fmt(task.reward)} USDT</div>
      <div class="modal-actions">
        ${task.channel_url ? `<a href="${esc(task.channel_url)}" target="_blank" class="btn btn-secondary" style="text-decoration:none">Open Channel</a>` : ""}
        <button class="btn btn-primary" id="btnCompleteTask">Complete Task</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.remove();
  });

  overlay.querySelector("#btnCompleteTask").addEventListener("click", async () => {
    const btn = overlay.querySelector("#btnCompleteTask");
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span>';

    const res = await api(`/tasks/${taskId}/complete`, { method: "POST" });
    if (res.success) {
      haptic("success");
      toast(`+${fmt(res.reward)} USDT earned!`);
      if (userData) {
        userData.balance = res.balance;
        userData.on_hold = res.on_hold;
        userData.tasks_completed = (userData.tasks_completed || 0) + 1;
        updateHeader(userData);
        updateBalance(userData);
        updateStats(userData);
      }
      overlay.remove();
      loadTasks();
    } else {
      haptic("error");
      btn.textContent = res.error || "Error";
      btn.disabled = false;
      setTimeout(() => { btn.textContent = "Complete Task"; }, 2000);
    }
  });
}

// ─── Fortune Wheel (Canvas) ──────────────────────────────────────
const WHEEL_COLORS = [
  "#2196F3", "#66BB6A", "#7C4DFF", "#FFD740",
  "#EC407A", "#26C6DA", "#EF5350", "#4FC3F7"
];

function drawWheel(angle = 0) {
  const canvas = $("#wheelCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const size = canvas.width;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = cx - 4;
  const innerR = outerR - 8;
  const n = wheelPrizes.length;
  const arc = (2 * Math.PI) / n;

  ctx.clearRect(0, 0, size, size);

  // Outer ring
  ctx.beginPath();
  ctx.arc(cx, cy, outerR, 0, 2 * Math.PI);
  const ringGrad = ctx.createLinearGradient(0, 0, size, size);
  ringGrad.addColorStop(0, "#2d2d30");
  ringGrad.addColorStop(1, "#1a1a1c");
  ctx.fillStyle = ringGrad;
  ctx.fill();

  // Dot markers on ring
  for (let i = 0; i < n * 2; i++) {
    const dotAngle = (i / (n * 2)) * 2 * Math.PI - Math.PI / 2;
    const dotX = cx + (outerR - 4) * Math.cos(dotAngle);
    const dotY = cy + (outerR - 4) * Math.sin(dotAngle);
    ctx.beginPath();
    ctx.arc(dotX, dotY, 2, 0, 2 * Math.PI);
    ctx.fillStyle = i % 2 === 0 ? "rgba(255,255,255,.3)" : "rgba(33,150,243,.4)";
    ctx.fill();
  }

  // Wheel slices
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(angle);

  for (let i = 0; i < n; i++) {
    const startAngle = i * arc - Math.PI / 2;

    // Slice
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, innerR, startAngle, startAngle + arc);
    ctx.closePath();

    const sliceGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, innerR);
    const baseColor = WHEEL_COLORS[i % WHEEL_COLORS.length];
    sliceGrad.addColorStop(0, adjustBrightness(baseColor, 30));
    sliceGrad.addColorStop(1, baseColor);
    ctx.fillStyle = sliceGrad;
    ctx.fill();

    // Slice border
    ctx.strokeStyle = "rgba(0,0,0,.2)";
    ctx.lineWidth = 1;
    ctx.stroke();

    // Prize text
    ctx.save();
    ctx.rotate(startAngle + arc / 2);
    ctx.fillStyle = "#fff";
    ctx.font = "bold 14px -apple-system, SF Pro Display, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.shadowColor = "rgba(0,0,0,.5)";
    ctx.shadowBlur = 4;
    ctx.fillText(String(wheelPrizes[i]), innerR * 0.62, 0);
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  ctx.restore();

  // Center circle with gradient
  ctx.beginPath();
  ctx.arc(cx, cy, 26, 0, 2 * Math.PI);
  ctx.fillStyle = "#1a1a1c";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, 23, 0, 2 * Math.PI);
  const centerGrad = ctx.createLinearGradient(cx - 23, cy - 23, cx + 23, cy + 23);
  centerGrad.addColorStop(0, "#2196F3");
  centerGrad.addColorStop(1, "#64B5F6");
  ctx.fillStyle = centerGrad;
  ctx.fill();

  // Center text
  ctx.fillStyle = "#fff";
  ctx.font = "bold 10px -apple-system, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("SPIN", cx, cy);
}

function adjustBrightness(hex, percent) {
  const num = parseInt(hex.replace("#", ""), 16);
  const r = Math.min(255, ((num >> 16) & 0xff) + percent);
  const g = Math.min(255, ((num >> 8) & 0xff) + percent);
  const b = Math.min(255, (num & 0xff) + percent);
  return `rgb(${r},${g},${b})`;
}

async function loadWheel() {
  drawWheel(wheelAngle);

  const data = await api("/wheel");
  if (data.error) return;

  if (data.prizes) wheelPrizes = data.prizes;
  drawWheel(wheelAngle);

  const btnFree = $("#btnSpinFree");
  const btnPaid = $("#btnSpinPaid");
  const cooldown = $("#wheelCooldown");
  const cooldownTime = $("#cooldownTime");

  if (data.can_spin_free) {
    btnFree.classList.remove("hidden");
    btnFree.disabled = false;
    cooldown.classList.add("hidden");
  } else {
    btnFree.classList.add("hidden");
    cooldown.classList.remove("hidden");
    cooldownTime.textContent = `${data.cooldown_hours}h ${data.cooldown_minutes}m`;
  }

  $("#spinCost").textContent = data.paid_cost || 0.25;

  // History
  const histEl = $("#wheelHistory");
  if (data.history && data.history.length) {
    histEl.innerHTML = data.history.map((h) => `
      <div class="history-item">
        <div class="history-item-left">
          <span class="history-item-type">${h.is_free ? "Free" : "Paid"} Spin</span>
          <span class="history-item-date">${h.time ? new Date(h.time).toLocaleString() : ""}</span>
        </div>
        <span class="history-item-amount positive">+${fmt(h.reward)}</span>
      </div>
    `).join("");
  } else {
    histEl.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;text-align:center;padding:16px">No spins yet</p>`;
  }
}

async function spinWheel(isFree) {
  if (wheelSpinning) return;
  wheelSpinning = true;
  haptic();

  const btnFree = $("#btnSpinFree");
  const btnPaid = $("#btnSpinPaid");
  btnFree.disabled = true;
  btnPaid.disabled = true;

  // Hide previous result
  $("#wheelResult").classList.add("hidden");

  const duration = 4000;
  const startAngle = wheelAngle;
  const extraSpins = 6 + Math.random() * 4;
  const targetAngle = startAngle + extraSpins * 2 * Math.PI;
  const startTime = performance.now();

  const resultPromise = api("/wheel/spin", {
    method: "POST",
    body: JSON.stringify({ is_free: isFree }),
  });

  function animate(now) {
    const elapsed = now - startTime;
    const t = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - t, 4); // quartic ease-out
    wheelAngle = startAngle + (targetAngle - startAngle) * ease;
    drawWheel(wheelAngle);

    if (t < 1) {
      requestAnimationFrame(animate);
    } else {
      finishSpin(resultPromise);
    }
  }

  requestAnimationFrame(animate);
}

async function finishSpin(resultPromise) {
  const res = await resultPromise;
  wheelSpinning = false;

  const resultEl = $("#wheelResult");
  const rewardText = $("#wheelRewardText");

  if (res.success) {
    haptic("success");
    rewardText.textContent = fmt(res.reward);
    resultEl.classList.remove("hidden");
    showConfetti();

    if (userData) {
      userData.balance = res.balance;
      userData.on_hold = res.on_hold;
      updateHeader(userData);
      updateBalance(userData);
      updateStats(userData);
    }

    setTimeout(() => resultEl.classList.add("hidden"), 5000);
  } else {
    haptic("error");
    toast(res.error || "Spin failed");
  }

  setTimeout(loadWheel, 600);
}

document.addEventListener("DOMContentLoaded", () => {
  $("#btnSpinFree")?.addEventListener("click", () => spinWheel(true));
  $("#btnSpinPaid")?.addEventListener("click", () => spinWheel(false));
});

// ─── Referrals ───────────────────────────────────────────────────
async function loadReferrals() {
  if (userData) {
    $("#refLinkInput").value = userData.referral_link || "";
  }

  const data = await api("/referrals");
  if (data.error) return;

  $("#refCount").textContent = data.count || 0;
  $("#refDirect").textContent = fmt(data.direct);
  $("#refPassive").textContent = fmt(data.passive);

  const list = $("#refList");
  if (data.referrals && data.referrals.length) {
    list.innerHTML = data.referrals.map((r) => `
      <div class="ref-item">
        <div>
          <span class="ref-item-name">${esc(r.username)} ${r.is_premium ? "&#11088;" : ""}</span>
          <span class="ref-item-tasks">${r.tasks_completed} tasks</span>
        </div>
        <span class="ref-item-earnings">+${fmt(r.passive_earnings)}</span>
      </div>
    `).join("");
  } else {
    list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;text-align:center;padding:16px">No referrals yet. Share your link!</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#btnCopyRef")?.addEventListener("click", () => {
    const input = $("#refLinkInput");
    if (!input.value) return;
    navigator.clipboard.writeText(input.value).then(() => {
      haptic("success");
      toast("Link copied!");
    }).catch(() => {
      input.select();
      document.execCommand("copy");
      toast("Link copied!");
    });
  });
});

// ─── Leaderboard ─────────────────────────────────────────────────
async function loadLeaders() {
  const data = await api("/leaderboard");
  if (data.error) return;

  const list = $("#leadersList");
  if (!data.leaders || data.leaders.length === 0) {
    list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;text-align:center;padding:24px">No leaders yet</p>`;
    return;
  }

  list.innerHTML = data.leaders.map((l, i) => {
    const rank = i + 1;
    const rankClass = rank === 1 ? "gold" : rank === 2 ? "silver" : rank === 3 ? "bronze" : "";
    const medal = rank === 1 ? "&#129351;" : rank === 2 ? "&#129352;" : rank === 3 ? "&#129353;" : rank;
    const isMe = data.my_id === l.user_id;
    return `
      <div class="leader-item ${isMe ? "is-me" : ""}">
        <div class="leader-rank ${rankClass}">${medal}</div>
        <span class="leader-name">${esc(l.name)} ${isMe ? "(you)" : ""}</span>
        <span class="leader-earned">${fmt(l.total_earned)} USDT</span>
      </div>
    `;
  }).join("");
}

// ─── Wallet ──────────────────────────────────────────────────────
let withdrawType = "usdt";

async function loadWallet() {
  if (userData) {
    $("#walletBalance").textContent = fmt(userData.balance) + " USDT";
  }
  $("#minWithdraw").textContent = "1.0";

  const data = await api("/history");
  if (data.error) return;

  const list = $("#historyList");
  if (!data.withdrawals || data.withdrawals.length === 0) {
    list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;text-align:center;padding:16px">No withdrawals yet</p>`;
    return;
  }

  list.innerHTML = data.withdrawals.map((w) => `
    <div class="history-item">
      <div class="history-item-left">
        <span class="history-item-type">${w.type.toUpperCase()} Withdrawal</span>
        <span class="history-item-date">${w.requested_at ? new Date(w.requested_at).toLocaleDateString() : ""}</span>
      </div>
      <div style="text-align:right">
        <span class="history-item-amount negative">-${fmt(w.amount)}</span>
        <span class="status-badge ${w.status}">${w.status}</span>
      </div>
    </div>
  `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  $("#togUsdt")?.addEventListener("click", () => {
    withdrawType = "usdt";
    $("#togUsdt").classList.add("active");
    $("#togTon").classList.remove("active");
    haptic();
  });
  $("#togTon")?.addEventListener("click", () => {
    withdrawType = "ton";
    $("#togTon").classList.add("active");
    $("#togUsdt").classList.remove("active");
    haptic();
  });

  $("#btnWithdraw")?.addEventListener("click", async () => {
    const amount = parseFloat($("#withdrawAmount").value);
    const wallet = $("#withdrawWallet").value.trim();
    const btn = $("#btnWithdraw");
    const resultEl = $("#withdrawResult");

    if (!amount || amount < 1) {
      haptic("error");
      resultEl.className = "withdraw-result error";
      resultEl.textContent = "Minimum withdrawal is 1.0 USDT";
      resultEl.classList.remove("hidden");
      return;
    }
    if (!wallet) {
      haptic("error");
      resultEl.className = "withdraw-result error";
      resultEl.textContent = "Enter wallet address";
      resultEl.classList.remove("hidden");
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span>';

    const res = await api("/withdraw", {
      method: "POST",
      body: JSON.stringify({ amount, type: withdrawType, wallet }),
    });

    if (res.success) {
      haptic("success");
      resultEl.className = "withdraw-result success";
      resultEl.textContent = `Withdrawal #${res.withdrawal_id} submitted! New balance: ${fmt(res.balance)} USDT`;
      resultEl.classList.remove("hidden");
      if (userData) {
        userData.balance = res.balance;
        updateHeader(userData);
        updateBalance(userData);
      }
      $("#withdrawAmount").value = "";
      $("#withdrawWallet").value = "";
      loadWallet();
    } else {
      haptic("error");
      resultEl.className = "withdraw-result error";
      resultEl.textContent = res.error || "Withdrawal failed";
      resultEl.classList.remove("hidden");
    }

    btn.disabled = false;
    btn.textContent = "Request Withdrawal";
  });
});

// ─── Profile ─────────────────────────────────────────────────────
function loadProfile() {
  if (!userData) return;
  const initial = (userData.first_name || userData.username || "T")[0].toUpperCase();
  $("#profileAvatar").textContent = initial;
  $("#profileName").textContent = userData.first_name || userData.username || "User";
  $("#profileId").textContent = `ID: ${userData.user_id}`;
  $("#pBalance").textContent = fmt(userData.balance);
  $("#pOnHold").textContent = fmt(userData.on_hold);
  $("#pEarned").textContent = fmt(userData.total_earned);
  $("#pTasks").textContent = userData.tasks_completed || 0;
  $("#pStreak").textContent = userData.login_streak || 0;
  $("#pRefs").textContent = userData.referral_count || 0;
}

// ═════════════════════════════════════════════════════════════════
// ─── ADMIN PANEL ─────────────────────────────────────────────────
// ═════════════════════════════════════════════════════════════════

async function loadAdmin() {
  if (!isAdmin) return;

  // Load stats
  const stats = await api("/admin/stats");
  if (!stats.error) {
    $("#adminTotalUsers").textContent = stats.total_users || 0;
    $("#adminNewUsers").textContent = stats.new_users_24h || 0;
    $("#adminBankBalance").textContent = fmt(stats.bank_balance);
    $("#adminPendingW").textContent = stats.pending_withdrawals || 0;
  }

  // Show main menu, hide sub-pages
  $("#adminMainMenu").classList.remove("hidden");
  $("#adminSubPage").classList.add("hidden");
}

function adminShowSubPage(html) {
  $("#adminMainMenu").classList.add("hidden");
  const sub = $("#adminSubPage");
  sub.innerHTML = html;
  sub.classList.remove("hidden");
}

function adminBack() {
  $("#adminMainMenu").classList.remove("hidden");
  $("#adminSubPage").classList.add("hidden");
  loadAdmin();
}

// ─── Admin: Tasks ────────────────────────────────────────────────
async function adminShowTasks() {
  haptic();
  adminShowSubPage('<div style="text-align:center;padding:20px"><span class="loading-spinner"></span></div>');

  const data = await api("/admin/tasks");
  if (data.error) {
    adminShowSubPage(`<p style="color:var(--red);padding:16px">${data.error}</p>`);
    return;
  }

  let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <h3 style="font-size:16px;font-weight:700">All Tasks</h3>
    <button class="btn btn-sm btn-secondary" onclick="adminBack()">Back</button>
  </div>`;

  if (!data.tasks || data.tasks.length === 0) {
    html += `<p style="color:var(--text-secondary);text-align:center;padding:20px">No tasks</p>`;
  } else {
    data.tasks.forEach((t) => {
      html += `
        <div class="admin-task-item">
          <div class="admin-task-status">${t.is_active ? "&#9989;" : "&#10060;"}</div>
          <div class="admin-task-body">
            <div class="admin-task-title">#${t.id} ${esc(t.title)}</div>
            <div class="admin-task-meta">${fmt(t.reward)} USDT | ${t.total_completions} done</div>
          </div>
          <div class="admin-task-actions">
            <button class="btn btn-sm ${t.is_active ? "btn-secondary" : "btn-success"}" onclick="adminToggleTask(${t.id})">${t.is_active ? "Off" : "On"}</button>
            <button class="btn btn-sm btn-danger" onclick="adminDeleteTask(${t.id})">Del</button>
          </div>
        </div>`;
    });
  }

  adminShowSubPage(html);
}

async function adminToggleTask(taskId) {
  haptic();
  const res = await api(`/admin/tasks/${taskId}/toggle`, { method: "POST" });
  if (res.success) {
    toast("Task updated");
    adminShowTasks();
  } else {
    toast(res.error || "Error");
  }
}

async function adminDeleteTask(taskId) {
  if (!confirm("Delete this task?")) return;
  haptic();
  const res = await api(`/admin/tasks/${taskId}`, { method: "DELETE" });
  if (res.success) {
    toast("Task deleted");
    adminShowTasks();
  } else {
    toast(res.error || "Error");
  }
}

// ─── Admin: Withdrawals ──────────────────────────────────────────
async function adminShowWithdrawals() {
  haptic();
  adminShowSubPage('<div style="text-align:center;padding:20px"><span class="loading-spinner"></span></div>');

  const data = await api("/admin/withdrawals");
  if (data.error) {
    adminShowSubPage(`<p style="color:var(--red);padding:16px">${data.error}</p>`);
    return;
  }

  let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <h3 style="font-size:16px;font-weight:700">Pending Withdrawals</h3>
    <button class="btn btn-sm btn-secondary" onclick="adminBack()">Back</button>
  </div>`;

  if (!data.withdrawals || data.withdrawals.length === 0) {
    html += `<p style="color:var(--text-secondary);text-align:center;padding:20px">No pending withdrawals</p>`;
  } else {
    data.withdrawals.forEach((w) => {
      html += `
        <div class="admin-withdrawal-item">
          <div class="admin-withdrawal-header">
            <span class="admin-withdrawal-user">@${esc(w.username || "user_" + w.user_id)}</span>
            <span class="admin-withdrawal-amount">${fmt(w.amount)} ${(w.type || "usdt").toUpperCase()}</span>
          </div>
          <div class="admin-withdrawal-wallet">${esc(w.wallet)}</div>
          <div class="admin-withdrawal-details">${w.requested_at ? new Date(w.requested_at).toLocaleString() : ""}</div>
          <div class="admin-withdrawal-actions">
            <button class="btn btn-sm btn-success" onclick="adminApproveW(${w.id})">Approve</button>
            <button class="btn btn-sm btn-danger" onclick="adminRejectW(${w.id})">Reject</button>
          </div>
        </div>`;
    });
  }

  adminShowSubPage(html);
}

async function adminApproveW(id) {
  haptic();
  const res = await api(`/admin/withdrawals/${id}/approve`, { method: "POST" });
  if (res.success) {
    toast("Approved");
    adminShowWithdrawals();
  } else {
    toast(res.error || "Error");
  }
}

async function adminRejectW(id) {
  haptic();
  const res = await api(`/admin/withdrawals/${id}/reject`, { method: "POST" });
  if (res.success) {
    toast("Rejected");
    adminShowWithdrawals();
  } else {
    toast(res.error || "Error");
  }
}

// ─── Admin: Broadcast ────────────────────────────────────────────
function adminShowBroadcast() {
  haptic();
  const html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="font-size:16px;font-weight:700">Broadcast</h3>
      <button class="btn btn-sm btn-secondary" onclick="adminBack()">Back</button>
    </div>
    <div class="admin-form">
      <div class="form-group">
        <label>Message (HTML supported)</label>
        <textarea class="admin-broadcast-textarea" id="broadcastText" placeholder="Enter message for all users..."></textarea>
      </div>
      <button class="btn btn-primary btn-block" id="btnBroadcast" onclick="adminSendBroadcast()">Send Broadcast</button>
      <div id="broadcastResult" class="hidden" style="margin-top:12px;padding:12px;border-radius:10px;text-align:center;font-size:14px"></div>
    </div>
  `;
  adminShowSubPage(html);
}

async function adminSendBroadcast() {
  const text = $("#broadcastText")?.value?.trim();
  if (!text) { toast("Enter a message"); return; }
  if (!confirm("Send this message to ALL users?")) return;

  haptic();
  const btn = $("#btnBroadcast");
  btn.disabled = true;
  btn.innerHTML = '<span class="loading-spinner"></span> Sending...';

  const res = await api("/admin/broadcast", {
    method: "POST",
    body: JSON.stringify({ text }),
  });

  const resultEl = $("#broadcastResult");
  resultEl.classList.remove("hidden");
  if (res.success) {
    resultEl.style.background = "rgba(76,175,80,.1)";
    resultEl.style.color = "var(--green-light)";
    resultEl.textContent = `Sent: ${res.success_count} | Failed: ${res.failed_count}`;
    haptic("success");
  } else {
    resultEl.style.background = "rgba(255,107,107,.1)";
    resultEl.style.color = "var(--red)";
    resultEl.textContent = res.error || "Broadcast failed";
  }

  btn.disabled = false;
  btn.textContent = "Send Broadcast";
}

// ─── Admin: Create Task ──────────────────────────────────────────
function adminShowCreateTask() {
  haptic();
  const html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="font-size:16px;font-weight:700">Create Task</h3>
      <button class="btn btn-sm btn-secondary" onclick="adminBack()">Back</button>
    </div>
    <div class="admin-form">
      <div class="form-group">
        <label>Title</label>
        <input type="text" class="form-input" id="newTaskTitle" placeholder="Subscribe to channel">
      </div>
      <div class="form-group">
        <label>Description</label>
        <input type="text" class="form-input" id="newTaskDesc" placeholder="Description...">
      </div>
      <div class="form-group">
        <label>Reward (USDT)</label>
        <input type="number" class="form-input" id="newTaskReward" placeholder="0.01" step="0.001" min="0.001">
      </div>
      <div class="form-group">
        <label>Channel Username (without @)</label>
        <input type="text" class="form-input" id="newTaskChannel" placeholder="channel_name">
      </div>
      <button class="btn btn-primary btn-block" onclick="adminCreateTask()">Create Task</button>
    </div>
  `;
  adminShowSubPage(html);
}

async function adminCreateTask() {
  const title = $("#newTaskTitle")?.value?.trim();
  const description = $("#newTaskDesc")?.value?.trim();
  const reward = parseFloat($("#newTaskReward")?.value);
  const channel = $("#newTaskChannel")?.value?.trim();

  if (!title) { toast("Enter title"); return; }
  if (!reward || reward < 0.001) { toast("Enter valid reward"); return; }
  if (!channel) { toast("Enter channel username"); return; }

  haptic();
  const res = await api("/admin/tasks", {
    method: "POST",
    body: JSON.stringify({
      title,
      description: description || title,
      reward,
      channel_username: channel.replace("@", ""),
    }),
  });

  if (res.success) {
    haptic("success");
    toast("Task created!");
    adminShowTasks();
  } else {
    haptic("error");
    toast(res.error || "Error creating task");
  }
}

// ─── Boot ────────────────────────────────────────────────────────
init();

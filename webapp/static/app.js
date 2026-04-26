/* ═══════════════════════════════════════════════════════════════════
   TaskHub Mini App — Frontend logic
   Telegram WebApp SDK + REST API calls + Fortune Wheel canvas
   ═══════════════════════════════════════════════════════════════════ */

// ─── Telegram WebApp ─────────────────────────────────────────────
const tg = window.Telegram?.WebApp;
let initData = "";
if (tg) {
  tg.ready();
  tg.expand();
  initData = tg.initData || "";
  // Apply Telegram theme
  document.documentElement.style.setProperty("--tg-theme-bg-color", tg.themeParams.bg_color || "#1c1c1e");
}

// ─── Helpers ─────────────────────────────────────────────────────
const API = "/api";

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: {
      "Authorization": "tma " + initData,
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });
  return res.json();
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
  setTimeout(() => el.remove(), 3000);
}

function haptic(type = "impact") {
  if (tg?.HapticFeedback) {
    if (type === "impact") tg.HapticFeedback.impactOccurred("medium");
    else if (type === "success") tg.HapticFeedback.notificationOccurred("success");
    else if (type === "error") tg.HapticFeedback.notificationOccurred("error");
  }
}

// ─── State ───────────────────────────────────────────────────────
let currentPage = "pageTasks";
let userData = null;
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

  // Update nav buttons
  $$(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === pageId);
  });

  haptic();

  // Load page data
  switch (pageId) {
    case "pageTasks":    loadTasks(); break;
    case "pageWheel":    loadWheel(); break;
    case "pageReferrals":loadReferrals(); break;
    case "pageLeaders":  loadLeaders(); break;
    case "pageWallet":   loadWallet(); break;
    case "pageProfile":  loadProfile(); break;
  }
}

// Attach nav clicks
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
      // In dev mode, show app anyway
      hideSplash();
      return;
    }
    userData = data;
    updateHeader(data);
    updateBalance(data);
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
  setTimeout(() => splash.remove(), 500);
}

function updateHeader(data) {
  const initial = (data.first_name || data.username || "T")[0].toUpperCase();
  $("#headerAvatar").textContent = initial;
  $("#headerName").textContent = data.first_name || data.username || "TaskHub";
  $("#headerBalance").textContent = fmt(data.balance) + " USDT";
  $("#headerStreak").textContent = (data.login_streak || 0) + "d";
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
        <lottie-player src="https://assets3.lottiefiles.com/packages/lf20_WpDG3calyJ.json"
          background="transparent" speed="1" style="width:100px;height:100px" loop autoplay></lottie-player>
        <p>No tasks available right now</p>
      </div>`;
    return;
  }

  list.innerHTML = data.tasks.map((t) => `
    <div class="task-card" onclick="openTask(${t.id})" data-task='${JSON.stringify(t).replace(/'/g, "&#39;")}'>
      <div class="task-icon">${t.type === "channel_subscription" ? "📢" : "🔗"}</div>
      <div class="task-body">
        <div class="task-title">${esc(t.title)}</div>
        <div class="task-desc">${t.channel_username ? "@" + esc(t.channel_username) : (esc(t.description || ""))}</div>
      </div>
      <div class="task-reward">+${fmt(t.reward)}</div>
    </div>
  `).join("");
}

function esc(s) { const d = document.createElement("div"); d.textContent = s || ""; return d.innerHTML; }

function openTask(taskId) {
  // Find task data from the card
  const card = document.querySelector(`.task-card[onclick="openTask(${taskId})"]`);
  if (!card) return;
  const task = JSON.parse(card.dataset.task);

  haptic();

  // Create modal
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal-sheet">
      <div class="modal-handle"></div>
      <div class="modal-title">${esc(task.title)}</div>
      <div class="modal-desc">${esc(task.description || "Subscribe to the channel to earn reward.")}</div>
      ${task.channel_username ? `<p style="font-size:14px;margin-bottom:12px">Channel: <a href="https://t.me/${esc(task.channel_username)}" target="_blank" style="color:var(--tg-theme-link-color)">@${esc(task.channel_username)}</a></p>` : ""}
      <div class="modal-reward">+${fmt(task.reward)} USDT</div>
      <div class="modal-actions">
        ${task.channel_url ? `<a href="${esc(task.channel_url)}" target="_blank" class="btn btn-secondary" style="text-decoration:none">Open Channel</a>` : ""}
        <button class="btn btn-primary" id="btnCompleteTask">Complete Task</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  // Close on overlay click
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.remove();
  });

  // Complete task button
  overlay.querySelector("#btnCompleteTask").addEventListener("click", async () => {
    const btn = overlay.querySelector("#btnCompleteTask");
    btn.disabled = true;
    btn.textContent = "Checking...";

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
      }
      overlay.remove();
      loadTasks();
    } else {
      haptic("error");
      btn.textContent = res.error || "Error";
      setTimeout(() => { btn.textContent = "Complete Task"; btn.disabled = false; }, 2000);
    }
  });
}

// ─── Fortune Wheel (Canvas) ──────────────────────────────────────
const WHEEL_COLORS = [
  "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
  "#FFEAA7", "#DDA0DD", "#98D8C8"
];

function drawWheel(angle = 0) {
  const canvas = $("#wheelCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const r = cx - 6;
  const n = wheelPrizes.length;
  const arc = (2 * Math.PI) / n;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(angle);

  for (let i = 0; i < n; i++) {
    const startAngle = i * arc - Math.PI / 2;
    // Slice
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, r, startAngle, startAngle + arc);
    ctx.closePath();
    ctx.fillStyle = WHEEL_COLORS[i % WHEEL_COLORS.length];
    ctx.fill();
    ctx.strokeStyle = "rgba(0,0,0,.15)";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Text
    ctx.save();
    ctx.rotate(startAngle + arc / 2);
    ctx.fillStyle = "#fff";
    ctx.font = "bold 13px -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.shadowColor = "rgba(0,0,0,.4)";
    ctx.shadowBlur = 3;
    ctx.fillText(wheelPrizes[i] + "", r * 0.65, 5);
    ctx.restore();
  }

  ctx.restore();

  // Center circle
  ctx.beginPath();
  ctx.arc(cx, cy, 22, 0, 2 * Math.PI);
  ctx.fillStyle = "#fff";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, 20, 0, 2 * Math.PI);
  const grad = ctx.createLinearGradient(cx - 20, cy - 20, cx + 20, cy + 20);
  grad.addColorStop(0, "#007aff");
  grad.addColorStop(1, "#5856d6");
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.font = "bold 10px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("SPIN", cx, cy + 4);
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
    histEl.innerHTML = `<p style="color:var(--tg-theme-hint-color);font-size:13px;text-align:center;padding:12px">No spins yet</p>`;
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

  // Spin animation
  const duration = 3500;
  const startAngle = wheelAngle;
  const extraSpins = 5 + Math.random() * 3;
  const targetAngle = startAngle + extraSpins * 2 * Math.PI;
  const startTime = performance.now();

  // Make API call in parallel
  const resultPromise = api("/wheel/spin", {
    method: "POST",
    body: JSON.stringify({ is_free: isFree }),
  });

  function animate(now) {
    const elapsed = now - startTime;
    const t = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const ease = 1 - Math.pow(1 - t, 3);
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

    // Play win animation
    const lottie = $("#winAnimation");
    if (lottie && lottie.play) lottie.play();

    if (userData) {
      userData.balance = res.balance;
      userData.on_hold = res.on_hold;
      updateHeader(userData);
      updateBalance(userData);
    }

    // Hide result after delay
    setTimeout(() => resultEl.classList.add("hidden"), 4000);
  } else {
    haptic("error");
    toast(res.error || "Spin failed");
  }

  // Reload wheel state
  setTimeout(loadWheel, 500);
}

// Attach spin handlers
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
          <span class="ref-item-name">${esc(r.username)} ${r.is_premium ? "⭐" : ""}</span>
          <span class="ref-item-tasks">${r.tasks_completed} tasks</span>
        </div>
        <span class="ref-item-earnings">+${fmt(r.passive_earnings)}</span>
      </div>
    `).join("");
  } else {
    list.innerHTML = `<p style="color:var(--tg-theme-hint-color);font-size:13px;text-align:center;padding:12px">No referrals yet. Share your link!</p>`;
  }
}

// Copy referral link
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
    list.innerHTML = `<p style="color:var(--tg-theme-hint-color);font-size:13px;text-align:center;padding:20px">No leaders yet</p>`;
    return;
  }

  list.innerHTML = data.leaders.map((l, i) => {
    const rank = i + 1;
    const rankClass = rank === 1 ? "gold" : rank === 2 ? "silver" : rank === 3 ? "bronze" : "";
    const medal = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : rank;
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

  // Load history
  const data = await api("/history");
  if (data.error) return;

  const list = $("#historyList");
  if (!data.withdrawals || data.withdrawals.length === 0) {
    list.innerHTML = `<p style="color:var(--tg-theme-hint-color);font-size:13px;text-align:center;padding:12px">No withdrawals yet</p>`;
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
  // Toggle currency type
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

  // Submit withdrawal
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
    btn.textContent = "Processing...";

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

// ─── Boot ────────────────────────────────────────────────────────
init();

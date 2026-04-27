/* ═══════════════════════════════════════════════════════════════════
   TaskHub Mini App — Frontend (RU, matching reference design)
   ═══════════════════════════════════════════════════════════════════ */

// ─── Telegram WebApp ─────────────────────────────────────────────
const tg = window.Telegram?.WebApp;
let initData = "";
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor("#06060c");
  tg.setBackgroundColor("#06060c");
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

// ─── Sticker System (Lottie JSON) ────────────────────────────────
async function initStickers(root = document) {
  const slots = root.querySelectorAll(".sticker-slot:not([data-loaded])");
  for (const slot of slots) {
    const name = slot.dataset.sticker;
    const w = slot.dataset.w || "80";
    const h = slot.dataset.h || "80";
    const fallback = slot.dataset.fallback || "";
    const localUrl = `/static/stickers/${name}.json`;

    slot.setAttribute("data-loaded", "1");
    slot.style.width = w + "px";
    slot.style.height = h + "px";

    let src = fallback;
    try {
      const check = await fetch(localUrl, { method: "HEAD" });
      if (check.ok) src = localUrl;
    } catch (_) {}

    if (src) {
      const player = document.createElement("lottie-player");
      player.setAttribute("src", src);
      player.setAttribute("background", "transparent");
      player.setAttribute("speed", "1");
      player.setAttribute("autoplay", "");
      player.setAttribute("loop", "");
      player.style.width = w + "px";
      player.style.height = h + "px";
      slot.appendChild(player);
    }
  }
}

// ─── Confetti ────────────────────────────────────────────────────
function showConfetti() {
  const colors = ["#4FC3F7", "#66BB6A", "#FFAB91", "#FFD740", "#B388FF", "#F06292", "#26C6DA", "#A8E6CF", "#FF6B35", "#81D4FA"];
  for (let i = 0; i < 55; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "vw";
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.animationDuration = (2 + Math.random() * 2.5) + "s";
    piece.style.animationDelay = Math.random() * 0.8 + "s";
    piece.style.width = (4 + Math.random() * 8) + "px";
    piece.style.height = (4 + Math.random() * 8) + "px";
    piece.style.borderRadius = Math.random() > 0.5 ? "50%" : Math.random() > 0.5 ? "2px" : "0";
    piece.style.opacity = (0.7 + Math.random() * 0.3).toString();
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), 5000);
  }
}

// ─── State ───────────────────────────────────────────────────────
let currentPage = "pageTasks";
let userData = null;
let isAdmin = false;
let wheelPrizes = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1];
let wheelSpinning = false;
let wheelAngle = 0;

// ─── Ripple effect ───────────────────────────────────────────────
function addRipple(e, el) {
  const rect = el.getBoundingClientRect();
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  const size = Math.max(rect.width, rect.height);
  ripple.style.width = ripple.style.height = size + "px";
  ripple.style.left = (e.clientX - rect.left - size / 2) + "px";
  ripple.style.top = (e.clientY - rect.top - size / 2) + "px";
  el.style.position = el.style.position || "relative";
  el.style.overflow = "hidden";
  el.appendChild(ripple);
  setTimeout(() => ripple.remove(), 600);
}

// ─── Navigation with page transitions ────────────────────────────
function showPage(pageId) {
  const prevPage = $(".page:not(.hidden)");

  $$(".page").forEach((p) => p.classList.add("hidden"));
  const page = $("#" + pageId);
  if (page) {
    page.classList.remove("hidden");
    /* Re-trigger entrance animation */
    page.style.animation = "none";
    page.offsetHeight; /* force reflow */
    page.style.animation = "";
    currentPage = pageId;
  }

  $$(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === pageId);
  });

  haptic();

  switch (pageId) {
    case "pageTasks":     loadDaily(); loadTasks(); break;
    case "pageWheel":     loadWheel(); break;
    case "pageReferrals": loadReferrals(); break;
    case "pageWallet":    loadWallet(); break;
    case "pageProfile":   loadProfile(); break;
    case "pageAdmin":     loadAdmin(); break;
  }

  /* Scroll to top on page switch */
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.addEventListener("DOMContentLoaded", () => {
  $$(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      addRipple(e, btn);
      showPage(btn.dataset.page);
    });
  });

  /* Add ripple to all primary buttons */
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-primary, .daily-claim-btn, .task-btn");
    if (btn) addRipple(e, btn);
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

// ─── Tasks ───────────────────────────────────────────────────────
async function loadTasks() {
  const data = await api("/tasks");
  const list = $("#tasksList");

  if (!data.tasks || data.tasks.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="sticker-slot" data-sticker="tasks-empty" data-w="120" data-h="120" data-fallback="https://assets2.lottiefiles.com/packages/lf20_kkflmtur.json"></div>
        <p>Нет доступных заданий</p>
      </div>`;
    initStickers(list);
    return;
  }

  list.innerHTML = data.tasks.map((t) => `
    <div class="task-card" onclick="openTask(${t.id})" data-task='${JSON.stringify(t).replace(/'/g, "&#39;")}'>
      <div class="task-thumb">${t.type === "channel_subscription" ? "&#128226;" : "&#128279;"}</div>
      <div class="task-body">
        <div class="task-title">${esc(t.title)}</div>
        <div class="task-desc">${t.channel_username ? "Подписаться на канал @" + esc(t.channel_username) : (esc(t.description || ""))}</div>
      </div>
      <div class="task-right">
        <div class="task-reward">+${fmt(t.reward)} &#11088;</div>
        <button class="task-btn">${t.type === "channel_subscription" ? "Subscribe" : "Start"}</button>
      </div>
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
      <div class="modal-desc">${esc(task.description || "Подпишитесь на канал, чтобы получить награду.")}</div>
      ${task.channel_username ? `<p style="font-size:14px;margin-bottom:12px">Канал: <a href="https://t.me/${esc(task.channel_username)}" target="_blank">@${esc(task.channel_username)}</a></p>` : ""}
      <div class="modal-reward">+${fmt(task.reward)} USDT</div>
      <div class="modal-actions">
        ${task.channel_url ? `<a href="${esc(task.channel_url)}" target="_blank" class="btn btn-secondary" style="text-decoration:none">Открыть канал</a>` : ""}
        <button class="btn btn-primary" id="btnCompleteTask">Выполнить</button>
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
      toast(`+${fmt(res.reward)} USDT получено!`);
      if (userData) {
        userData.balance = res.balance;
        userData.on_hold = res.on_hold;
        userData.tasks_completed = (userData.tasks_completed || 0) + 1;
      }
      overlay.remove();
      loadTasks();
    } else {
      haptic("error");
      btn.textContent = res.error || "Ошибка";
      btn.disabled = false;
      setTimeout(() => { btn.textContent = "Выполнить"; }, 2000);
    }
  });
}

// ─── Daily Check-in ──────────────────────────────────────────
let dailyData = null;

async function loadDaily() {
  const data = await api("/daily");
  if (data.error) return;
  dailyData = data;
  renderDaily(data);
}

function renderDaily(data) {
  const container = $("#dailyDays");
  const btn = $("#btnDailyClaim");
  const streakNum = $("#dailyStreakNum");
  if (!container || !btn) return;

  const rewards = data.rewards || [];
  const dayIndex = data.day_index || 0;
  const streak = data.streak || 0;
  const claimed = data.already_claimed;

  streakNum.textContent = streak;

  container.innerHTML = rewards.map((r, i) => {
    let cls = "daily-day";
    let circleContent = i + 1;

    if (i < dayIndex) {
      cls += " claimed";
      circleContent = "&#10003;";
    } else if (i === dayIndex) {
      if (claimed) {
        cls += " claimed";
        circleContent = "&#10003;";
      } else {
        cls += " active";
      }
    } else {
      cls += " future";
    }

    return `
      <div class="${cls}">
        <div class="daily-day-num">Д${i + 1}</div>
        <div class="daily-day-circle">${circleContent}</div>
        <div class="daily-day-reward">${r} &#11088;</div>
      </div>`;
  }).join("");

  if (claimed) {
    btn.disabled = true;
    btn.textContent = "Получено \u2714";
  } else {
    btn.disabled = false;
    btn.innerHTML = `Забрать +${fmt(rewards[dayIndex])} &#11088;`;
  }
}

async function claimDaily() {
  const btn = $("#btnDailyClaim");
  if (!btn || btn.disabled) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="loading-spinner"></span>';
  haptic();

  const res = await api("/daily/claim", { method: "POST" });

  if (res.success) {
    haptic("success");
    toast(`+${fmt(res.reward)} USDT получено!`);
    showConfetti();
    if (userData) {
      userData.balance = res.balance;
      userData.login_streak = res.streak;
    }
    // Обновляем карточку
    await loadDaily();
  } else {
    haptic("error");
    toast(res.error || "Ошибка");
    btn.disabled = false;
    btn.textContent = "Забрать бонус";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#btnDailyClaim")?.addEventListener("click", claimDaily);
});

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
  ringGrad.addColorStop(0, "#1a1a2e");
  ringGrad.addColorStop(1, "#0e0e18");
  ctx.fillStyle = ringGrad;
  ctx.fill();

  // Dot markers
  for (let i = 0; i < n * 2; i++) {
    const dotAngle = (i / (n * 2)) * 2 * Math.PI - Math.PI / 2;
    const dotX = cx + (outerR - 4) * Math.cos(dotAngle);
    const dotY = cy + (outerR - 4) * Math.sin(dotAngle);
    ctx.beginPath();
    ctx.arc(dotX, dotY, 2, 0, 2 * Math.PI);
    ctx.fillStyle = i % 2 === 0 ? "rgba(255,255,255,.3)" : "rgba(33,150,243,.4)";
    ctx.fill();
  }

  // Slices
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(angle);

  for (let i = 0; i < n; i++) {
    const startAngle = i * arc - Math.PI / 2;
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

    ctx.strokeStyle = "rgba(0,0,0,.25)";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.save();
    ctx.rotate(startAngle + arc / 2);
    ctx.fillStyle = "#fff";
    ctx.font = "800 14px Nunito, -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.shadowColor = "rgba(0,0,0,.5)";
    ctx.shadowBlur = 4;
    ctx.fillText(String(wheelPrizes[i]), innerR * 0.62, 0);
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  ctx.restore();

  // Center circle
  ctx.beginPath();
  ctx.arc(cx, cy, 26, 0, 2 * Math.PI);
  ctx.fillStyle = "#1a1a2e";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, 23, 0, 2 * Math.PI);
  const centerGrad = ctx.createLinearGradient(cx - 23, cy - 23, cx + 23, cy + 23);
  centerGrad.addColorStop(0, "#2196F3");
  centerGrad.addColorStop(1, "#64B5F6");
  ctx.fillStyle = centerGrad;
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.font = "800 10px Nunito, sans-serif";
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
    cooldownTime.textContent = `${data.cooldown_hours}ч ${data.cooldown_minutes}м`;
  }

  $("#spinCost").textContent = data.paid_cost || 0.25;

  const histEl = $("#wheelHistory");
  if (data.history && data.history.length) {
    histEl.innerHTML = data.history.map((h) => `
      <div class="tx-item">
        <div class="tx-icon">&#9889;</div>
        <div class="tx-body">
          <div class="tx-title">${h.is_free ? "Бесплатный" : "Платный"} спин</div>
          <div class="tx-date">${h.time ? new Date(h.time).toLocaleString("ru") : ""}</div>
        </div>
        <div class="tx-right">
          <div class="tx-amount">+${fmt(h.reward)} &#11088;</div>
        </div>
      </div>
    `).join("");
  } else {
    histEl.innerHTML = `<p style="color:var(--text-sec);font-size:13px;text-align:center;padding:16px">Нет спинов</p>`;
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
    const ease = 1 - Math.pow(1 - t, 4);
    wheelAngle = startAngle + (targetAngle - startAngle) * ease;
    drawWheel(wheelAngle);
    if (t < 1) requestAnimationFrame(animate);
    else finishSpin(resultPromise);
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
    }
    setTimeout(() => resultEl.classList.add("hidden"), 5000);
  } else {
    haptic("error");
    toast(res.error || "Ошибка спина");
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
          <span class="ref-item-tasks">${r.tasks_completed} заданий</span>
        </div>
        <span class="ref-item-earnings">+${fmt(r.passive_earnings)}</span>
      </div>
    `).join("");
  } else {
    list.innerHTML = `<p style="color:var(--text-sec);font-size:13px;text-align:center;padding:16px">Нет рефералов. Поделитесь ссылкой!</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#btnCopyRef")?.addEventListener("click", () => {
    const input = $("#refLinkInput");
    if (!input.value) return;
    navigator.clipboard.writeText(input.value).then(() => {
      haptic("success");
      toast("Ссылка скопирована!");
    }).catch(() => {
      input.select();
      document.execCommand("copy");
      toast("Ссылка скопирована!");
    });
  });
});

// ─── Wallet ──────────────────────────────────────────────────────
let withdrawType = "usdt";

async function loadWallet() {
  if (userData) {
    const bal = userData.balance || 0;
    $("#walletBalanceBig").innerHTML = fmt(bal) + '<span class="wallet-balance-star">&#11088;</span>';
    $("#walletBalanceSub").innerHTML = `&asymp; ${fmt(bal * 0.018)} &#9410;`;
    if (userData.wallet_address) {
      const addr = userData.wallet_address;
      $("#walletAddr").textContent = addr.slice(0, 4) + "..." + addr.slice(-4);
    }
  }
  $("#minWithdraw").textContent = "1.0";

  // Load transaction history
  const data = await api("/history");
  if (data.error) return;

  const list = $("#txList");
  if (!data.withdrawals || data.withdrawals.length === 0) {
    list.innerHTML = `<p style="color:var(--text-sec);font-size:13px;text-align:center;padding:16px">Нет транзакций</p>`;
    return;
  }

  list.innerHTML = data.withdrawals.map((w) => `
    <div class="tx-item">
      <div class="tx-icon ${w.status === 'completed' ? '' : 'withdraw'}">&#9654;</div>
      <div class="tx-body">
        <div class="tx-title">${w.type.toUpperCase()} Вывод</div>
        <div class="tx-date">${w.requested_at ? timeAgo(w.requested_at) : ""}</div>
      </div>
      <div class="tx-right">
        <div class="tx-amount negative">-${fmt(w.amount)} &#11088;</div>
        <div class="tx-sub"><span class="status-badge ${w.status}">${statusRu(w.status)}</span></div>
      </div>
    </div>
  `).join("");
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Сегодня";
  if (days === 1) return "Вчера";
  return days + "д назад";
}

function statusRu(s) {
  if (s === "pending") return "ожидание";
  if (s === "completed") return "готово";
  if (s === "failed" || s === "rejected") return "отклонено";
  return s;
}

document.addEventListener("DOMContentLoaded", () => {
  // Toggle withdraw form
  $("#btnShowWithdraw")?.addEventListener("click", () => {
    const form = $("#withdrawFormCard");
    form.classList.toggle("hidden");
    haptic();
  });

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
      resultEl.textContent = "Минимальная сумма вывода: 1.0 USDT";
      resultEl.classList.remove("hidden");
      return;
    }
    if (!wallet) {
      haptic("error");
      resultEl.className = "withdraw-result error";
      resultEl.textContent = "Введите адрес кошелька";
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
      resultEl.textContent = `Вывод #${res.withdrawal_id} отправлен! Баланс: ${fmt(res.balance)} USDT`;
      resultEl.classList.remove("hidden");
      if (userData) {
        userData.balance = res.balance;
        userData.wallet_address = wallet;
      }
      $("#withdrawAmount").value = "";
      $("#withdrawWallet").value = "";
      loadWallet();
    } else {
      haptic("error");
      resultEl.className = "withdraw-result error";
      resultEl.textContent = res.error || "Ошибка вывода";
      resultEl.classList.remove("hidden");
    }

    btn.disabled = false;
    btn.textContent = "Запросить вывод";
  });
});

// ─── Profile (includes leaderboard) ──────────────────────────────
async function loadProfile() {
  if (!userData) return;

  // Avatar
  const initial = (userData.first_name || userData.username || "T")[0].toUpperCase();
  const avatarEl = $("#profileAvatar");
  if (tg?.initDataUnsafe?.user?.photo_url) {
    avatarEl.innerHTML = `<img src="${tg.initDataUnsafe.user.photo_url}" alt="">`;
  } else {
    avatarEl.textContent = initial;
  }

  // Username
  const username = userData.username ? "@" + userData.username : (userData.first_name || "User");
  $("#profileUsername").textContent = username;

  // Streak
  const streak = userData.login_streak || 0;
  const streakText = streak + " " + pluralDays(streak);
  $("#profileStreak").textContent = streakText;

  // Stats
  const earned = userData.total_earned || 0;
  $("#profileEarned").innerHTML = fmt(earned) + ' <span style="font-size:16px">&#11088;</span>';
  $("#profileEarnedSub").innerHTML = `&asymp; $${fmt(earned * 0.018)} &#9410;`;
  $("#profileTasks").textContent = userData.tasks_completed || 0;
  $("#profileFriends").textContent = userData.referral_count || 0;

  // Load leaderboard
  const data = await api("/leaderboard");
  const list = $("#leadersList");
  if (!data.leaders || data.leaders.length === 0) {
    list.innerHTML = `<p style="color:#999;text-align:center;padding:12px;font-size:13px">Пока нет лидеров</p>`;
    return;
  }

  list.innerHTML = data.leaders.slice(0, 5).map((l, i) => {
    const rank = i + 1;
    const initials = (l.name || "?").slice(0, 2).toUpperCase();
    const isMe = data.my_id === l.user_id;
    return `
      <div class="leader-row" ${isMe ? 'style="background:rgba(33,150,243,.08);border-color:rgba(33,150,243,.15)"' : ""}>
        <div class="leader-rank-num">${rank}</div>
        <div class="leader-avatar-sm">${initials}</div>
        <div class="leader-info">
          <div class="leader-name">@${esc(l.name)} &#11088;</div>
        </div>
        <div class="leader-earned-col">
          <div class="leader-earned-stars">${fmt(l.total_earned)} &#11088;</div>
          <div class="leader-earned-ton">&asymp; $${fmt(l.total_earned * 0.018)} &#9410;</div>
        </div>
      </div>
    `;
  }).join("");
}

function pluralDays(n) {
  const abs = Math.abs(n) % 100;
  const last = abs % 10;
  if (abs > 10 && abs < 20) return "Дней";
  if (last > 1 && last < 5) return "Дня";
  if (last === 1) return "День";
  return "Дней";
}

// ═════════════════════════════════════════════════════════════════
// ─── ADMIN PANEL ─────────────────────────────────────────────────
// ═════════════════════════════════════════════════════════════════

async function loadAdmin() {
  if (!isAdmin) return;

  const stats = await api("/admin/stats");
  if (!stats.error) {
    $("#adminTotalUsers").textContent = stats.total_users || 0;
    $("#adminNewUsers").textContent = stats.new_users_24h || 0;
    $("#adminBankBalance").textContent = fmt(stats.bank_balance);
    $("#adminPendingW").textContent = stats.pending_withdrawals || 0;
  }

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

async function adminShowTasks() {
  haptic();
  adminShowSubPage('<div style="text-align:center;padding:20px"><span class="loading-spinner"></span></div>');

  const data = await api("/admin/tasks");
  if (data.error) {
    adminShowSubPage(`<p style="color:var(--red);padding:16px">${data.error}</p>`);
    return;
  }

  let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <h3 style="font-size:16px;font-weight:700">Все задания</h3>
    <button class="btn btn-sm btn-secondary" onclick="adminBack()">Назад</button>
  </div>`;

  if (!data.tasks || data.tasks.length === 0) {
    html += `<p style="color:var(--text-sec);text-align:center;padding:20px">Нет заданий</p>`;
  } else {
    data.tasks.forEach((t) => {
      html += `
        <div class="admin-task-item">
          <div class="admin-task-status">${t.is_active ? "&#9989;" : "&#10060;"}</div>
          <div class="admin-task-body">
            <div class="admin-task-title">#${t.id} ${esc(t.title)}</div>
            <div class="admin-task-meta">${fmt(t.reward)} USDT | ${t.total_completions} выполнено</div>
          </div>
          <div class="admin-task-actions">
            <button class="btn btn-sm ${t.is_active ? "btn-secondary" : "btn-success"}" onclick="adminToggleTask(${t.id})">${t.is_active ? "Выкл" : "Вкл"}</button>
            <button class="btn btn-sm btn-danger" onclick="adminDeleteTask(${t.id})">Удал</button>
          </div>
        </div>`;
    });
  }
  adminShowSubPage(html);
}

async function adminToggleTask(taskId) {
  haptic();
  const res = await api(`/admin/tasks/${taskId}/toggle`, { method: "POST" });
  if (res.success) { toast("Задание обновлено"); adminShowTasks(); }
  else toast(res.error || "Ошибка");
}

async function adminDeleteTask(taskId) {
  if (!confirm("Удалить задание?")) return;
  haptic();
  const res = await api(`/admin/tasks/${taskId}`, { method: "DELETE" });
  if (res.success) { toast("Задание удалено"); adminShowTasks(); }
  else toast(res.error || "Ошибка");
}

async function adminShowWithdrawals() {
  haptic();
  adminShowSubPage('<div style="text-align:center;padding:20px"><span class="loading-spinner"></span></div>');

  const data = await api("/admin/withdrawals");
  if (data.error) {
    adminShowSubPage(`<p style="color:var(--red);padding:16px">${data.error}</p>`);
    return;
  }

  let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <h3 style="font-size:16px;font-weight:700">Ожидающие вывода</h3>
    <button class="btn btn-sm btn-secondary" onclick="adminBack()">Назад</button>
  </div>`;

  if (!data.withdrawals || data.withdrawals.length === 0) {
    html += `<p style="color:var(--text-sec);text-align:center;padding:20px">Нет ожидающих выводов</p>`;
  } else {
    data.withdrawals.forEach((w) => {
      html += `
        <div class="admin-withdrawal-item">
          <div class="admin-withdrawal-header">
            <span class="admin-withdrawal-user">@${esc(w.username || "user_" + w.user_id)}</span>
            <span class="admin-withdrawal-amount">${fmt(w.amount)} ${(w.type || "usdt").toUpperCase()}</span>
          </div>
          <div class="admin-withdrawal-wallet">${esc(w.wallet)}</div>
          <div class="admin-withdrawal-actions">
            <button class="btn btn-sm btn-success" onclick="adminApproveW(${w.id})">Одобрить</button>
            <button class="btn btn-sm btn-danger" onclick="adminRejectW(${w.id})">Отклонить</button>
          </div>
        </div>`;
    });
  }
  adminShowSubPage(html);
}

async function adminApproveW(id) {
  haptic();
  const res = await api(`/admin/withdrawals/${id}/approve`, { method: "POST" });
  if (res.success) { toast("Одобрено"); adminShowWithdrawals(); }
  else toast(res.error || "Ошибка");
}

async function adminRejectW(id) {
  haptic();
  const res = await api(`/admin/withdrawals/${id}/reject`, { method: "POST" });
  if (res.success) { toast("Отклонено"); adminShowWithdrawals(); }
  else toast(res.error || "Ошибка");
}

function adminShowBroadcast() {
  haptic();
  const html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="font-size:16px;font-weight:700">Рассылка</h3>
      <button class="btn btn-sm btn-secondary" onclick="adminBack()">Назад</button>
    </div>
    <div class="admin-form">
      <div class="form-group">
        <label>Сообщение (HTML)</label>
        <textarea class="admin-broadcast-textarea" id="broadcastText" placeholder="Введите сообщение для всех пользователей..."></textarea>
      </div>
      <button class="btn btn-primary btn-block" id="btnBroadcast" onclick="adminSendBroadcast()">Отправить рассылку</button>
      <div id="broadcastResult" class="hidden" style="margin-top:12px;padding:12px;border-radius:10px;text-align:center;font-size:14px"></div>
    </div>
  `;
  adminShowSubPage(html);
}

async function adminSendBroadcast() {
  const text = $("#broadcastText")?.value?.trim();
  if (!text) { toast("Введите сообщение"); return; }
  if (!confirm("Отправить сообщение ВСЕМ пользователям?")) return;

  haptic();
  const btn = $("#btnBroadcast");
  btn.disabled = true;
  btn.innerHTML = '<span class="loading-spinner"></span> Отправка...';

  const res = await api("/admin/broadcast", {
    method: "POST",
    body: JSON.stringify({ text }),
  });

  const resultEl = $("#broadcastResult");
  resultEl.classList.remove("hidden");
  if (res.success) {
    resultEl.style.background = "rgba(76,175,80,.1)";
    resultEl.style.color = "var(--green-light)";
    resultEl.textContent = `Отправлено: ${res.success_count} | Ошибок: ${res.failed_count}`;
    haptic("success");
  } else {
    resultEl.style.background = "rgba(255,107,107,.1)";
    resultEl.style.color = "var(--red)";
    resultEl.textContent = res.error || "Ошибка рассылки";
  }

  btn.disabled = false;
  btn.textContent = "Отправить рассылку";
}

function adminShowCreateTask() {
  haptic();
  const html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="font-size:16px;font-weight:700">Создать задание</h3>
      <button class="btn btn-sm btn-secondary" onclick="adminBack()">Назад</button>
    </div>
    <div class="admin-form">
      <div class="form-group">
        <label>Название</label>
        <input type="text" class="form-input" id="newTaskTitle" placeholder="Подписка на канал">
      </div>
      <div class="form-group">
        <label>Описание</label>
        <input type="text" class="form-input" id="newTaskDesc" placeholder="Описание задания...">
      </div>
      <div class="form-group">
        <label>Награда (USDT)</label>
        <input type="number" class="form-input" id="newTaskReward" placeholder="0.01" step="0.001" min="0.001">
      </div>
      <div class="form-group">
        <label>Username канала (без @)</label>
        <input type="text" class="form-input" id="newTaskChannel" placeholder="channel_name">
      </div>
      <button class="btn btn-primary btn-block" onclick="adminCreateTask()">Создать</button>
    </div>
  `;
  adminShowSubPage(html);
}

async function adminCreateTask() {
  const title = $("#newTaskTitle")?.value?.trim();
  const description = $("#newTaskDesc")?.value?.trim();
  const reward = parseFloat($("#newTaskReward")?.value);
  const channel = $("#newTaskChannel")?.value?.trim();

  if (!title) { toast("Введите название"); return; }
  if (!reward || reward < 0.001) { toast("Введите награду"); return; }
  if (!channel) { toast("Введите username канала"); return; }

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
    toast("Задание создано!");
    adminShowTasks();
  } else {
    haptic("error");
    toast(res.error || "Ошибка создания");
  }
}

// ─── Boot ────────────────────────────────────────────────────────
initStickers();
init();

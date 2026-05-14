/**
 * HC MVP — LIFF 會員前端 (Phase 2, v0.2.0)
 *
 * 流程：
 *  1. LIFF init → 取得 access token → POST /api/auth/line/verify → 暫存 line_user_id
 *  2a. 已存在用戶 → GET /api/users/line/{id} → 直接進使用者首頁
 *  2b. 新用戶 → OTP 流程 → POST /api/users/register → 進使用者首頁
 */

const LIFF_ID = window.__LIFF_ID__ || "";

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  lineUserId:  null,   // string
  phone:       null,   // E.164 string
  verifyToken: null,   // string from /api/otp/verify
  user:        null,   // { name, phone, email }
};

const APP_VIEWS = new Set(["step-home", "step-member"]);

// ── DOM helpers ───────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function showStep(id) {
  document.querySelectorAll(".step").forEach((el) => el.classList.add("hidden"));
  $(id).classList.remove("hidden");
  $("main-header").classList.toggle("hidden", APP_VIEWS.has(id));
}

function showError(elementId, msg) {
  const el = $(elementId);
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError(elementId) {
  $(elementId).classList.add("hidden");
}

function setLoading(btn, loading) {
  btn.disabled = loading;
  btn.textContent = loading ? "請稍候…" : btn.dataset.label;
}

// ── API helpers ───────────────────────────────────────────────────────────
async function apiPost(path, body) {
  const resp = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = data.detail || `HTTP ${resp.status}`;
    throw Object.assign(new Error(detail), { status: resp.status, data });
  }
  return data;
}

async function apiGet(path) {
  const resp = await fetch(path);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = data.detail || `HTTP ${resp.status}`;
    throw Object.assign(new Error(detail), { status: resp.status, data });
  }
  return data;
}

// ── Member helpers ─────────────────────────────────────────────────────────
async function checkExistingUser(lineUserId) {
  try {
    return await apiGet(`/api/users/line/${encodeURIComponent(lineUserId)}`);
  } catch (err) {
    if (err.status === 404) return null;
    throw err;
  }
}

function formatPhoneDisplay(e164) {
  // +886xxxxxxxxx → 09xxxxxxxx
  return "0" + e164.slice(4);
}

function populateMember(user) {
  $("member-name").textContent  = user.name;
  $("member-phone").textContent = formatPhoneDisplay(user.phone);
  $("member-email").textContent = user.email;
}

let _toastTimer = null;
function showComingSoon() {
  const toast = $("toast");
  toast.classList.add("visible");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => toast.classList.remove("visible"), 2200);
}

// ── Step 1: LIFF init ──────────────────────────────────────────────────────
async function initLiff() {
  showStep("step-init");
  try {
    await liff.init({ liffId: LIFF_ID });

    if (!liff.isLoggedIn()) {
      liff.login({ redirectUri: location.href });
      return;
    }

    const accessToken = liff.getAccessToken();
    const { line_user_id } = await apiPost("/api/auth/line/verify", { access_token: accessToken });
    state.lineUserId = line_user_id;

    const existing = await checkExistingUser(line_user_id);
    if (existing) {
      state.user = existing;
      populateMember(existing);
      showStep("step-home");
    } else {
      showStep("step-phone");
    }
  } catch (err) {
    $("global-error-msg").textContent =
      "LINE 身份驗證失敗，請關閉後重新開啟。\n(" + err.message + ")";
    showStep("step-error");
  }
}

// ── Step 2: Send OTP ───────────────────────────────────────────────────────
function normalisePhone(raw) {
  const cleaned = raw.replace(/\D/g, "");
  if (/^09\d{8}$/.test(cleaned)) return cleaned;
  return null;
}

async function handleSendOtp() {
  hideError("phone-error");
  const raw   = $("phone-input").value.trim();
  const phone = normalisePhone(raw);

  if (!phone) {
    showError("phone-error", "請輸入正確的台灣手機號碼（09xxxxxxxx）");
    return;
  }

  const btn = $("btn-send-otp");
  setLoading(btn, true);
  try {
    await apiPost("/api/otp/send", { phone });
    state.phone = "+886" + phone.slice(1);
    $("otp-phone-display").textContent = phone;
    showStep("step-otp");
  } catch (err) {
    const msg = err.status === 429
      ? "今日驗證碼發送次數已達上限（3 次），請明日再試。"
      : "發送失敗，請稍後再試。";
    showError("phone-error", msg);
  } finally {
    setLoading(btn, false);
  }
}

// ── Step 3: Verify OTP ─────────────────────────────────────────────────────
async function handleVerifyOtp() {
  hideError("otp-error");
  const code = $("otp-input").value.trim();

  if (!/^\d{6}$/.test(code)) {
    showError("otp-error", "請輸入 6 位數字驗證碼");
    return;
  }

  const btn = $("btn-verify-otp");
  setLoading(btn, true);
  try {
    const { token } = await apiPost("/api/otp/verify", { phone: state.phone, code });
    state.verifyToken = token;
    showStep("step-profile");
  } catch (err) {
    showError("otp-error", "驗證碼錯誤或已過期，請確認後再試。");
  } finally {
    setLoading(btn, false);
  }
}

// ── Step 4: Register ───────────────────────────────────────────────────────
function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

async function handleRegister() {
  hideError("profile-error");
  const name  = $("name-input").value.trim();
  const email = $("email-input").value.trim();

  if (!name)                 { showError("profile-error", "請輸入姓名"); return; }
  if (!validateEmail(email)) { showError("profile-error", "請輸入有效的 Email 地址"); return; }

  const btn = $("btn-register");
  setLoading(btn, true);
  try {
    await apiPost("/api/users/register", {
      line_user_id: state.lineUserId,
      phone:        state.phone,
      verify_token: state.verifyToken,
      name,
      email,
    });
    state.user = { name, phone: state.phone, email };
    populateMember(state.user);
    showStep("step-home");
  } catch (err) {
    showError("profile-error", "註冊失敗，請稍後再試。(" + err.message + ")");
  } finally {
    setLoading(btn, false);
  }
}

// ── Event wiring ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  ["btn-send-otp", "btn-verify-otp", "btn-register"].forEach((id) => {
    const el = $(id);
    if (el) el.dataset.label = el.textContent;
  });

  $("btn-send-otp")    ?.addEventListener("click", handleSendOtp);
  $("btn-verify-otp")  ?.addEventListener("click", handleVerifyOtp);
  $("btn-resend-otp")  ?.addEventListener("click", () => {
    showStep("step-phone");
    $("otp-input").value = "";
  });
  $("btn-register")    ?.addEventListener("click", handleRegister);

  $("btn-to-member")    ?.addEventListener("click", () => showStep("step-member"));
  $("btn-to-home")      ?.addEventListener("click", () => showStep("step-home"));
  $("btn-start-booking")?.addEventListener("click", showComingSoon);
  $("btn-my-booking")   ?.addEventListener("click", showComingSoon);

  $("phone-input") ?.addEventListener("keydown", (e) => e.key === "Enter" && handleSendOtp());
  $("otp-input")   ?.addEventListener("keydown", (e) => e.key === "Enter" && handleVerifyOtp());
  $("email-input") ?.addEventListener("keydown", (e) => e.key === "Enter" && handleRegister());

  initLiff();
});

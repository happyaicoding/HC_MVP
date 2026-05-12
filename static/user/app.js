/**
 * HC MVP — LIFF 會員註冊前端
 *
 * 流程：
 *  1. LIFF init → 取得 access token → POST /api/auth/line/verify → 暫存 line_user_id
 *  2. 使用者輸入手機 → POST /api/otp/send
 *  3. 使用者輸入 OTP → POST /api/otp/verify → 取得 verify_token
 *  4. 使用者填寫姓名/Email → POST /api/users/register
 *  5. 顯示成功畫面
 */

const LIFF_ID = document.currentScript?.dataset?.liffId
  || window.__LIFF_ID__
  || "";          // 由後端注入或 .env 提供；見 index.html meta tag

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  lineUserId:   null,   // string
  phone:        null,   // E.164 string
  verifyToken:  null,   // string from /api/otp/verify
};

// ── DOM helpers ───────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function showStep(id) {
  document.querySelectorAll(".step").forEach((el) => el.classList.add("hidden"));
  $(id).classList.remove("hidden");
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
    showStep("step-phone");
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
  const raw = $("phone-input").value.trim();
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

  if (!name)                  { showError("profile-error", "請輸入姓名"); return; }
  if (!validateEmail(email))  { showError("profile-error", "請輸入有效的 Email 地址"); return; }

  const btn = $("btn-register");
  setLoading(btn, true);
  try {
    await apiPost("/api/users/register", {
      line_user_id:  state.lineUserId,
      phone:         state.phone,
      verify_token:  state.verifyToken,
      name,
      email,
    });
    showStep("step-done");
    // Close LIFF window after 2s if running inside LINE
    if (liff.isInClient()) setTimeout(() => liff.closeWindow(), 2000);
  } catch (err) {
    showError("profile-error", "註冊失敗，請稍後再試。(" + err.message + ")");
  } finally {
    setLoading(btn, false);
  }
}

// ── Event wiring ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Store button labels for setLoading restore
  ["btn-send-otp", "btn-verify-otp", "btn-register"].forEach((id) => {
    const el = $(id);
    if (el) el.dataset.label = el.textContent;
  });

  $("btn-send-otp")   ?.addEventListener("click", handleSendOtp);
  $("btn-verify-otp") ?.addEventListener("click", handleVerifyOtp);
  $("btn-resend-otp") ?.addEventListener("click", () => {
    showStep("step-phone");
    $("otp-input").value = "";
  });
  $("btn-register")   ?.addEventListener("click", handleRegister);

  // Allow Enter key submission on inputs
  $("phone-input") ?.addEventListener("keydown", (e) => e.key === "Enter" && handleSendOtp());
  $("otp-input")   ?.addEventListener("keydown", (e) => e.key === "Enter" && handleVerifyOtp());
  $("email-input") ?.addEventListener("keydown", (e) => e.key === "Enter" && handleRegister());

  initLiff();
});

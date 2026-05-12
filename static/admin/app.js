/**
 * HC MVP — Admin 後台前端
 *
 * 流程：
 *  1. 嘗試取得使用者列表；若 401 → 顯示登入畫面
 *  2. 登入成功 → 顯示後台主畫面
 *  3. 支援客戶端搜尋（姓名 / 手機 / Email）與分頁
 */

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  allUsers:   [],     // 全部已載入的 user 物件
  filtered:   [],     // 搜尋後結果
  page:       1,
  pageSize:   50,
  totalServer: 0,
};

// ── DOM helpers ───────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function showView(id) {
  document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
  $(id).classList.remove("hidden");
}

function setLoading(btn, loading) {
  btn.disabled = loading;
  btn.textContent = loading ? "請稍候…" : btn.dataset.label;
}

// ── API helpers ───────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const resp = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw Object.assign(new Error(data.detail || `HTTP ${resp.status}`), { status: resp.status });
  return data;
}

// ── Load users from server (all pages, up to 1000 rows for MVP) ──────────
async function loadAllUsers() {
  const PAGE_SIZE = 200;
  let page = 1;
  const all = [];
  while (true) {
    const data = await apiFetch(`/api/admin/users?page=${page}&size=${PAGE_SIZE}`);
    all.push(...data.items);
    state.totalServer = data.total;
    if (all.length >= data.total || data.items.length < PAGE_SIZE) break;
    page++;
  }
  state.allUsers = all;
}

// ── Rendering ─────────────────────────────────────────────────────────────
function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString("zh-TW", {
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function applyFilter(query) {
  const q = query.toLowerCase().trim();
  state.filtered = q
    ? state.allUsers.filter((u) =>
        u.name.toLowerCase().includes(q) ||
        u.phone.includes(q) ||
        u.email.toLowerCase().includes(q)
      )
    : [...state.allUsers];
  state.page = 1;
  render();
}

function render() {
  const { filtered, page, pageSize } = state;
  const start  = (page - 1) * pageSize;
  const slice  = filtered.slice(start, start + pageSize);
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));

  // Badge
  $("total-badge").textContent = `共 ${state.allUsers.length} 人`;

  // Table rows
  const tbody = $("table-body");
  if (slice.length === 0) {
    tbody.innerHTML = "";
    $("no-data").classList.remove("hidden");
  } else {
    $("no-data").classList.add("hidden");
    tbody.innerHTML = slice
      .map(
        (u, i) => `<tr>
          <td>${start + i + 1}</td>
          <td>${esc(u.name)}</td>
          <td>${esc(u.phone)}</td>
          <td>${esc(u.email)}</td>
          <td class="uid" title="${esc(u.line_user_id)}">${esc(u.line_user_id)}</td>
          <td>${formatDate(u.registered_at)}</td>
        </tr>`
      )
      .join("");
  }

  // Pagination
  const pg = $("pagination");
  if (totalPages <= 1) { pg.innerHTML = ""; return; }

  const buttons = [];
  // Prev
  buttons.push(`<button class="page-btn" ${page === 1 ? "disabled" : ""} data-p="${page - 1}">‹</button>`);
  // Page numbers (show at most 7 around current)
  const range = pageRange(page, totalPages);
  range.forEach((p) => {
    if (p === "…") {
      buttons.push(`<span class="page-btn" style="cursor:default">…</span>`);
    } else {
      buttons.push(`<button class="page-btn ${p === page ? "active" : ""}" data-p="${p}">${p}</button>`);
    }
  });
  // Next
  buttons.push(`<button class="page-btn" ${page === totalPages ? "disabled" : ""} data-p="${page + 1}">›</button>`);
  pg.innerHTML = buttons.join("");
}

function pageRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = new Set([1, total, current]);
  for (let d = -2; d <= 2; d++) {
    const p = current + d;
    if (p >= 1 && p <= total) pages.add(p);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  const result = [];
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) result.push("…");
    result.push(p);
    prev = p;
  }
  return result;
}

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Event handlers ────────────────────────────────────────────────────────
async function handleLogin() {
  $("login-error").classList.add("hidden");
  const username = $("username").value.trim();
  const password = $("password").value;

  if (!username || !password) {
    $("login-error").textContent = "請輸入帳號與密碼";
    $("login-error").classList.remove("hidden");
    return;
  }

  const btn = $("btn-login");
  setLoading(btn, true);
  try {
    await apiFetch("/api/admin/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    await enterDashboard();
  } catch (err) {
    $("login-error").textContent =
      err.status === 401 ? "帳號或密碼錯誤" : "登入失敗，請稍後再試";
    $("login-error").classList.remove("hidden");
  } finally {
    setLoading(btn, false);
  }
}

async function enterDashboard() {
  await loadAllUsers();
  applyFilter("");
  showView("view-dashboard");
}

async function handleLogout() {
  try { await apiFetch("/api/admin/logout", { method: "POST" }); } catch { /* ignore */ }
  showView("view-login");
  $("username").value = "";
  $("password").value = "";
  $("search-input").value = "";
}

// ── Bootstrap ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // Button events
  $("btn-login").addEventListener("click", handleLogin);
  $("btn-logout").addEventListener("click", handleLogout);
  $("password").addEventListener("keydown", (e) => e.key === "Enter" && handleLogin());

  // Search (debounced)
  let searchTimer;
  $("search-input").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => applyFilter(e.target.value), 250);
  });

  // Pagination delegation
  $("pagination").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-p]");
    if (!btn || btn.disabled) return;
    state.page = Number(btn.dataset.p);
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // Try auto-enter dashboard (already logged in?)
  try {
    await enterDashboard();
  } catch (err) {
    if (err.status === 401) {
      showView("view-login");
    } else {
      showView("view-login");
    }
  }
});

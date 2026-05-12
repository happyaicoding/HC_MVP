# Phase 3 工作說明書

**專案**：HC MVP — LIFF 會員系統  
**Phase**：3 — LINE LIFF 整合與使用者註冊  
**完成日期**：2025-05-11  
**分支**：`develop`  
**Commit**：`e1fb9e3`

---

## 完成項目

| # | 項目 | 檔案 |
|---|------|------|
| 1 | LINE LIFF access token 驗證服務 | `app/services/line_service.py` |
| 2 | Pydantic schemas（LineVerify、Register、UserOut） | `app/schemas/auth.py`, `app/schemas/user.py` |
| 3 | LINE auth 路由（POST /api/auth/line/verify） | `app/routers/auth.py` |
| 4 | 使用者註冊路由（POST /api/users/register） | `app/routers/users.py` |
| 5 | 路由注冊 + Jinja2 GET / 頁面路由（注入 LIFF_ID） | `app/main.py` |
| 6 | LIFF 前端頁面（HTML/CSS/JS，RWD） | `static/user/`, `templates/user/index.html` |
| 7 | 測試（LINE service 9 個 + 使用者 8 個） | `tests/test_auth.py`, `tests/test_users.py` |

---

## 關鍵技術決定

### LIFF_ID 注入
LIFF SDK 需要在前端以 JavaScript 呼叫 `liff.init({ liffId: "..." })`。LIFF ID 屬敏感設定，不應硬寫在靜態檔案中。解決方式：以 Jinja2 Template 在 `GET /` 時將 `settings.liff_id` 注入為 `window.__LIFF_ID__`，前端 `app.js` 讀取此全域變數。

### Dataclass Exception `__post_init__`
`@dataclass` 繼承 `Exception` 時，Python 不會自動呼叫 `Exception.__init__(*args)`，導致 `str(exc)` 為空字串。加入 `__post_init__` 呼叫 `super().__init__(self.failure_reason)` 後，`pytest.raises(match=...)` 與一般例外訊息顯示均正常。此修正同時套用於 `LineAuthError` 與 `TwilioError`。

### Verify Token 雙重驗證
`POST /api/users/register` 驗證步驟：
1. `otp_service.verify_token(body.verify_token)` — itsdangerous 解簽並確認未過期
2. `token_phone == body.phone` — 確認 token 中的手機號碼與請求一致，防止 token 被跨手機重用

### 手機號碼覆寫（Q7）
相同手機若已存在使用者，`upsert` 邏輯更新 `line_user_id`、`name`、`email`、`updated_at`，資料列不重複建立。

---

## 測試結果

```
36 passed in 7.66s

tests/test_auth.py  (9)   LIFF token 驗證全情境
tests/test_users.py (8)   註冊、覆寫、token 驗證、頁面渲染
tests/test_otp.py   (18)  (Phase 2，持續通過)
tests/test_health.py (1)  (Phase 1，持續通過)
```

---

## 前端頁面路徑

| 路徑 | 說明 |
|------|------|
| `GET /` | LIFF 使用者註冊頁（Jinja2，含 LIFF_ID） |
| `/static/user/style.css` | 樣式（LINE 綠色主題，RWD） |
| `/static/user/app.js` | 5 步驟流程邏輯 |

---

## 下一步（Phase 4）

- `app/schemas/admin.py`：AdminLoginRequest、UserListResponse
- `app/routers/admin.py`：POST /api/admin/login、GET /api/admin/users、POST /api/admin/logout
- `static/admin/`：管理者登入頁 + 使用者清單表格（RWD）
- `tests/test_admin.py`：admin 登入/權限/查詢 unit tests

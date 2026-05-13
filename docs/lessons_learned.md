# Lessons Learned — HC MVP 部署與除錯

> 記錄 v0.1.0 上線後實際遭遇的問題、根本原因與改善對策。

---

## LL-01 · LIFF ID 字元混淆（l vs I）

### 症狀
```
LIFF app '2010071215-yghPwGil' was not found.
```

### 根本原因
LIFF ID 最後一個字元為大寫 `I`（i），從 LINE Developers Console 複製時，
在多數字型下與小寫 `l`（L）幾乎無法區分，導致 `.env` 寫入錯誤字元。

| 位置 | 值 |
|------|-----|
| `.env`（錯誤）| `2010071215-yghPwGi**l**` |
| LINE Console（正確）| `2010071215-yghPwGi**I**` |

### 對策
1. **複製後立即驗證**：在 LINE Developers Console 點「Copy」按鈕，貼入後用肉眼逐字比對末尾字元。
2. **程式層防禦**：`app/config.py` 加入 `@field_validator("liff_id")` 自動 strip 空白；
   若 ID 為空則啟動時立即拋錯，避免靜默失敗。
3. **字型建議**：在 `.env` 或設定檔使用等寬字型（如 Consolas、Fira Code），可區分 `l`、`I`、`1`。

### 修正 commit
`5d1a5f3` — fix: strip LIFF_ID whitespace and use tojson for safe JS injection

---

## LL-02 · LIFF ID 空白字元（copy-paste artifact）

### 症狀
無明顯錯誤訊息，但 `liff.init()` 靜默失敗，或 LINE token 驗證時 channel mismatch。

### 根本原因
從 LINE Developers Console 複製 LIFF ID 貼入 `.env` 時，前後可能夾帶空格或換行，
`pydantic-settings` 預設不做 strip，導致 `settings.liff_id = " 2010071215-xxx "` 含空白。

此空白會傳播到：
- `liff.init({ liffId: " 2010071215-xxx " })` → LINE SDK 初始化失敗
- `settings.liff_id.split("-")[0]` → channel_id 含前置空白 → token 驗證 mismatch

### 對策
在 `Settings` 加入 validator，於啟動時清除：
```python
@field_validator("liff_id")
@classmethod
def _strip_liff_id(cls, v: str) -> str:
    stripped = v.strip()
    if not stripped:
        raise ValueError("LIFF_ID must not be empty")
    return stripped
```

### 修正 commit
`5d1a5f3` — fix: strip LIFF_ID whitespace and use tojson for safe JS injection

---

## LL-03 · 錯誤的 LINE Token 驗證端點

### 症狀
```
LINE 身份驗證失敗，請關閉後重新開啟。(invalid liff token)
後端 log: 401 Unauthorized on /api/auth/line/verify
```

### 根本原因
使用了錯誤的 LINE API 端點驗證 LIFF token：

| | 舊做法（錯誤）| 新做法（正確）|
|---|---|---|
| 端點 | `GET /oauth2/v2.1/verify?access_token=...` | `GET /v2/profile` |
| 適用 token 類型 | Channel access token（後端對後端）| User access token ✅ |
| Token 來源 | LINE 後台核發給伺服器 | `liff.getAccessToken()` 核發給使用者 |
| User ID 欄位 | `sub`（需 openid scope） | `userId`（直接提供）|

`liff.getAccessToken()` 取得的是 **LINE Login user access token**，
應以 `Authorization: Bearer <token>` 呼叫 `/v2/profile`，而非將 token 以 query param 傳入 verify 端點。

### LINE API 端點對照

```
# ❌ 用於 channel access token (server-to-server)
GET https://api.line.me/oauth2/v2.1/verify?access_token={channel_token}

# ✅ 用於 LIFF user access token
GET https://api.line.me/v2/profile
Authorization: Bearer {user_access_token}
```

### 對策
1. LIFF token 驗證一律使用 `/v2/profile`，HTTP 200 即代表 token 有效。
2. `userId` 欄位即為 LINE user ID，無需額外的 channel ID 比對。
3. 若需確認 token 所屬 channel，可另外呼叫 `/oauth2/v2.1/verify`（但對 LIFF 流程通常不必要）。

### 修正 commit
`b9155ef` — fix: use /v2/profile to verify LIFF user access token

---

## LL-04 · 前端 JS 注入安全性

### 症狀
無直接錯誤，但存在潛在 XSS 風險。

### 根本原因
Jinja2 的 `{{ variable }}` 做的是 **HTML escape**（`<` → `&lt;`），
不是 **JavaScript string escape**。若 LIFF ID 含特殊字元（單引號、反斜線），
直接嵌入 JS 字串會產生語法錯誤或注入漏洞。

```html
<!-- ❌ 只做 HTML escape，JS context 不安全 -->
<script>window.__LIFF_ID__ = "{{ liff_id }}";</script>

<!-- ✅ tojson filter 輸出合法 JSON 字串字面值，含引號且正確 escape -->
<script>window.__LIFF_ID__ = {{ liff_id | tojson }};</script>
```

### 對策
在 Jinja2 template 中凡將變數注入 `<script>` 區塊，一律使用 `| tojson` filter。

### 修正 commit
`5d1a5f3` — fix: strip LIFF_ID whitespace and use tojson for safe JS injection

---

## 通用教訓

| # | 教訓 | 實踐 |
|---|------|------|
| 1 | **ENV 值在啟動時就驗證** | 用 pydantic `@field_validator` 在 process 啟動時 fail fast，比執行期才出錯好除錯 |
| 2 | **查官方文件確認端點用途** | LINE 有多個 token 相關端點，用途不同；先看「適用 token 類型」再選 |
| 3 | **Log 要包含原始回應** | 中介層只拋自訂錯誤碼時，原始 API response body 必須記到 log，否則無法診斷 |
| 4 | **模板注入依 context 選 escape** | HTML context → `{{ }}`；JS context → `| tojson`；URL context → `| urlencode` |
| 5 | **字元混淆高風險欄位要測試** | `l`/`I`/`1`、`O`/`0` 在 ID 類欄位是常見陷阱，單元測試加入「字元相似值」的 case |

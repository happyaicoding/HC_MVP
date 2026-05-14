# Phase 2 工作說明書 — 使用者首頁 & 會員專區

**版本：** v0.2.0
**日期：** 2026-05-14
**基準：** v1.0.0-mvp（commit 1dc5e98）

---

## 背景

MVP（Phase 1–5）完成後，使用者開啟 LIFF 只能看到 OTP 註冊流程。Phase 2 目標：為已完成註冊的用戶提供使用者首頁，新用戶完成 OTP 後也直接進入首頁，不再關閉視窗。

---

## 新增功能

### 1. 後端 API — `GET /api/users/line/{line_user_id}`

| 項目 | 說明 |
|------|------|
| 路徑 | `GET /api/users/line/{line_user_id}` |
| 成功回應 | `200 { name, phone, email }` |
| 找不到 | `404 { detail: "user not found" }` |
| 用途 | LIFF 啟動時判斷 LINE 用戶是否已完成會員註冊 |

**修改檔案：**
- `app/schemas/user.py` — 新增 `UserProfileResponse(name, phone, email)`
- `app/routers/users.py` — 新增 `get_user_by_line_id` endpoint

### 2. 前端畫面 1 — 使用者首頁（線上預約）

- 頂部導覽列：左側顯示分頁名稱「線上預約」，右側「會員專區」按鈕
- 店家資訊卡（MOCK）：形象圖佔位、店名、說明、營業時間、地址
- 底部「開始預約」按鈕（MOCK，點擊顯示「敬請期待」toast）

### 3. 前端畫面 2 — 會員專區

- 頂部導覽列：左側「前往預約」按鈕，右側顯示分頁名稱「會員專區」
- 會員資料卡：顯示姓名、手機（格式化為 09xxxxxxxx）、Email
- 底部「我的預約」按鈕（MOCK，點擊顯示「敬請期待」toast）

### 4. 流程調整

```
LIFF 開啟
  └─ POST /api/auth/line/verify → 取得 line_user_id
       └─ GET /api/users/line/{id}
            ├─ 200（已存在）→ 直接進使用者首頁
            └─ 404（新用戶）→ OTP 流程 → 完成後進使用者首頁
```

**舊流程（Phase 1）：** 完成 OTP 後顯示「註冊成功」畫面並關閉 LIFF 視窗。
**新流程（Phase 2）：** 完成 OTP 後直接進入使用者首頁，不關閉視窗。

---

## 修改檔案摘要

| 檔案 | 變動 |
|------|------|
| `app/schemas/user.py` | 新增 `UserProfileResponse` schema |
| `app/routers/users.py` | 新增 `GET /line/{line_user_id}` endpoint |
| `templates/user/index.html` | 新增 step-home、step-member section；新增 toast；header 加 id；版本號升 0.2.0 |
| `static/user/style.css` | 新增 app-nav、store-card、member-card、toast 樣式 |
| `static/user/app.js` | 完整改寫：新增 checkExistingUser、populateMember、showComingSoon；更新 showStep、initLiff、handleRegister；新增 event wiring |

---

## 版本號

靜態檔案版本：`?v=0.1.2` → `?v=0.2.0`

---

## 測試驗證

### 後端（pytest）
```
pytest tests/  # 確認原有 51 tests 全通過
```

### 手動驗證清單

| 情境 | 預期結果 |
|------|---------|
| 已存在 LINE user 開啟 LIFF | 直接進「線上預約」首頁 |
| 點擊「會員專區」 | 切換到會員專區，顯示姓名/手機/Email |
| 點擊「前往預約」 | 返回使用者首頁 |
| 點擊「開始預約」 | 顯示「敬請期待」toast 2.2 秒後消失 |
| 點擊「我的預約」 | 顯示「敬請期待」toast 2.2 秒後消失 |
| 新 LINE user 開啟 LIFF | 進入 OTP 流程（現有邏輯不變） |
| 新用戶完成 OTP 註冊 | 自動進入使用者首頁（不關閉視窗） |
| `/admin` 管理者頁面 | 功能不受影響 |

---

## 後續工作（本 Phase 不含）

- 預約系統實作（目前為 MOCK）
- 店家資料動態化（目前為靜態 MOCK 內容）
- 會員資料編輯功能
- 我的預約記錄查詢

# Phase 4 工作說明書

**專案**：HC MVP — LIFF 會員系統  
**Phase**：4 — 管理者後台  
**完成日期**：2025-05-11  
**分支**：`develop`  
**Commit**：`7246280`

---

## 完成項目

| # | 項目 | 檔案 |
|---|------|------|
| 1 | Admin schemas（登入/使用者清單） | `app/schemas/admin.py` |
| 2 | Admin 路由（login / logout / users） | `app/routers/admin.py` |
| 3 | 路由注冊 + GET /admin 頁面路由 | `app/main.py` |
| 4 | Admin 後台 HTML template | `templates/admin/index.html` |
| 5 | Admin CSS（藍色主題，RWD） | `static/admin/style.css` |
| 6 | Admin JS（登入、自動探針、搜尋、分頁） | `static/admin/app.js` |
| 7 | Admin 完整測試（15 個） | `tests/test_admin.py` |

---

## API 說明

| Method | Path | Auth | 說明 |
|--------|------|------|------|
| `POST` | `/api/admin/login` | 無 | 帳密驗證，寫入 Session |
| `POST` | `/api/admin/logout` | Session | 清除 Session |
| `GET`  | `/api/admin/users?page=1&size=50` | Session | 分頁使用者清單，最新先 |
| `GET`  | `/admin` | 無 | 管理後台 HTML 頁 |

---

## 關鍵技術決定

### `secrets.compare_digest` 常數時間比對
一般字串比對（`==`）在不匹配時提前返回，可能被計時攻擊推斷出正確帳密前幾個字元。`secrets.compare_digest` 保證比對時間固定，防止 timing-based username enumeration。

### 客戶端搜尋 + 一次載入
MVP 會員量有限（<10,000），前端一次從 API 批次載入全部資料（每次最多 200 筆，循環至載完），搜尋與分頁在 JS 端處理。優點：回應快、無需額外後端搜尋 API。後續量大時可改為 server-side 搜尋。

### Session 保護
所有需要認證的 admin 路由皆以 `Depends(require_admin_session)` 確保。`require_admin_session` 在 `app/dependencies.py` 中定義（Phase 1 已建立）。

---

## 測試結果

```
51 passed in 8.57s

tests/test_admin.py  (15)  登入/登出/session/listing/pagination/頁面
tests/test_auth.py   (9)   (Phase 3，持續通過)
tests/test_users.py  (8)   (Phase 3，持續通過)
tests/test_otp.py    (18)  (Phase 2，持續通過)
tests/test_health.py (1)   (Phase 1，持續通過)
```

---

## 前端頁面

| URL | 畫面 |
|-----|------|
| `GET /admin` | 登入卡片 → 後台主畫面（Session 存在時自動跳過登入） |

後台主畫面功能：
- 顯示「共 N 人」總數徽章
- 即時搜尋（姓名 / 手機 / Email，250ms debounce）
- 表格：#、姓名、手機、Email、LINE User ID、註冊日期
- 分頁（上一頁 / 頁碼 / 下一頁）
- 登出按鈕

---

## 下一步（Phase 5）

- Nginx config（reverse proxy → uvicorn，HTTPS 已就緒）
- systemd service 檔案（自動重啟）
- 部署腳本（`deploy.sh`）
- 端對端冒煙測試（實機 LIFF 流程驗證）

# Phase 5 工作說明書

**專案**：HC MVP — LIFF 會員系統  
**Phase**：5 — Ubuntu 24.04 部署  
**完成日期**：2025-05-12  
**分支**：`develop`

---

## 完成項目

| # | 檔案 | 說明 |
|---|------|------|
| 1 | `deploy/nginx.conf` | Nginx reverse proxy + static 直接服務 + HTTPS + Security headers |
| 2 | `deploy/hc-mvp.service` | systemd unit（非 root 執行、自動重啟、安全性強化） |
| 3 | `deploy.sh` | 持續部署腳本（pull → test → migrate → reload） |
| 4 | `deploy/install.sh` | 首次安裝引導（8 步驟，互動式）|
| 5 | `deploy/logrotate.conf` | Nginx log 每日輪替（保留 14 天） |

---

## 伺服器架構

```
Internet (HTTPS:443)
        │
   ┌────▼──────────────────────────────┐
   │  Nginx (Reverse Proxy + SSL)      │
   │  /static/  → 直接服務靜態檔案      │
   │  /         → proxy_pass :8000    │
   └────────────────┬──────────────────┘
                    │ 127.0.0.1:8000
   ┌────────────────▼──────────────────┐
   │  uvicorn（workers=2）              │
   │  FastAPI app（user: hcmvp）        │
   └────────────────┬──────────────────┘
                    │
   ┌────────────────▼──────────────────┐
   │  SQLite /opt/hc_mvp/hc_mvp.db    │
   └───────────────────────────────────┘
```

---

## 首次部署步驟（在 Ubuntu 24.04 伺服器上執行）

```bash
# 1. 取得程式碼（或以 scp 上傳）
git clone https://github.com/your-org/hc-mvp.git /opt/hc_mvp
cd /opt/hc_mvp

# 2. 執行首次安裝腳本（互動式，8 步驟）
sudo bash deploy/install.sh

# 腳本會：
#   ① 安裝系統套件（git nginx python3 certbot sqlite3）
#   ② 建立系統使用者 hcmvp
#   ③ 設定虛擬環境並安裝 Python 依賴
#   ④ 引導填入 .env（交互暫停）
#   ⑤ 執行 alembic upgrade head
#   ⑥ 啟動並 enable systemd service
#   ⑦ 設定 Nginx + logrotate
```

---

## 日後更新（持續部署）

```bash
# 在伺服器 /opt/hc_mvp 目錄下執行：
./deploy.sh

# 腳本流程：
#  git pull origin main
#  pip install（更新依賴）
#  pytest（若失敗則中止）
#  alembic upgrade head
#  systemctl reload-or-restart hc-mvp
#  curl health check
```

---

## 常用維運指令

```bash
# 查看即時 log
journalctl -u hc-mvp -f

# 查看最近 50 行 log
journalctl -u hc-mvp -n 50

# 手動重啟
sudo systemctl restart hc-mvp

# 檢查服務狀態
sudo systemctl status hc-mvp

# Nginx 重新載入（修改 conf 後）
sudo nginx -t && sudo systemctl reload nginx

# 手動備份 DB
cp /opt/hc_mvp/hc_mvp.db /opt/hc_mvp/hc_mvp.db.backup.$(date +%Y%m%d)

# 切換至 PostgreSQL（未來擴充）
#   1. 安裝 psycopg2-binary
#   2. 修改 .env: DATABASE_URL=postgresql+psycopg2://...
#   3. alembic upgrade head
#   4. systemctl restart hc-mvp
```

---

## .env 設定一覽（production）

```ini
APP_ENV=production
SECRET_KEY=<32 位以上隨機字串，可用 openssl rand -hex 32 產生>

DATABASE_URL=sqlite:////opt/hc_mvp/hc_mvp.db

LINE_CHANNEL_ACCESS_TOKEN=<LINE Developer Console>
LINE_CHANNEL_SECRET=<LINE Developer Console>
LIFF_ID=<LINE Developer Console LIFF ID>

TWILIO_ACCOUNT_SID=<Twilio Console>
TWILIO_AUTH_TOKEN=<Twilio Console>
TWILIO_FROM_NUMBER=+886xxxxxxxxx

ADMIN_USERNAME=<自訂帳號>
ADMIN_PASSWORD=<強密碼>

OTP_EXPIRE_MINUTES=10
OTP_DAILY_LIMIT=3
```

---

## 冒煙測試清單（部署後手動驗證）

| # | 測試項目 | 預期結果 |
|---|---------|---------|
| 1 | `curl https://ai.rh888.tw/health` | `{"status":"ok"}` |
| 2 | 瀏覽器開啟 `https://ai.rh888.tw/` | LIFF 頁面載入，spinner 出現 |
| 3 | 在 LINE App 中開啟 LIFF 連結 | LINE 授權 → 手機輸入畫面 |
| 4 | 輸入 09xxxxxxxx → 發送驗證碼 | SMS 收到 6 位數字 |
| 5 | 輸入驗證碼 → 填寫姓名/Email | 顯示「註冊成功」畫面 |
| 6 | 瀏覽器開啟 `https://ai.rh888.tw/admin` | 顯示管理後台登入畫面 |
| 7 | 以 .env 帳密登入 | 顯示使用者清單，可見剛才的測試會員 |
| 8 | 重新整理後台（session 保留） | 不需重新登入，直接進入清單 |
| 9 | 點擊登出 | 回到登入畫面，session 清除 |

---

## 測試結果（Phase 5 無新增測試）

```
51 passed（全部前期 Phase 測試持續通過）
```

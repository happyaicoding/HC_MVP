#!/usr/bin/env bash
# ============================================================
# HC MVP — 首次伺服器安裝腳本（Ubuntu 24.04）
#
# 執行前提：
#   - 以具 sudo 權限的帳號執行
#   - 已設定 DNS：ai.rh888.tw → 本機 IP
#   - HTTPS 憑證已存在（/etc/letsencrypt/live/ai.rh888.tw/）
#
# 使用方式（一次性）：
#   chmod +x install.sh
#   sudo bash install.sh
# ============================================================
set -euo pipefail

APP_USER="hcmvp"
APP_DIR="/opt/hc_mvp"
REPO_URL="https://github.com/happyaicoding/HC_mvp.git"
BRANCH="main"
PYTHON_MIN="3.11"

log()  { echo "▶ $*"; }
die()  { echo "[ERROR] $*" >&2; exit 1; }
step() { echo ""; echo "══════════════════════════════════════"; echo "  STEP $*"; echo "══════════════════════════════════════"; }

# ── Step 1: 系統套件 ────────────────────────────────────────
step "1/8  系統套件更新與安裝"
apt-get update -qq
apt-get install -y -qq \
  git curl nginx python3 python3-pip python3-venv \
  certbot python3-certbot-nginx \
  sqlite3

# 確認 Python 版本
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log "Python version: ${PYTHON_VER}"
python3 -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'" \
  || die "Python ${PYTHON_MIN}+ is required. Install python3.11 or higher."

# ── Step 2: 建立系統使用者 ─────────────────────────────────
step "2/8  建立應用程式使用者 ${APP_USER}"
if ! id "${APP_USER}" &>/dev/null; then
  useradd --system --shell /usr/sbin/nologin --home "${APP_DIR}" "${APP_USER}"
  log "User ${APP_USER} created"
else
  log "User ${APP_USER} already exists"
fi

# ── Step 3: Clone 程式碼 ────────────────────────────────────
step "3/8  Clone repository"
if [[ -d "${APP_DIR}/.git" ]]; then
  log "Repository already cloned, pulling latest..."
  git -C "${APP_DIR}" pull origin "${BRANCH}"
else
  git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

# ── Step 4: 建立虛擬環境並安裝依賴 ─────────────────────────
step "4/8  Python 虛擬環境"
if [[ ! -d "${APP_DIR}/.venv" ]]; then
  python3 -m venv "${APP_DIR}/.venv"
fi
"${APP_DIR}/.venv/bin/pip" install -q --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -q -e "${APP_DIR}[dev]"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}/.venv"

# ── Step 5: 環境變數 .env ────────────────────────────────────
step "5/8  環境變數設定"
if [[ ! -f "${APP_DIR}/.env" ]]; then
  cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
  chmod 600 "${APP_DIR}/.env"
  chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
  log ""
  log "⚠️  請編輯 ${APP_DIR}/.env 填入實際設定值："
  log "     sudo nano ${APP_DIR}/.env"
  log ""
  log "   必填項目："
  log "     APP_ENV=production"
  log "     SECRET_KEY=<32 位以上隨機字串>"
  log "     LINE_CHANNEL_ACCESS_TOKEN=<token>"
  log "     LINE_CHANNEL_SECRET=<secret>"
  log "     LIFF_ID=<liff-id>"
  log "     TWILIO_ACCOUNT_SID=<sid>"
  log "     TWILIO_AUTH_TOKEN=<token>"
  log "     TWILIO_FROM_NUMBER=<+886xxxxxxxxx>"
  log "     ADMIN_USERNAME=<帳號>"
  log "     ADMIN_PASSWORD=<密碼>"
  log ""
  read -r -p "   設定完成後按 Enter 繼續..." _
else
  log ".env already exists, skipping"
fi

# ── Step 6: DB migration ─────────────────────────────────────
step "6/8  資料庫 migration"
cd "${APP_DIR}"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/alembic" upgrade head
log "Migrations applied"

# ── Step 7: systemd service ──────────────────────────────────
step "7/8  systemd 服務"
cp "${APP_DIR}/deploy/hc-mvp.service" /etc/systemd/system/hc-mvp.service
systemctl daemon-reload
systemctl enable hc-mvp
systemctl start  hc-mvp
sleep 2
systemctl is-active --quiet hc-mvp \
  && log "Service hc-mvp is running ✅" \
  || die "Service failed to start. Check: journalctl -u hc-mvp -n 50"

# ── Step 8: Nginx ────────────────────────────────────────────
step "8/8  Nginx 設定"
cp "${APP_DIR}/deploy/nginx.conf" /etc/nginx/sites-available/hc-mvp

# 確保不會與 default 衝突
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  rm -f /etc/nginx/sites-enabled/default
  log "Removed default site"
fi

ln -sf /etc/nginx/sites-available/hc-mvp /etc/nginx/sites-enabled/hc-mvp

# Logrotate
cp "${APP_DIR}/deploy/logrotate.conf" /etc/logrotate.d/hc-mvp

nginx -t && systemctl reload nginx
log "Nginx configured and reloaded ✅"

# ── 完成 ────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅  HC MVP 安裝完成                                   ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  使用者 LIFF  https://ai.rh888.tw/                    ║"
echo "║  管理後台      https://ai.rh888.tw/admin              ║"
echo "║  健康檢查      https://ai.rh888.tw/health             ║"
echo "║  API 文件      https://ai.rh888.tw/docs  (dev only)   ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  日後更新      ./deploy.sh                            ║"
echo "║  查看 log      journalctl -u hc-mvp -f               ║"
echo "╚══════════════════════════════════════════════════════╝"

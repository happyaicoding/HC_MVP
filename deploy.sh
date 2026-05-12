#!/usr/bin/env bash
# ============================================================
# HC MVP — 持續部署腳本
# 用途：每次 push 後在伺服器上執行以更新程式
#
# 使用方式：
#   chmod +x deploy.sh
#   ./deploy.sh           # 正常部署
#   ./deploy.sh --skip-tests   # 跳過測試（緊急熱修復用）
# ============================================================
set -euo pipefail

APP_DIR="/opt/hc_mvp"
VENV="${APP_DIR}/.venv"
SERVICE="hc-mvp"
BRANCH="main"

SKIP_TESTS=false
for arg in "$@"; do
  [[ "$arg" == "--skip-tests" ]] && SKIP_TESTS=true
done

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

# ── 1. 確認在正確目錄 ──────────────────────────────────────
cd "${APP_DIR}" || die "Cannot cd to ${APP_DIR}"

log "🔍 Current branch: $(git rev-parse --abbrev-ref HEAD)"
log "📦 Pulling latest code from ${BRANCH}..."

# ── 2. Pull 最新程式碼 ─────────────────────────────────────
git fetch origin
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

COMMIT=$(git rev-parse --short HEAD)
log "✅ Code updated to commit ${COMMIT}"

# ── 3. 安裝/更新 Python 依賴 ────────────────────────────────
log "📥 Installing dependencies..."
"${VENV}/bin/pip" install -q --upgrade pip
"${VENV}/bin/pip" install -q -e ".[dev]"

# ── 4. 執行測試（可跳過）──────────────────────────────────
if [[ "${SKIP_TESTS}" == "false" ]]; then
  log "🧪 Running tests..."
  "${VENV}/bin/pytest" tests/ --no-cov -q \
    || die "Tests failed — deployment aborted. Fix tests before deploying."
  log "✅ All tests passed"
else
  log "⚠️  Tests skipped (--skip-tests flag)"
fi

# ── 5. 執行 DB migration ───────────────────────────────────
log "🗄️  Running Alembic migrations..."
"${VENV}/bin/alembic" upgrade head
log "✅ Migrations applied"

# ── 6. 重啟服務（zero-downtime reload） ────────────────────
log "🔄 Reloading service ${SERVICE}..."
sudo systemctl reload-or-restart "${SERVICE}"

# 等待服務穩定
sleep 2
if systemctl is-active --quiet "${SERVICE}"; then
  log "✅ Service ${SERVICE} is running"
else
  die "Service ${SERVICE} failed to start. Check: journalctl -u ${SERVICE} -n 50"
fi

# ── 7. 健康檢查 ────────────────────────────────────────────
log "🏥 Health check..."
HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health || echo "000")
if [[ "${HTTP_STATUS}" == "200" ]]; then
  log "✅ Health check passed (HTTP 200)"
else
  die "Health check failed (HTTP ${HTTP_STATUS}). Rolling back requires manual intervention."
fi

log ""
log "🎉 Deployment complete — commit ${COMMIT} is live at https://ai.rh888.tw"

# Phase 1 工作說明書

**專案**：HC MVP — LIFF 會員系統  
**Phase**：1 — 專案骨架與資料庫  
**完成日期**：2025-05-11  
**分支**：`develop`  
**Commit**：`1af2029`

---

## 完成項目

| # | 項目 | 檔案 |
|---|------|------|
| 1 | Git repo 初始化，建立 `main` / `develop` 分支 | `.git/` |
| 2 | 依賴與工具設定 | `pyproject.toml` |
| 3 | 環境變數範本 | `.env.example` |
| 4 | Git 排除清單 | `.gitignore` |
| 5 | 應用程式設定（pydantic-settings） | `app/config.py` |
| 6 | SQLAlchemy engine（SQLite/PostgreSQL 可切換） | `app/database.py` |
| 7 | ORM Model：User | `app/models/user.py` |
| 8 | ORM Model：OtpRecord | `app/models/otp_record.py` |
| 9 | FastAPI app 入口（SessionMiddleware、CORS、health endpoint） | `app/main.py` |
| 10 | 共用依賴（require_admin_session） | `app/dependencies.py` |
| 11 | Alembic 環境設定 | `alembic/env.py`, `alembic.ini` |
| 12 | Init migration（users + otp_records） | `alembic/versions/0001_init_users_and_otp_records.py` |
| 13 | 測試 fixture（in-memory SQLite） | `tests/conftest.py` |
| 14 | Smoke test：health endpoint | `tests/test_health.py` |

---

## 技術決定說明

### SQLite → PostgreSQL 切換機制
- `DATABASE_URL` 由 `.env` 讀取，`app/database.py` 根據 URL scheme 自動調整 `connect_args`
- SQLite 啟用 WAL 模式與 Foreign Keys pragma
- Alembic `env.py` 於執行時讀取 `DATABASE_URL`，遷移腳本無需修改
- **切換步驟**：更新 `.env` 的 `DATABASE_URL` → 執行 `alembic upgrade head`

### Session 機制
- 使用 Starlette `SessionMiddleware`（itsdangerous 簽名 cookie）
- `SECRET_KEY` 從 `.env` 讀取，production 時 `https_only=True`

### OtpRecord.code_hash
- 儲存 OTP 的 bcrypt hash 而非明文，Phase 2 實作 `otp_service.py` 時使用

---

## 本機執行方式

```bash
# 1. 複製環境變數
cp .env.example .env
# 編輯 .env 填入實際值

# 2. 建立虛擬環境並安裝依賴
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"

# 3. 執行 DB migration
alembic upgrade head

# 4. 啟動開發伺服器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 執行測試
pytest
```

---

## 測試結果

```
1 passed in 0.06s
tests/test_health.py::test_health_check PASSED
```

---

## 下一步（Phase 2）

- `app/services/otp_service.py`：OTP 生成、bcrypt hash、驗證、每日次數限制
- `app/services/twilio_service.py`：Twilio SMS 發送
- `app/routers/otp.py`：`POST /api/otp/send`、`POST /api/otp/verify`
- `tests/test_otp.py`：OTP 完整 unit test

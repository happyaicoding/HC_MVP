# Phase 2 工作說明書

**專案**：HC MVP — LIFF 會員系統  
**Phase**：2 — OTP 核心邏輯與 Twilio SMS  
**完成日期**：2025-05-11  
**分支**：`develop`  
**Commit**：`6fbdead`

---

## 完成項目

| # | 項目 | 檔案 |
|---|------|------|
| 1 | OTP 業務邏輯（生成、hash、驗證、次數限制、verify token） | `app/services/otp_service.py` |
| 2 | Twilio SMS 發送服務（含 try-except、TwilioError） | `app/services/twilio_service.py` |
| 3 | Pydantic schemas（OtpSendRequest、OtpVerifyRequest/Response） | `app/schemas/otp.py` |
| 4 | OTP 路由（POST /api/otp/send、/api/otp/verify） | `app/routers/otp.py` |
| 5 | 路由注冊到 FastAPI app | `app/main.py` |
| 6 | 全套 unit tests（18 個測試案例） | `tests/test_otp.py` |
| 7 | 測試基礎設施修正（StaticPool、models import） | `tests/conftest.py` |

---

## 關鍵技術決定

### bcrypt 直接呼叫（取代 passlib）
`passlib` 的 bcrypt 後端在 `bcrypt>=4.0` 下執行 `detect_wrap_bug` 自我測試時，會傳入超過 72 bytes 的測試密碼，導致 `ValueError`。解決方式：改為直接呼叫 `bcrypt.hashpw` / `bcrypt.checkpw`，移除 `passlib` 依賴。

### OTP 每日限制計算（Taipei 時區）
`count_today_sends` 以台北時間（UTC+8）當日日期計算次數，使用 SQLite `strftime('%Y-%m-%d', created_at)` 對應台北日期字串。切換至 PostgreSQL 時，應改用 `CAST(created_at AT TIME ZONE 'Asia/Taipei' AS DATE)` 以確保準確性。

### Verify Token
OTP 驗證成功後，用 `itsdangerous.URLSafeTimedSerializer` 簽發一個包含 `{"phone": ...}` 的短效 token（有效期同 OTP，10 分鐘），傳給 Phase 3 的 `/api/users/register` 使用，避免在前端暴露原始 OTP 碼。

### StaticPool（測試環境）
SQLite `:memory:` 每個連線獨立，多個 session 會看到不同的空資料庫。加入 `poolclass=StaticPool` 後，所有 session 共用同一個實體連線，確保 `create_all` 建立的表格對所有測試請求可見。

---

## 測試結果

```
19 passed in 9.48s

tests/test_health.py::test_health_check                  PASSED
tests/test_otp.py::test_create_otp_returns_six_digits    PASSED
tests/test_otp.py::test_create_otp_stored_as_hash        PASSED
tests/test_otp.py::test_create_otp_sets_expiry           PASSED
tests/test_otp.py::test_verify_otp_success               PASSED
tests/test_otp.py::test_verify_otp_marks_used            PASSED
tests/test_otp.py::test_verify_otp_wrong_code_raises     PASSED
tests/test_otp.py::test_verify_otp_expired_raises        PASSED
tests/test_otp.py::test_verify_otp_used_code_raises      PASSED
tests/test_otp.py::test_resend_supersedes_old_otp        PASSED
tests/test_otp.py::test_daily_limit_raises               PASSED
tests/test_otp.py::test_verify_token_roundtrip           PASSED
tests/test_otp.py::test_verify_token_invalid_raises      PASSED
tests/test_otp.py::test_send_otp_endpoint_200            PASSED
tests/test_otp.py::test_send_otp_invalid_phone_422       PASSED
tests/test_otp.py::test_send_otp_daily_limit_429         PASSED
tests/test_otp.py::test_send_otp_twilio_failure_503      PASSED
tests/test_otp.py::test_verify_otp_endpoint_200          PASSED
tests/test_otp.py::test_verify_otp_wrong_code_400        PASSED
```

---

## 下一步（Phase 3）

- `app/services/line_service.py`：呼叫 LINE `/oauth2/v2.1/verify` 驗證 LIFF access token
- `app/routers/auth.py`：`POST /api/auth/line/verify`
- `app/routers/users.py`：`POST /api/users/register`（含覆寫 line_user_id 邏輯）
- `static/user/`：LIFF 前端（HTML/CSS/JS，RWD）
- `tests/test_auth.py`, `tests/test_users.py`：對應 unit tests

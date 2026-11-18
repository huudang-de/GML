# Thiết kế: Đăng nhập, CSDL người dùng nội bộ, Trang quản trị & Phân quyền theo tài khoản

- **Ngày:** 18/11/2026
- **Phạm vi:** `7. AI-Business-Assistant/v2` (FastAPI + Streamlit + PostgreSQL)
- **Trạng thái:** Đã duyệt (18/11/2026) — đã chốt toàn bộ 5 quyết định kiến trúc, sẵn sàng cho bước lập kế hoạch & triển khai.

---

## 1. Vì sao cần làm

Hiện nay **ai mở web cũng tự chọn được vai trò** trong ô "👤 Vai trò người dùng" ở thanh bên (`ROLE_TOKENS` trong `streamlit_app.py`), và URL `?role=ceo` cũng đổi được vai trò. Đằng sau, giao diện gửi một trong 4 token cố định (`gml-dev-token-ceo`, `-ktt`, `-kho`, `-admin`) được viết cứng trong `app/core/auth.py`. Nghĩa là:

- Nhân viên kho có thể chọn "CEO" và xem toàn bộ nợ vay, dòng tiền.
- Nhật ký `app.audit_log` ghi `usr_ceo`, nhưng không biết **người thật** nào đã thao tác.
- Không có cách thêm người mới, khoá người nghỉ việc, hay đổi vai trò mà không sửa code.

Mục tiêu: **quyền được xác định bởi tài khoản đăng nhập**, không phải do người dùng tự chọn. Lớp phân quyền dữ liệu hiện có (vai trò → view → KPI trong `db/catalog.yaml`, `can_access_kpi`) giữ nguyên; thứ thay đổi là *vai trò lấy từ đâu*.

## 2. Mục tiêu / Ngoài phạm vi / Điều tuyệt đối tránh

**Mục tiêu**
1. Trang đăng nhập (tên đăng nhập + mật khẩu) trước khi vào bất kỳ màn hình nào.
2. CSDL người dùng nội bộ trong PostgreSQL: tài khoản, mật khẩu đã băm, vai trò, nguồn dữ liệu được phép, trạng thái.
3. Trang quản trị cho vai trò `quan_tri_he_thong`: tạo/sửa/khoá tài khoản, đặt lại mật khẩu, thu hồi phiên, xem nhật ký đăng nhập.
4. Mọi API (`/v1/*`) xác thực bằng phiên đăng nhập thật; vai trò và nguồn dữ liệu (`real`/`synth`) được kiểm tra phía server.
5. Nhật ký truy cập ghi đúng người thật.

**Ngoài phạm vi (lần này)**
- Đăng nhập một lần qua Microsoft 365 / Google (SSO/OIDC) — để ngỏ cho giai đoạn sau (xem Phương án C).
- Xác thực 2 lớp (OTP), quên mật khẩu qua email, tự đăng ký tài khoản.
- Trình chỉnh quyền chi tiết theo từng KPI cho từng người. **Vai trò vẫn là đơn vị phân quyền**; mỗi tài khoản được gán đúng 1 vai trò.

**Điều tuyệt đối tránh (dù chạy được cũng coi là hỏng)**
- Vẫn còn bất kỳ đường nào để người dùng tự nâng vai trò (ô chọn vai trò, `?role=` trên URL, token cố định chạy ở môi trường production).
- Lưu mật khẩu hoặc token dạng thô trong CSDL hay log.
- Khoá tài khoản xong mà người đó vẫn dùng tiếp được phiên cũ.
- Làm vỡ các kiểm thử hiện có (278 test) hoặc hợp đồng API `Authorization: Bearer <token>`.

## 3. Ràng buộc từ hệ thống hiện tại

- Toàn bộ API đã dùng `Authorization: Bearer <token>` → `get_current_user` → `TokenAuthVerifier.verify_bearer_token` → `UserPrincipal(user_id, role, display_name)`. Thiết kế giữ nguyên hợp đồng này để không phải sửa từng router.
- Có **2 CSDL** theo nguồn dữ liệu (`real` = `data_warehouse`, `synth` = `gml_synth`), mỗi CSDL có schema `app` riêng. Danh tính người dùng phải là **một nguồn duy nhất**, không nhân đôi theo nguồn dữ liệu.
- Các bảng hiện có lưu `user_id VARCHAR(100)` (`chat_turn`, `audit_log`, `feedback`, `action_item.created_by`, `pinned_kpi`, `alert_event.acknowledged_by`). Mã người dùng mới phải giữ được kiểu này và lịch sử cũ của `usr_ceo`, `usr_ktt`, `usr_kho`, `usr_admin`.
- Thư viện đã có sẵn: `argon2-cffi 25.1.0`, `bcrypt 5.0.0`, `PyJWT 2.14.0`, Streamlit `1.55.0` (có `st.context.cookies` chỉ đọc và `st.login` cho OIDC).
- Ranh giới kiến trúc: `app/ui/**` không được import `app.services`, `app.agents`, `app.knowledge`, `db` — giao diện chỉ gọi API qua `HttpApiClient`.
- Vai trò `quan_tri_he_thong` hiện không xem được view dữ liệu nào (`get_allowed_views` trả rỗng).

## 4. Các phương án đã cân nhắc

| | **A. Tài khoản nội bộ + phiên lưu trong PostgreSQL** *(đề xuất)* | B. Tài khoản nội bộ + JWT không trạng thái | C. SSO qua Microsoft Entra ID / Google (OIDC) |
|---|---|---|---|
| Cách làm | Đăng nhập trả về token ngẫu nhiên; server chỉ lưu mã băm SHA-256 của token trong bảng phiên | Đăng nhập trả về JWT ký bằng khoá bí mật; server không lưu phiên | Chuyển hướng sang trang đăng nhập Microsoft/Google; Streamlit có sẵn `st.login` |
| Khoá tài khoản / thu hồi phiên | Có hiệu lực ngay ở request tiếp theo | Phải chờ JWT hết hạn, hoặc làm thêm danh sách đen (lại thành có trạng thái) | Phụ thuộc cấu hình bên IdP |
| Thay đổi so với hiện tại | Nhỏ: `TokenAuthVerifier` đã băm token SHA-256 và so sánh hằng thời gian, chỉ cần thêm tra cứu bảng phiên | Vừa: thêm quản lý khoá ký, xoay khoá | Lớn: cần tenant, đăng ký ứng dụng, HTTPS, URL callback |
| Phù hợp quy mô | Vài chục người dùng nội bộ — rất phù hợp | Phù hợp hệ thống nhiều máy chủ, lưu lượng lớn | Phù hợp khi công ty đã dùng Microsoft 365/Google Workspace tập trung |

**Đề xuất: Phương án A.** Lý do: giữ nguyên hợp đồng Bearer nên mọi router và kiểm thử hiện có chạy tiếp; khoá người nghỉ việc có hiệu lực tức thì (đúng nhu cầu kiểm soát truy cập tài chính); mỗi request thêm một truy vấn theo chỉ mục là không đáng kể với quy mô vài chục người. Phương án C để dành giai đoạn sau: bảng người dùng của A vẫn dùng lại được (thêm cột `external_subject`), chỉ thay bước xác minh mật khẩu.

### 4.1. Đối chiếu với các hệ thống BI & chuẩn bảo mật uy tín

Bản thiết kế này tổng hợp từ cấu trúc hiện có của `v2` kết hợp với các mẫu kiến trúc thực tế từ 5 nguồn tham chiếu chuẩn ngành:

| Nguồn tham chiếu | Mẫu chuẩn được áp dụng vào thiết kế |
|---|---|
| **Metabase** (*Session Management UI & People Directory*) | Bảng quản lý phiên hoạt động hiển thị IP, trình duyệt (`user_agent`), thời điểm hoạt động gần nhất (`last_seen_at`), thu hồi tức thì từng phiên/từng người dùng và ghi rõ lý do thu hồi (`revoked_reason`: `user_logout`, `admin_revoked`, `password_changed`, `role_changed`, `account_disabled`, `idle_timeout`). |
| **Apache Superset** (*Flask-AppBuilder RBAC & `DASHBOARD_RBAC`*) | Tách biệt rõ *Capability Role* (`quan_tri_he_thong` quản trị hệ thống) khỏi *Data-Domain Roles* (`ceo`, `ke_toan_truong`, `quan_ly_kho` gắn với view dữ liệu trong `db/catalog.yaml`), tránh anti-pattern mọi tài khoản đều xem được số liệu mặc định. |
| **Grafana** (*Users vs Service Accounts & Reference Tokens*) | Tách biệt phiên người dùng tương tác (lưu trong `iam.user_session` có hạn tuyệt đối + hạn nhàn rỗi) khỏi token máy/tích hợp (`auth_tokens_json` cho service account như Power BI), đảm bảo thu hồi tài khoản có hiệu lực ở request kế tiếp. |
| **OWASP** (*Authentication, Session Management & Password Storage Cheat Sheets*) | Lưu mật khẩu bằng `Argon2id` (memory-hard, tự động `check_needs_rehash`); token phiên ngẫu nhiên $\ge 256$-bit entropy chỉ lưu mã băm `SHA-256` kèm so sánh hằng thời gian (`hmac.compare_digest`); chống dò tên đăng nhập qua kênh thời gian bằng cách luôn chạy băm giả `Argon2id` khi `username` không tồn tại. |
| **NIST SP 800-63B** (*Digital Identity Guidelines*) | Chính sách mật khẩu ưu tiên độ dài ($\ge 10$ đến $128$ ký tự UTF-8, cho phép khoảng trắng) kết hợp danh sách từ cấm ngữ cảnh/phổ biến (`minhlong`, `gominhlong`, `password`, `1234567890`, trùng `username`/`email`) thay vì ép ký tự đặc biệt máy móc; khoá tạm thời 15 phút (chống DoS khoá vĩnh viễn) + giới hạn tần suất theo IP. |

## 5. Thiết kế chi tiết

### 5.1. Vai trò và quyền (không đổi về bản chất)

| Vai trò | Nhãn hiển thị | Dữ liệu được xem | Màn hình |
|---|---|---|---|
| `ceo` | Tổng Giám đốc | Toàn bộ 7 view | Tổng quan (có tab "Tổng hợp điều hành"), Cảnh báo, Hỏi đáp AI, Hành động, Lịch sử |
| `ke_toan_truong` | Kế toán trưởng | 6 view tài chính | Như trên, không có tab "Tổng hợp điều hành" |
| `quan_ly_kho` | Quản lý kho | 1 view tồn kho | Như trên, không có tab "Tổng hợp điều hành" |
| `quan_tri_he_thong` | Quản trị hệ thống | **Không xem dữ liệu tài chính** | Chỉ các màn quản trị (mục 5.6) |

**Tách bạch nhiệm vụ (đã chốt):** người quản trị (`quan_tri_he_thong`) quản lý người dùng, phiên đăng nhập, nhật ký và **kích hoạt chạy lại dữ liệu mô phỏng/dự báo cuối tháng**, nhưng bản thân **không** xem số liệu tài chính. Nếu người làm IT cần xem số liệu, họ dùng **tài khoản thứ hai** với vai trò nghiệp vụ. Cách này khớp với ma trận quyền hiện có (`quan_tri_he_thong` → 0 view).

**Quyền theo nguồn dữ liệu (đã chốt theo quy trình mô phỏng/dự báo cuối tháng):** nguồn `synth` chứa dữ liệu mô phỏng & kết quả chạy mô hình dự báo (ML/NM) cuối mỗi tháng. Mặc định **các vai trò nghiệp vụ** (`ceo`, `ke_toan_truong`, `quan_ly_kho`) được cấp `allowed_profiles = ['real', 'synth']` để **xem** cả số liệu thực tế và kết quả dự báo tháng (Admin có thể thu hẹp xuống `['real']` cho từng tài khoản nếu cần); **riêng quyền kích hoạt/chạy lại batch dữ liệu mô phỏng & dự báo cuối tháng (`POST /v1/admin/simulation/run`) chỉ dành cho `quan_tri_he_thong`**. Server từ chối (`403 PROFILE_FORBIDDEN`) nếu người dùng truy vấn nguồn không nằm trong `allowed_profiles`.

### 5.2. CSDL người dùng nội bộ

Đặt trong **schema mới `iam` của CSDL `real` (`data_warehouse`)** — một nguồn danh tính duy nhất, dùng chung bất kể người dùng đang xem nguồn `real` hay `synth`. Tạo bằng migration `db/migrations/003_iam_users_sessions.sql`, chạy qua `apply_db.py` như 001/002.

```sql
CREATE SCHEMA IF NOT EXISTS iam;

-- Tài khoản
CREATE TABLE iam.app_user (
    user_id              VARCHAR(100) PRIMARY KEY,          -- vd 'usr_ceo', 'u_7f3a9c21'
    username             VARCHAR(64)  NOT NULL,              -- lưu chữ thường
    display_name         VARCHAR(200) NOT NULL,
    email                VARCHAR(200),
    password_hash        TEXT         NOT NULL,              -- argon2id
    role                 VARCHAR(50)  NOT NULL CHECK (role IN ('ceo','ke_toan_truong','quan_ly_kho','quan_tri_he_thong')),
    allowed_profiles     TEXT[]       NOT NULL DEFAULT ARRAY['real', 'synth'],
    is_active            BOOLEAN      NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN      NOT NULL DEFAULT TRUE,
    failed_login_count   INT          NOT NULL DEFAULT 0,
    locked_until         TIMESTAMPTZ,
    last_login_at        TIMESTAMPTZ,
    password_changed_at  TIMESTAMPTZ,
    created_by           VARCHAR(100),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_app_user_username ON iam.app_user (lower(username));

-- Phiên đăng nhập (chỉ lưu mã băm token)
CREATE TABLE iam.user_session (
    id             BIGSERIAL PRIMARY KEY,
    token_hash     CHAR(64)     NOT NULL UNIQUE,             -- SHA-256 hex
    user_id        VARCHAR(100) NOT NULL REFERENCES iam.app_user(user_id),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at     TIMESTAMPTZ  NOT NULL,                    -- hạn tuyệt đối
    last_seen_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),      -- để tính hạn khi không hoạt động
    revoked_at     TIMESTAMPTZ,
    revoked_reason VARCHAR(50),                              -- 'user_logout' | 'admin_revoked' | 'role_changed' | ...
    revoked_by     VARCHAR(100),                             -- actor user_id nếu admin thu hồi
    client_ip      VARCHAR(64),
    user_agent     VARCHAR(300)
);
CREATE INDEX idx_user_session_user ON iam.user_session (user_id) WHERE revoked_at IS NULL;

-- Nhật ký sự kiện xác thực & quản trị
CREATE TABLE iam.auth_event (
    id                 BIGSERIAL PRIMARY KEY,
    event_type         VARCHAR(40)  NOT NULL,   -- xem danh sách bên dưới
    user_id            VARCHAR(100),            -- tài khoản bị tác động (NULL nếu đăng nhập sai tên)
    username_attempted VARCHAR(64),
    actor_user_id      VARCHAR(100),            -- ai thực hiện (admin), NULL nếu tự thao tác
    detail             JSONB,                   -- KHÔNG chứa mật khẩu/token
    client_ip          VARCHAR(64),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_auth_event_created ON iam.auth_event (created_at DESC);
CREATE INDEX idx_auth_event_user ON iam.auth_event (user_id);

GRANT USAGE ON SCHEMA iam TO gml_ai_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA iam TO gml_ai_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA iam TO gml_ai_app;
-- gml_ai_ro (vai trò truy vấn của AI) KHÔNG có quyền gì trên schema iam.
```

`event_type`: `login_success`, `login_failed`, `account_locked`, `logout`, `session_expired`, `password_changed`, `password_reset_by_admin`, `user_created`, `user_updated`, `role_changed`, `profiles_changed`, `user_disabled`, `user_enabled`, `sessions_revoked`, `simulation_triggered`.

**Giữ lịch sử cũ:** tài khoản ban đầu dùng lại đúng `user_id` hiện có (`usr_ceo`, `usr_ktt`, `usr_kho`, `usr_admin`) nên lịch sử hỏi đáp, ghim KPI, hành động cũ vẫn thuộc về họ. Tài khoản mới nhận `user_id` dạng `u_` + 8 ký tự hex ngẫu nhiên.

### 5.3. Luật bảo mật

| Hạng mục | Quy định (đề xuất theo OWASP / NIST 800-63B / Metabase) |
|---|---|
| Băm mật khẩu | `Argon2id` (`argon2-cffi`, tối thiểu 19 MiB RAM theo OWASP); tự động `check_needs_rehash` nâng cấp khi thông số thay đổi |
| Chống dò tài khoản theo thời gian | Nếu `username` không tồn tại vẫn chạy xác minh giả với chuỗi băm mẫu (`_DUMMY_PASSWORD_HASH`) để thời gian phản hồi đồng nhất |
| Độ mạnh mật khẩu (NIST 800-63B) | 10–128 ký tự UTF-8 (cho phép dấu cách), có ít nhất chữ và số; chặn trùng `username`/`email` và từ cấm (`minhlong`, `gominhlong`, `password`, `1234567890`, ...) |
| Token phiên | `secrets.token_urlsafe(32)` ($\ge 256$ bit entropy); CSDL chỉ lưu `SHA-256`, đối chiếu bằng `hmac.compare_digest` |
| Hạn phiên | Tuyệt đối 12 giờ (một ngày làm việc); tự hết hạn nếu không hoạt động 2 giờ |
| Khoá do đăng nhập sai | 5 lần sai liên tiếp → khoá tạm 15 phút (tránh tự khoá vĩnh viễn kiểu DoS), ghi `account_locked` |
| Thông báo lỗi đăng nhập | Luôn chung chung: "Tên đăng nhập hoặc mật khẩu không đúng." (không tiết lộ tài khoản có tồn tại hay không) |
| Giới hạn tần suất | `/v1/auth/login` tối đa 10 lần/phút theo IP, dùng `SlidingWindowRateLimiter` sẵn có |
| Khoá tài khoản / đổi vai trò | Thu hồi **toàn bộ** phiên đang mở của người đó ngay lập tức kèm `revoked_reason` (`account_disabled` / `role_changed`) |
| Đổi mật khẩu | Thu hồi các phiên khác (`revoked_reason = 'password_changed'`), giữ phiên hiện tại |
| Mật khẩu tạm | Admin đặt lại → hệ thống sinh mật khẩu ngẫu nhiên 12 ký tự, hiện **một lần duy nhất**, bắt buộc đổi ở lần đăng nhập kế tiếp |
| Bảo vệ quản trị | Admin không tự khoá/hạ vai trò chính mình; luôn phải còn ít nhất 1 admin đang hoạt động |

### 5.4. API mới

Mọi phản hồi lỗi dùng phong bì lỗi thống nhất hiện có (`ApiException`). Mọi thao tác ghi 1 dòng `iam.auth_event`; các API quản trị cũng ghi `app.audit_log` như các API khác.

**Xác thực (`/v1/auth`)**

| Method & Path | Ai gọi | Mô tả |
|---|---|---|
| `POST /v1/auth/login` | Chưa đăng nhập | Body `{username, password}` → `200 {access_token, expires_at, user: {user_id, display_name, role, allowed_profiles, must_change_password}}`; sai → `401 INVALID_CREDENTIALS`; đang bị khoá → `423 ACCOUNT_LOCKED` (kèm thời điểm mở khoá); tài khoản bị vô hiệu → `401 INVALID_CREDENTIALS` |
| `POST /v1/auth/logout` | Đã đăng nhập | Thu hồi phiên hiện tại → `200 {"status": "ok"}` |
| `GET /v1/auth/me` | Đã đăng nhập | Trả thông tin người dùng hiện tại (dùng khi tải lại trang) |
| `POST /v1/auth/change-password` | Đã đăng nhập | Body `{current_password, new_password}`; tắt cờ `must_change_password` |

Khi `must_change_password = true`, mọi API khác ngoài `/v1/auth/*` trả `403 PASSWORD_CHANGE_REQUIRED`.

**Quản trị (`/v1/admin`, chỉ `quan_tri_he_thong`; vai trò khác → `403 FORBIDDEN`)**

| Method & Path | Mô tả |
|---|---|
| `GET /v1/admin/users?q=&role=&is_active=` | Danh sách tài khoản (không bao giờ trả `password_hash`) |
| `POST /v1/admin/users` | Tạo tài khoản `{username, display_name, email?, role, allowed_profiles}` → trả kèm **mật khẩu tạm** một lần |
| `PATCH /v1/admin/users/{user_id}` | Sửa `display_name`, `email`, `role`, `allowed_profiles`, `is_active` |
| `POST /v1/admin/users/{user_id}/reset-password` | Sinh mật khẩu tạm mới, thu hồi phiên |
| `POST /v1/admin/users/{user_id}/unlock` | Mở khoá do đăng nhập sai |
| `POST /v1/admin/users/{user_id}/revoke-sessions` | Đăng xuất người đó khỏi mọi thiết bị |
| `GET /v1/admin/users/{user_id}/sessions` | Các phiên đang mở (thời điểm, IP, trình duyệt) |
| `DELETE /v1/admin/sessions/{session_id}` | Thu hồi 1 phiên cụ thể trên toàn hệ thống |
| `GET /v1/admin/sessions` | Danh sách toàn bộ phiên đang mở trên hệ thống |
| `GET /v1/admin/auth-events?user_id=&event_type=&from=&to=` | Nhật ký đăng nhập & quản trị, phân trang |
| `GET /v1/admin/simulation/status` | Trạng thái cập nhật gần nhất của nguồn mô phỏng/dự báo (`synth`, từ `job_heartbeat` + checksum `EVAL`) |
| `POST /v1/admin/simulation/run` | Kích hoạt chạy lại batch tạo dữ liệu mô phỏng/dự báo tháng (`generate_synthetic_warehouse`), xoá cache KPI, ghi `job_heartbeat` + `iam.auth_event` (`simulation_triggered`) |

### 5.5. Thay đổi phía server cho các API hiện có

1. **`TokenAuthVerifier`** (`app/core/auth.py`) xác minh theo thứ tự:
   1. Token tĩnh (token dev 4 vai trò khi `app_env != production`; `auth_tokens_json` cho tài khoản dịch vụ, ví dụ tích hợp Power BI) — giữ nguyên như hiện nay để 278 kiểm thử chạy tiếp.
   2. Tra `iam.user_session` theo `token_hash`, kết hợp `iam.app_user`: phiên chưa thu hồi, chưa quá `expires_at`, `last_seen_at` trong vòng 2 giờ, tài khoản `is_active`. Thành công → cập nhật `last_seen_at` (tối đa 1 lần/phút để giảm ghi).
   - Ở môi trường `production`, token dev **không bao giờ** được nạp (đã đúng như hiện nay) và trang đăng nhập là con đường duy nhất.
2. **`UserPrincipal`** thêm `allowed_profiles: list[str]` (token dev mặc định `['real','synth']`) và `must_change_password: bool = False`.
3. **`resolve_profile`** (`app/api/deps.py`) nhận thêm `user` và từ chối `403 PROFILE_FORBIDDEN` nếu nguồn không nằm trong `allowed_profiles`.
4. Thêm `get_iam_engine()` trỏ cố định CSDL `real` để đọc/ghi schema `iam`.
5. **`/v1/chat`** hiện nhận `data_profile` trong body (không qua `resolve_profile`) — cũng phải áp cùng kiểm tra nguồn dữ liệu.

### 5.6. Giao diện

**a) Trang đăng nhập** — hiện khi chưa có phiên; theme Gỗ Minh Long hiện tại (đỏ `#B82601`, font Be Vietnam Pro, Logo GML), không có thanh bên.

```
┌──────────────────────────────────────────────┐
│                [Logo GML]                     │
│      GỖ MINH LONG · TRỢ LÝ ĐIỀU HÀNH AI       │
│                                               │
│   Tên đăng nhập  [_________________________]  │
│   Mật khẩu       [_________________________]  │
│                                               │
│            [        Đăng nhập        ]        │
│                                               │
│   ⚠ Tên đăng nhập hoặc mật khẩu không đúng.   │
│                                               │
│   Quên mật khẩu? Liên hệ Quản trị hệ thống.   │
└──────────────────────────────────────────────┘
```

**b) Đổi mật khẩu bắt buộc** — sau khi đăng nhập bằng mật khẩu tạm: chỉ có ô mật khẩu hiện tại, mật khẩu mới, nhập lại, và gợi ý quy tắc độ mạnh. Xong → vào màn hình chính.

**c) Thanh bên sau khi đăng nhập** — **bỏ ô chọn vai trò**; thay bằng thẻ người dùng chỉ đọc:

```
┌───────────────────────────────┐
│ [Logo] GỖ MINH LONG · AI      │
├───────────────────────────────┤
│ 👤 Trần Thị B                  │
│    Kế toán trưởng              │
│ 🌐 Nguồn dữ liệu: Thực tế      │  ← chỉ hiện nút chọn nếu được phép ≥ 2 nguồn
├───────────────────────────────┤
│ 📌 Chức năng                   │
│  ◉ Tổng quan  ○ Cảnh báo ...   │
├───────────────────────────────┤
│ 🔑 Đổi mật khẩu                │
│ ↩ Đăng xuất                    │
└───────────────────────────────┘
```

**d) Trang quản trị** — tài khoản `quan_tri_he_thong` chỉ thấy **4 tab quản trị** (không xem dữ liệu tài chính):

- **👥 Người dùng:** ô tìm kiếm + lọc vai trò/trạng thái; bảng *Tên đăng nhập · Họ tên · Vai trò · Nguồn dữ liệu · Trạng thái (Hoạt động / Bị khoá / Vô hiệu) · Đăng nhập gần nhất*; nút **"➕ Thêm người dùng"** mở biểu mẫu; chọn 1 dòng để mở khung chi tiết với các nút *Sửa · Đặt lại mật khẩu · Mở khoá · Thu hồi phiên · Vô hiệu hoá/Kích hoạt*. Mật khẩu tạm hiện trong hộp thông báo kèm nút sao chép và cảnh báo "chỉ hiện một lần".
- **🔐 Phiên đăng nhập:** các phiên đang mở trên toàn hệ thống, thu hồi từng phiên (`revoked_reason = 'admin_revoked'`).
- **⚙️ Dữ liệu Mô phỏng & Dự báo Tháng (`synth`):** xem trạng thái cập nhật mô hình dự báo/dữ liệu mô phỏng gần nhất và bấm **"▶ Chạy cập nhật dữ liệu mô phỏng tháng"** (`POST /v1/admin/simulation/run`) sau khi số liệu cuối tháng đã được nạp.
- **📜 Nhật ký truy cập:** bảng `iam.auth_event` có lọc theo người dùng, loại sự kiện, khoảng ngày; thời gian định dạng `HH:mm · DD/MM/YYYY`.

```
👥 Quản lý người dùng                                  [➕ Thêm người dùng]
[🔍 Tìm tên/username ]  Vai trò [Tất cả ▾]  Trạng thái [Tất cả ▾]
┌────────────┬──────────────┬────────────────┬──────────┬───────────┬──────────────────┐
│ Username   │ Họ tên       │ Vai trò        │ Nguồn    │ Trạng thái│ Đăng nhập gần nhất│
├────────────┼──────────────┼────────────────┼──────────┼───────────┼──────────────────┤
│ nva.ceo    │ Nguyễn Văn A │ Tổng Giám đốc  │ Thực tế… │ 🟢 Hoạt động│ 08:12 · 18/11/2026│
│ ttb.ktt    │ Trần Thị B   │ Kế toán trưởng │ Thực tế… │ 🔒 Bị khoá  │ 17:40 · 17/11/2026│
└────────────┴──────────────┴────────────────┴──────────┴───────────┴──────────────────┘
```

**e) Hết phiên / bị thu hồi:** khi API trả `401`, giao diện xoá cookie + phiên trong `st.session_state` và quay về trang đăng nhập với thông báo "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại."

**f) Liên kết Power BI Quick Ask:** bỏ hẳn tham số `?role=`; giữ `?dashboard=`, `?kpi=`, `?screen=`, `?profile=`. Nếu chưa đăng nhập, hiện trang đăng nhập rồi **mở tiếp đúng liên kết** đã yêu cầu. `?profile=` chỉ có hiệu lực nếu tài khoản được phép nguồn đó.

**g) Giữ đăng nhập khi tải lại trang (F5) — Đã chốt:** lưu token phiên ngẫu nhiên vào cookie trình duyệt `gml_session` (`SameSite=Lax`, `max-age=43200`, thiết lập từ trình duyệt sau khi đăng nhập thành công và xoá khi đăng xuất/401). Khi F5, Streamlit đọc `st.context.cookies.get("gml_session")` và gọi `GET /v1/auth/me` để khôi phục phiên hợp lệ ngay lập tức mà không lộ mật khẩu.

### 5.7. Khởi tạo tài khoản ban đầu

- Lệnh `python -m scripts.create_admin --username <...> --display-name "<...>"` tạo admin đầu tiên, in mật khẩu tạm ra màn hình một lần. Không có mật khẩu mặc định nào nằm trong migration.
- Môi trường dev: lệnh `python -m scripts.seed_demo_users` tạo 4 tài khoản demo (`demo.ceo`, `demo.ktt`, `demo.kho`, `demo.admin`) gắn đúng `user_id` cũ (`allowed_profiles = ['real', 'synth']` cho các vai trò nghiệp vụ); từ chối chạy khi `app_env=production`.

### 5.8. Kiểm thử cần có

- Đăng nhập đúng/sai, khoá sau 5 lần sai, mở khoá sau 15 phút hoặc admin mở khoá.
- Phiên hết hạn tuyệt đối và hết hạn do không hoạt động; đăng xuất; thu hồi phiên có hiệu lực ngay ở request kế tiếp.
- Vô hiệu tài khoản hoặc đổi vai trò → phiên cũ bị từ chối ngay.
- `quan_ly_kho` đăng nhập thật không gọi được KPI tài chính (`403`), không gọi được `/v1/admin/*` (`403`), không dùng được `?profile=synth` nếu admin chỉ cấp `['real']`.
- Không có vai trò nào khác ngoài `quan_tri_he_thong` gọi được `/v1/admin/*` (kể cả `/v1/admin/simulation/run`); admin không tự khoá/hạ quyền mình; không xoá được admin cuối cùng.
- `password_hash`, token thô không xuất hiện trong bất kỳ phản hồi API, `iam.auth_event.detail` hay `app.audit_log`.
- Giao diện: chưa đăng nhập chỉ thấy trang đăng nhập; không còn ô chọn vai trò; `?role=` không có tác dụng; admin chỉ thấy 4 tab quản trị và không xem được số liệu KPI/chat tài chính.
- Toàn bộ 278 kiểm thử hiện có vẫn đạt (token dev giữ nguyên ở môi trường không phải production). Kiểm thử UI cũ giữ một điểm cắm test để không phải viết lại 21 test UI hiện có, kèm bộ test UI riêng ở chế độ bắt buộc đăng nhập.

## 6. Phần để người triển khai tự quyết

- Tên file/module cụ thể: `app/api/routers/auth.py`, `app/api/routers/admin.py`, `app/services/iam_service.py`, `app/ui/components/login_view.py`, `app/ui/components/admin_view.py`.
- Bố cục chi tiết biểu mẫu quản trị và câu chữ thông báo, miễn tuân theo theme và định dạng tiếng Việt hiện có.
- Cách dọn phiên hết hạn cũ (dọn nhẹ khi đăng nhập mới hoặc câu lệnh bảo trì).
- Cập nhật `docs/openapi.json`, `api_contract.txt` và ảnh EV-16 theo quy trình như các đợt trước.

## 7. Các quyết định đã chốt từ người dùng (18/11/2026)

1. **Giữ đăng nhập khi tải lại trang (F5):** **Có** — dùng cookie `gml_session` (`SameSite=Lax`, `max-age=43200`) + `st.context.cookies` + `GET /v1/auth/me`.
2. **Nguồn dữ liệu mô phỏng / dự báo (`synth`):** Các vai trò nghiệp vụ (`ceo`, `ke_toan_truong`, `quan_ly_kho`) mặc định có `allowed_profiles = ['real', 'synth']` để **xem** kết quả dự báo cuối tháng (admin vẫn có thể tuỳ chỉnh từng người); **chỉ `quan_tri_he_thong`** được phép chạy lại batch mô phỏng/dự báo cuối tháng (`POST /v1/admin/simulation/run`).
3. **Tách bạch quản trị và nghiệp vụ:** **Tách biệt hoàn toàn** — `quan_tri_he_thong` chỉ dùng Trang quản trị, không xem dữ liệu tài chính/vận hành.
4. **Liên kết Power BI Quick Ask:** **Bỏ hẳn `?role=`** — vai trò luôn xác định theo tài khoản đã đăng nhập.
5. **Thông số bảo mật & phiên:** **Đồng ý** với mặc định (Argon2id + chặn timing enumeration, mật khẩu 10–128 ký tự + danh sách từ cấm NIST 800-63B, phiên tối đa 12 giờ / 2 giờ không hoạt động, khoá 15 phút sau 5 lần đăng nhập sai).

---

### Các quyết định tôi tự đặt (cần anh/chị soát lại khi đọc)
- Chọn Phương án A (phiên lưu trong PostgreSQL), để SSO là giai đoạn sau.
- Bảng người dùng đặt ở schema `iam` của CSDL `real`, dùng chung cho cả hai nguồn dữ liệu.
- Giữ nguyên `user_id` cũ (`usr_ceo`, `usr_ktt`, `usr_kho`, `usr_admin`) cho tài khoản ban đầu để không mất lịch sử.
- Các thông số bảo mật ở mục 5.3 (argon2id, mật khẩu ≥ 10 ký tự, 12 giờ / 2 giờ, khoá 15 phút sau 5 lần sai).
- Giữ token dev và `auth_tokens_json` ở môi trường không phải production để toàn bộ kiểm thử hiện có không phải viết lại.

# Hướng dẫn Tạo tài khoản & Đăng nhập Hệ thống (Gỗ Minh Long AI Business Assistant v2)

Hệ thống sử dụng **quản lý tài khoản nội bộ (IAM)** — không có trang tự đăng ký công khai (self-sign-up). Tài khoản mới được tạo bởi Quản trị hệ thống (`quan_tri_he_thong`) hoặc qua script khởi tạo.

---

## 1. Khởi tạo lần đầu (Môi trường mới / Production)

### Bước 1: Áp dụng migration tạo schema & bảng IAM
Đảm bảo PostgreSQL đang chạy và migration `v2/db/migrations/003_iam_users_sessions.sql` đã được áp dụng để tạo schema `iam` (`iam.app_user`, `iam.app_session`, `iam.auth_audit_log`).

### Bước 2: Tạo tài khoản Quản trị hệ thống (`quan_tri_he_thong`) đầu tiên
Chạy lệnh sau trong thư mục `v2/`:

```powershell
python -m scripts.create_admin --username admin.it --display-name "Quản trị IT" --email it@gominhlong.vn
```

- Script `v2/scripts/create_admin.py` chạy idempotent (nếu `username` đã tồn tại sẽ báo lại và **không** ghi đè mật khẩu).
- Khi tạo mới thành công, terminal sẽ in ra **mật khẩu tạm (chỉ hiển thị một lần duy nhất)**.
- Ở lần đăng nhập đầu tiên, hệ thống bắt buộc đổi mật khẩu.

### (Tuỳ chọn) Tạo 4 tài khoản Demo cho môi trường Dev / Staging
> **Lưu ý:** Script từ chối chạy khi `APP_ENV=production`.

Chạy trong thư mục `v2/`:

```powershell
python -m scripts.seed_demo_users
```

Script `v2/scripts/seed_demo_users.py` tạo 4 tài khoản mặc định (mật khẩu chung: `DemoPass@2026`):

| User ID | Username | Vai trò (`role`) | Nguồn dữ liệu (`allowed_profiles`) | Ghi chú |
|---|---|---|---|---|
| `usr_ceo` | `demo.ceo` | `ceo` | `real`, `synth` | Xem điều hành & AI |
| `usr_ktt` | `demo.ktt` | `ke_toan_truong` | `real`, `synth` | Xem tài chính/công nợ & AI |
| `usr_kho` | `demo.kho` | `quan_ly_kho` | `real`, `synth` | Xem tồn kho & AI |
| `usr_admin` | `demo.admin` | `quan_tri_he_thong` | `real`, `synth` | Chỉ truy cập Admin Panel |

---

## 2. Tạo tài khoản cho nhân sự mới (trên Admin Panel)

1. Đăng nhập bằng tài khoản có vai trò **`quan_tri_he_thong`**.
2. Mở tab **1. `👥 Người dùng`** trong Admin Panel (`v2/app/ui/components/admin_view.py`).
3. Điền thông tin tạo tài khoản mới:
   - **Username:** chữ thường, không dấu (ví dụ: `lan.kt`, `minh.kho`).
   - **Họ tên hiển thị** & **Email** (tuỳ chọn).
   - **Vai trò:** chọn 1 trong 4 vai trò: `ceo`, `ke_toan_truong`, `quan_ly_kho`, hoặc `quan_tri_he_thong`.
   - **Nguồn dữ liệu được phép:** `Thực tế` (`real`) và/hoặc `Mô phỏng` (`synth`).
4. Sau khi tạo, hệ thống hiển thị **mật khẩu tạm một lần duy nhất** trên màn hình. Admin sao chép và gửi cho người dùng qua kênh nội bộ bảo mật.

---

## 3. Hướng dẫn Người dùng Đăng nhập & Đổi mật khẩu lần đầu

1. Mở giao diện ứng dụng Streamlit (`v2/app/ui/streamlit_app.py`), nhập **Username** và **Mật khẩu tạm** được cấp.
2. Nếu đây là lần đăng nhập đầu tiên (hoặc tài khoản vừa được Admin reset mật khẩu), màn hình **🔑 Đổi mật khẩu bắt buộc** (`v2/app/ui/components/login_view.py`) sẽ hiển thị.
3. Nhập **Mật khẩu hiện tại** (mật khẩu tạm) và **Mật khẩu mới** tuân thủ quy định **NIST 800-63B**:
   - Độ dài **10–128 ký tự**.
   - Có **cả chữ và số** (cho phép dấu cách).
   - Không trùng với username, email hoặc các từ mật khẩu phổ biến bị cấm.
4. Nhấn **✅ Đổi mật khẩu** để hoàn tất và vào giao diện làm việc theo đúng vai trò.

---

## 4. Lưu ý vận hành & bảo mật phiên đăng nhập

- **Giữ đăng nhập khi tải lại trang (F5):** Cookie phiên `gml_session` tự động duy trì tối đa **12 giờ** (tự hết hạn nếu không hoạt động quá **2 giờ**).
- **Khoá tạm thời khi nhập sai:** Nhập sai mật khẩu **5 lần liên tiếp** sẽ tự động khoá tài khoản **15 phút** (Admin có thể mở khoá thủ công hoặc reset mật khẩu trong tab `👥 Người dùng`).
- **Tách biệt Quản trị & Nghiệp vụ:** Tài khoản `quan_tri_he_thong` chỉ thấy 4 tab Admin Panel (bao gồm chạy mô phỏng `synth` cuối tháng ở tab `⚙️ Dữ liệu Mô phỏng & Dự báo`), không vào màn hình AI nghiệp vụ; các vai trò nghiệp vụ chỉ xem được các nguồn dữ liệu đã được cấp phép.

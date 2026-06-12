# Lab Ngày 12 - Câu trả lời nhiệm vụ

## Phần 1: Localhost và Production

### Bài tập 1.1: Các anti-pattern được tìm thấy

1. Các thông tin bí mật (secrets) và thông tin đăng nhập cơ sở dữ liệu bị hardcode (viết cứng vào code).
2. API key bị in ra log.
3. Chế độ debug tự động tải lại (debug reload) luôn được bật.
4. Host và port bị hardcode cho localhost.
5. Không có endpoint kiểm tra sức khỏe (health check) hoặc mức độ sẵn sàng (readiness check).
6. Không có vòng đời tắt ứng dụng an toàn (graceful shutdown).
7. Cấu hình không được tải từ biến môi trường (environment variables).

### Bài tập 1.3: So sánh

| Tính năng | Phát triển (Develop) | Triển khai (Production) | Tại sao quan trọng? |
|---|---|---|---|
| Cấu hình | Viết cứng (Hardcoded) | Biến môi trường | Cùng một artifact có thể hoạt động trên nhiều môi trường khác nhau |
| Kiểm tra sức khỏe | Không có | `/health` và `/ready` | Các nền tảng có thể khởi động lại hoặc dừng điều hướng lưu lượng đến các instance không khỏe mạnh |
| Ghi log (Logging) | Dùng `print()` và rò rỉ secret | Log có cấu trúc và không chứa thông tin bí mật | Dễ dàng tìm kiếm và vận hành an toàn hơn |
| Tắt ứng dụng (Shutdown) | Đột ngột | Lifespan/graceful timeout | Cho phép các yêu cầu đang xử lý được hoàn thành |

## Phần 2: Docker

### Bài tập 2.1

1. Image cơ sở cho môi trường phát triển (Develop base image): `python:3.11`.
2. Thư mục làm việc (Working directory): `/app`.
3. File requirements được copy trước để các layer phụ thuộc (dependency layers) được lưu trong cache khi chỉ có mã nguồn thay đổi.
4. `CMD` cung cấp một lệnh mặc định có thể bị thay thế; `ENTRYPOINT` định nghĩa lệnh thực thi thường cố định.

### Bài tập 2.3: So sánh Image

- Image môi trường phát triển (Develop image): khoảng 424 MB.
- Image môi trường production (Production image): khoảng 57 MB.
- Image production nhỏ hơn khoảng 87% nhờ vào runtime phiên bản slim và kỹ thuật build đa tầng (multi-stage build).

## Phần 3: Triển khai Cloud

Railway sử dụng `railway.toml`, Railpack, biến môi trường `PORT` được inject (tiêm vào), và endpoint `/health`.
URL triển khai công khai (public deployment URL) phải được ghi lại trong file `DEPLOYMENT.md` sau khi triển khai thành công.

## Phần 4: Bảo mật API

- Xác thực API-key từ chối các key bị thiếu hoặc sai bằng phản hồi HTTP 401.
- JWT phù hợp khi thông tin danh tính và vai trò cần được truyền tải trong các token được ký số.
- Giới hạn tần suất (Rate limiting) sử dụng cơ chế sliding window (cửa sổ trượt) lưu trong Redis và trả về HTTP 429 sau 10 yêu cầu/phút.
- Tính năng giám sát chi phí (Cost guard) lưu trữ mức chi tiêu hàng tháng của từng người dùng trong Redis và trả về HTTP 402 khi vượt quá ngân sách (budget).

## Phần 5: Khả năng mở rộng và Độ tin cậy

- Endpoint `/health` kiểm tra xem tiến trình có đang hoạt động hay không (liveness).
- Endpoint `/ready` xác minh kết nối tới Redis trước khi chấp nhận lưu lượng truy cập.
- Uvicorn nhận tín hiệu SIGTERM và có thời gian chờ tắt ứng dụng an toàn (graceful shutdown timeout) là 30 giây.
- Lịch sử cuộc hội thoại, giới hạn tần suất và mức sử dụng ngân sách được lưu trữ trong Redis.
- Nginx phân phối các yêu cầu đến các container agent đã được scale (mở rộng).

# Thanh Vị – Xử lý ảnh

Mở `ThanhVi.exe` bản 1.1.0. Không cần Python, mạng hoặc quyền quản trị.

## Hai chế độ

**Tự động:** thả ảnh/thư mục hoặc dùng nút chọn để xoá logo, ký tên và lưu hàng loạt như trước.

**Chỉnh tay:** thả ảnh/thư mục, chọn ảnh trong danh sách. Chỉnh đường kính cọ (pixel ảnh gốc), tô vùng cần bỏ và nhả chuột để phục hồi. Lăn chuột để zoom; giữ Space rồi kéo để di chuyển. Có Vừa khung và 100%. `Ctrl+Z` hoàn tác, `Ctrl+Y` làm lại; tối đa 20 nét. Khôi phục đưa phần chỉnh tay về ảnh ban đầu.

Hai tick Xoá logo và Thêm chữ ký độc lập, được ghi nhớ. Xử lý lớp logo/chữ ký không làm tích luỹ chữ khi xem hoặc lưu nhiều lần. Cọ phù hợp vết bẩn/vật nhỏ; vật lớn và nền phức tạp có thể lộ chỗ vá.

## Lưu và kéo sang web

- **Lưu** (`Ctrl+S`): lần đầu tạo bản mới cạnh nguồn, các lần sau cập nhật tệp kết quả của phiên đó.
- **Lưu thành…** (`Ctrl+Shift+S`): chọn tên/nơi lưu và PNG/JPG. Không ghi đè ảnh nguồn. Hộp thoại hỏi trước khi thay tệp có sẵn.
- **Kéo ảnh nhỏ ở cột trái** vào vùng nhận ảnh của website. App tự lưu kết quả mới nhất trước, rồi kéo tệp thật; nếu lưu lỗi thì không kéo. Huỷ kéo vẫn giữ tệp đã lưu. Trang web phải hỗ trợ thả tệp.
- **Tick xoá nguồn cũng áp dụng lúc kéo** vì kéo sẽ tự lưu trước. Kiểm tra tick này trước thao tác; mặc định tắt.
- Rời ảnh hoặc đóng app khi chưa lưu sẽ hỏi Lưu / Bỏ thay đổi / Huỷ.
- Chế độ đã chọn, cỡ cọ và các cài đặt được ghi nhớ qua lần mở sau.

## Quy tắc đầu ra

- Luôn xoá vùng logo góc phải dưới; khi không tìm thấy logo, app dùng vùng mặc định theo ảnh mẫu. Chi tiết nền trong vùng này có thể thay đổi.
- Chữ ký Thanh Vị màu trắng, kiểu viết tay, mặc định hiện 80%. Thanh cỡ chữ tính theo phần trăm cạnh ngắn của ảnh.
- PNG đổi sang JPG chất lượng 95; định dạng khác đổi sang PNG. Nền trong suốt được ghép trắng khi xuất JPG.
- Tệp mới nằm cạnh nguồn, thêm `_ThanhVi`; trùng tên sẽ thêm số. App bỏ qua các tệp đầu ra này khi thả thư mục.
- Mặc định giữ ảnh gốc. Nếu bật xoá nguồn, app chỉ xoá sau khi lưu và đọc kiểm tra ảnh mới thành công. Lựa chọn được ghi nhớ, hãy kiểm tra trước mỗi lượt.
- Hỗ trợ ảnh tĩnh PNG, JPEG, WebP, BMP, TIFF; duyệt cả thư mục con. Không hỗ trợ ảnh động hoặc TIFF nhiều trang.
- Bỏ metadata thông thường; không bảo đảm xoá watermark ẩn hoặc mọi dấu hiệu ảnh AI. Màu có thể khác trên ảnh dùng cấu hình ICC đặc biệt vì đầu ra không giữ ICC.

## Mã nguồn

Python 3.11; phụ thuộc Pillow, numpy, opencv-python, PySide6-Essentials, PyInstaller. Tạo/kích hoạt môi trường `.venv` rồi cài `pip install -r requirements.txt`. Đóng kèm phông Dancing Script hỗ trợ tiếng Việt, giấy phép OFL trong `assets/fonts/OFL.txt`. Thư viện Qt và giấy phép: `THIRD_PARTY_NOTICES.md` (xem nút Giấy phép trong app).

Chạy: `python app.py`

Kiểm tra: `python -m unittest test_processor.py test_editor.py test_drop.py`

Đóng gói (bao gồm phông chữ): `python -m PyInstaller --noconfirm --clean ThanhVi.spec`

Kiểm tra mã/phông và phục hồi ảnh bên trong EXE: `python verify_release.py`.

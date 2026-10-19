# Thanh Vị – Xử lý ảnh

Mở `ThanhVi.exe`, thả ảnh hoặc thư mục vào cửa sổ. Có thể dùng nút Chọn ảnh hoặc Chọn thư mục. Không cần Python, mạng hoặc quyền quản trị.

- Luôn xoá vùng logo góc phải dưới; khi không tìm thấy logo, app dùng vùng mặc định theo ảnh mẫu. Chi tiết nền trong vùng này có thể thay đổi.
- Chữ ký Thanh Vị màu trắng, kiểu viết tay, mặc định hiện 80%. Thanh cỡ chữ tính theo phần trăm cạnh ngắn của ảnh.
- PNG đổi sang JPG chất lượng 95; định dạng khác đổi sang PNG. Nền trong suốt được ghép trắng khi xuất JPG.
- Tệp mới nằm cạnh nguồn, thêm `_ThanhVi`; trùng tên sẽ thêm số. App bỏ qua các tệp đầu ra này khi thả thư mục.
- Mặc định giữ ảnh gốc. Nếu bật xoá nguồn, app chỉ xoá sau khi lưu và đọc kiểm tra ảnh mới thành công. Lựa chọn được ghi nhớ, hãy kiểm tra trước mỗi lượt.
- Hỗ trợ ảnh tĩnh PNG, JPEG, WebP, BMP, TIFF; duyệt cả thư mục con. Không hỗ trợ ảnh động hoặc TIFF nhiều trang.
- Bỏ metadata thông thường; không bảo đảm xoá watermark ẩn hoặc mọi dấu hiệu ảnh AI. Màu có thể khác trên ảnh dùng cấu hình ICC đặc biệt vì đầu ra không giữ ICC.

## Mã nguồn

Python 3.11; phụ thuộc Pillow, numpy, opencv-python, PyInstaller. Dùng phông Segoe Script có sẵn trên Windows.

Chạy: `python app.py`

Kiểm tra: `python -m unittest test_processor.py`

Đóng gói: `python -m PyInstaller --noconfirm --clean --onefile --windowed --name ThanhVi --exclude-module gradio --exclude-module matplotlib --exclude-module scipy --exclude-module pandas app.py`

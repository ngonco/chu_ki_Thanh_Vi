[⬇ TẢI THANHVI.EXE — BẢN MỚI NHẤT](https://github.com/ngonco/chu_ki_Thanh_Vi/releases/latest/download/ThanhVi.exe)

# Thanh Vị – Xử lý ảnh

App Windows chạy offline, không cần cài đặt. Thả ảnh hoặc thư mục để xoá vùng logo Gemini góc phải dưới và thêm chữ ký **Thanh Vị**.

## Sử dụng

1. Tải và mở `ThanhVi.exe` bằng link trên.
2. Chọn độ hiện chữ ký (mặc định 80%) và kích thước.
3. Thả ảnh/thư mục vào cửa sổ, hoặc dùng nút chọn.
4. Ảnh mới lưu cạnh ảnh nguồn, tên thêm `_ThanhVi`. Mặc định giữ ảnh gốc; tuỳ chọn xoá nguồn được ghi nhớ.

PNG đổi sang JPG chất lượng 95; các định dạng được hỗ trợ khác đổi sang PNG. App luôn xử lý vùng logo, kể cả không phát hiện chắc chắn, nên có thể thay đổi chi tiết nền. Loại metadata thông thường; không bảo đảm xoá watermark ẩn hoặc mọi dấu hiệu ảnh AI.

Hỗ trợ PNG, JPG/JPEG, WebP, BMP, TIFF tĩnh; duyệt thư mục con. [Hướng dẫn đầy đủ](HUONG_DAN.md).

## Phát triển

- Đọc [system_map.md](system_map.md) để hiểu kiến trúc và điểm mở rộng.
- Đọc [AGENTS.md](AGENTS.md) trước khi sửa.
- Python 3.11 trên Windows: `python -m pip install -r requirements.txt`
- Chạy: `python app.py`
- Kiểm tra: `python -m unittest test_processor.py` và `python test_drop.py`
- Đóng gói: `python -m PyInstaller --noconfirm --clean ThanhVi.spec`

File phát hành nằm tại `dist/ThanhVi.exe`. Không đưa ảnh cá nhân hoặc thư mục build vào Git.

## Bản 1.0.1

- Sửa bỏ sót nét logo mờ trên nền có nhiều chi tiết; phục hồi bằng miếng nền lân cận.
- Đóng kèm phông viết tay hỗ trợ đầy đủ “Thanh Vị”, sửa lỗi ký tự vuông ở chữ “ị”.
- Build sạch và kiểm tra mã, phông bên trong `.exe` trước khi phát hành.

Phông Dancing Script sử dụng theo [giấy phép OFL](assets/fonts/OFL.txt).

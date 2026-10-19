[⬇ TẢI THANHVI.EXE — BẢN MỚI NHẤT](https://github.com/ngonco/chu_ki_Thanh_Vi/releases/latest/download/ThanhVi.exe)

# Thanh Vị – Xử lý ảnh

App Windows chạy offline, không cần cài đặt. Có chế độ tự động xoá vùng logo/ký tên và trình chỉnh tay bằng cọ phục hồi.

## Sử dụng

1. Tải và mở `ThanhVi.exe` bằng link trên.
2. Chọn **Tự động** để xử lý hàng loạt như cũ; hoặc **Chỉnh tay** để xem ảnh và tô vùng cần xoá.
3. Trong Chỉnh tay: chỉnh cỡ cọ, tô và nhả chuột để phục hồi. Lăn chuột để zoom, giữ Space rồi kéo để di chuyển. `Ctrl+Z` hoàn tác, `Ctrl+Y` làm lại.
4. Bật/tắt riêng **Xoá logo** và **Thêm chữ ký**; độ hiện chữ ký mặc định 80%.
5. Bấm **Lưu** hoặc **Lưu thành…**. Kéo ảnh nhỏ ở cột trái sang vùng nhận ảnh của web để tự lưu và kéo tệp kết quả.

Ảnh mới lưu cạnh nguồn, tên thêm `_ThanhVi`. Mặc định giữ nguồn; lựa chọn xoá nguồn được ghi nhớ và cũng áp dụng khi tự lưu trước lúc kéo. Lưu lại trong cùng phiên cập nhật đúng tệp đầu ra đó.

PNG đổi sang JPG chất lượng 95; các định dạng được hỗ trợ khác đổi sang PNG. App luôn xử lý vùng logo, kể cả không phát hiện chắc chắn, nên có thể thay đổi chi tiết nền. Loại metadata thông thường; không bảo đảm xoá watermark ẩn hoặc mọi dấu hiệu ảnh AI.

Hỗ trợ PNG, JPG/JPEG, WebP, BMP, TIFF tĩnh; duyệt thư mục con. [Hướng dẫn đầy đủ](HUONG_DAN.md).

## Phát triển

- Đọc [system_map.md](system_map.md) để hiểu kiến trúc và điểm mở rộng.
- Đọc [AGENTS.md](AGENTS.md) trước khi sửa.
- Python 3.11 trên Windows: tạo/kích hoạt `.venv`, rồi `python -m pip install -r requirements.txt`
- Chạy: `python app.py`
- Kiểm tra: `python -m unittest test_processor.py test_editor.py test_drop.py`
- Đóng gói: `python -m PyInstaller --noconfirm --clean ThanhVi.spec`

File phát hành nằm tại `dist/ThanhVi.exe`. Không đưa ảnh cá nhân hoặc thư mục build vào Git.

## Bản 1.1.0

- Thêm Chỉnh tay: cọ phục hồi, zoom/pan, lịch sử 20 bước, danh sách ảnh.
- Lưu/Lưu thành và ô kéo ảnh ra web; tự lưu kết quả mới nhất trước khi kéo.
- Chuyển giao diện sang Qt, giữ xử lý offline. Cọ hợp vết bẩn và vật nhỏ, không phải mô hình AI xoá vật lớn.
- Kiểm tra tự động xử lý ảnh, tương tác cọ, lưu và tệp kéo ra đã đạt. Người dùng tự kiểm tra kéo sang Chrome thật theo yêu cầu.
- [Thông báo thư viện và giấy phép Qt](THIRD_PARTY_NOTICES.md).

## Bản 1.0.1

- Sửa bỏ sót nét logo mờ trên nền có nhiều chi tiết; phục hồi bằng miếng nền lân cận.
- Đóng kèm phông viết tay hỗ trợ đầy đủ “Thanh Vị”, sửa lỗi ký tự vuông ở chữ “ị”.
- Build sạch và kiểm tra mã, phông bên trong `.exe` trước khi phát hành.

Phông Dancing Script sử dụng theo [giấy phép OFL](assets/fonts/OFL.txt).

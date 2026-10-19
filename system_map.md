# Bản đồ hệ thống Thanh Vị 1.1.0

## Kiến trúc và điểm bắt đầu

Ứng dụng Windows Python 3.11, PySide6 Essentials (Qt Core/GUI/Widgets), xử lý Pillow/NumPy/OpenCV. Chạy offline, PyInstaller đóng gói một `.exe`. Giao diện trước 1.1.0 dùng Tkinter; mã hook WM_DROPFILES đã được thay bằng Qt.

| Thành phần | Vai trò |
|---|---|
| `app.py` / `App` | Hai chế độ, danh sách ảnh, cài đặt, xem trước, worker, lưu và kéo tệp ra ngoài |
| `app.py` / `Canvas` | QGraphicsView, toạ độ ảnh gốc, mặt nạ cọ liên tục, zoom/pan và lớp tô đỏ |
| `app.py` / `DragTile` | Ô kéo riêng, phát sinh QDrag/QMimeData chứa URL tệp cục bộ |
| `editor.py` / `EditorDocument` | Pixel ảnh chỉnh tay, ảnh ban đầu, lịch sử patch tối đa 20 bước, revision và đường dẫn đầu ra |
| `processor.py` | Thu thập/đọc ảnh, phục hồi mặt nạ, logo, chữ ký và lưu an toàn |
| `ThanhVi.spec` | Đóng gói Qt, font Dancing Script, giấy phép và app thành `dist/ThanhVi.exe` |
| `test_processor.py`, `test_editor.py` | Hồi quy logo/font/metadata/lưu, mặt nạ/alpha, lịch sử và xuất ảnh |
| `test_drop.py` | Qt events kiểm tra đầu vào, cọ ở nhiều mức zoom, pan, lưu, hỏi chưa lưu và MIME đầu ra |
| `verify_release.py` | Lấy module processor/editor và font từ EXE, chạy hồi quy trực tiếp trên mã đóng gói |

## Luồng xử lý

**Tự động:** Qt nhận local URLs → `collect()` (duyệt thư mục, bỏ hậu tố `_ThanhVi`) → worker xử lý từng ảnh qua `process()` → lưu kết quả và báo tiến độ. Chế độ này luôn xoá logo/ký tên, không phụ thuộc hai tick của chế độ chỉnh tay.

**Chỉnh tay:** `collect(include_outputs=True)` cho mở cả ảnh kết quả cũ → `EditorDocument` giữ original và image RGBA riêng → Canvas ánh xạ chuột qua `mapToScene` thành mặt nạ đúng kích thước ảnh → nhả chuột phát `stroke` → worker `heal_region()` → commit patch và cập nhật preview. Ngoài mask, pixel và alpha không thay đổi.

**Preview/xuất:** `render_image()` sao chép pixel chỉnh tay → xoá logo nếu bật → chữ ký nếu bật. Hiệu ứng không được ghi ngược vào pixel chỉnh tay. Cache preview gắn revision; khi lưu chỉ dùng cache nếu revision còn đúng. Đổi hiệu ứng tăng revision và cập nhật preview sau debounce.

**Lưu:** lần đầu sinh tên mới cạnh nguồn; các lần sau cập nhật đúng output của document. Save As chọn tệp khác và hỏi nếu trùng. `save_image()` ghi tệp tạm cùng thư mục → mở đọc kiểm tra → rename/replace nguyên tử → mới xoá nguồn nếu được bật. Không cho đích trùng nguồn. Lỗi không xoá nguồn và không đánh dấu document đã lưu.

**Kéo ra web:** DragTile → lưu mới nhất bằng worker → chờ kết quả trong Qt event loop → `QDrag` với `QMimeData.setUrls([QUrl.fromLocalFile(...)])`, chỉ CopyAction. Lưu lỗi không kéo. Huỷ kéo vẫn giữ tệp đã lưu. Không dùng tệp ảo/ảnh clipboard. Người dùng tự kiểm tra Chrome thật; kiểm tra tự động bao phủ tệp và MIME.

## Trạng thái và ràng buộc

- `EditorDocument` chỉ giữ một ảnh đang mở; chuyển ảnh/đóng app khi dirty hỏi Lưu/Bỏ thay đổi/Huỷ. Không lưu bản nháp vào nguồn.
- Mỗi nét lưu bbox, patch trước và sau; undo/redo tối đa 20 bước, nét mới xoá redo. Khôi phục về original và xoá lịch sử.
- `QThreadPool(maxThreadCount=1)` chạy Job; QObject signals đưa kết quả về GUI. Trong lúc bận khoá chỉnh/lưu/kéo và không cho đóng. Worker lỗi không commit nét cọ. Không gọi widget từ worker.
- Canvas dùng pixel ảnh gốc cho đường kính cọ 1–300. Lăn chuột zoom 2%–3200%, Space + kéo pan; không dùng cọ để kéo tệp.
- Cài đặt ở `%APPDATA%/ThanhViImage/settings.json`: opacity=80, size=3.5 (% cạnh ngắn), delete=False, mode='auto', brush=24, remove_logo=True, signature=True. Đọc được cấu hình 1.0.x và bổ sung mặc định cho trường mới.
- PNG → JPG quality 95/subsampling 0, nền trắng; ảnh khác → PNG. Save As hỗ trợ PNG/JPG. Tệp mới bỏ metadata thông thường/ICC. Giữ kích thước sau áp dụng EXIF orientation. Không hỗ trợ ảnh động/TIFF nhiều trang.

## Giao diện nội bộ và mở rộng

- `read_image(source) -> RGBA Image`; `collect(paths, include_outputs=False) -> list[Path]`.
- `heal_region(image, mask) -> Image`: mask 2D cùng kích thước; trống thì copy, phủ toàn ảnh thì báo lỗi. Telea + tìm miếng nền lân cận theo viền, ghép Poisson; cuối cùng chỉ lấy pixel trong mask. Copy mask trước gọi OpenCV vì seamlessClone có thể thay đổi mặt nạ truyền vào.
- `logo_mask(image) -> (mask, detected)`: luôn phủ vùng quanh (90% rộng, 90% cao), bán kính 3.4% cạnh ngắn; component sáng chỉ mở rộng mask. `clean_logo()` dùng hàm heal chung.
- `sign(image, opacity, size) -> RGBA Image`: Dancing Script Unicode “Thanh Vị”, vẽ 4x rồi thu nhỏ. Font từ assets hoặc `sys._MEIPASS` khi đóng gói; không phụ thuộc font Windows.
- `render_image(image, settings) -> Image`: hiệu ứng không tích luỹ. `save_image(image, source, settings, target=None, overwrite=False) -> (Path, status)` chỉ lưu pixel đã render. `process()` ghép read/render/save cho tự động.
- Thêm công cụ ảnh: tạo hàm thuần trong processor; worker xử lý snapshot, commit patch khi thành công. Giữ thứ tự lớp hiệu ứng và ánh xạ tọa độ gốc. Thêm cài đặt thì cập nhật DEFAULTS/load_settings/App và kiểm tra migration.

## Kiểm tra và phát hành

Tạo/kích hoạt `.venv`, `pip install -r requirements.txt`. Chạy `python -m unittest test_processor.py test_editor.py test_drop.py`. Qt tests dùng nền offscreen và chỉ ảnh thử, không tác động ảnh cá nhân/cài đặt thật.

Build sạch `python -m PyInstaller --noconfirm --clean ThanhVi.spec`, rồi `python verify_release.py`. Có thể chạy `dist/ThanhVi.exe --smoke-test <marker.json>` để mở/đóng GUI và thử xử lý ảnh tổng hợp trong bản đóng gói. Không dùng lại bytecode cũ.

Qt 6.12 dùng API ICU của Windows. Spec phải loại `icuuc.dll` riêng khỏi gói: dependency scanner có thể lấy nhầm ICU của Poppler trên PATH, gây lỗi “DLL load failed / specified procedure could not be found” khi import QtCore. Windows 10/11 cung cấp DLL hệ thống phù hợp. Chế độ smoke ghi traceback vào `<marker>.error.txt` nếu khởi động lỗi.

Cập nhật tài liệu/phiên bản, commit và push main, tạo GitHub Release tăng phiên bản với asset `ThanhVi.exe`, kiểm tra link latest đầu README. Chi tiết quy tắc ở `AGENTS.md`; giấy phép và cách thay thư viện Qt ở `THIRD_PARTY_NOTICES.md`.

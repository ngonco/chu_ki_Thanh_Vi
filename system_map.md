# Bản đồ hệ thống Thanh Vị

## Điểm bắt đầu và kiến trúc

Ứng dụng Windows Python 3.11, giao diện Tkinter; đóng gói một file bằng PyInstaller. Không dùng máy chủ, API hoặc mạng khi chạy.

| Thành phần | Trách nhiệm |
|---|---|
| `app.py` / `App` | Giao diện tiếng Việt, nhận tệp/thư mục, thanh cài đặt, tiến độ, worker và hàng đợi sự kiện |
| `processor.py` | Thu thập ảnh, xoá logo, chữ ký, chuyển định dạng, lưu an toàn, cài đặt |
| `ThanhVi.spec` | Đóng gói app và thư viện vào `dist/ThanhVi.exe` |
| `test_processor.py` | Kiểm tra xử lý, tên trùng, metadata, kích thước, độ hiện, cài đặt và giữ nguồn khi lỗi |
| `test_drop.py` | Gửi thông điệp kéo thả Windows vào cửa sổ thật; xử lý ảnh tạm, kiểm tra đầu ra |
| `AGENTS.md` | Quy tắc sửa, kiểm tra, push main và phát hành `.exe` |

## Luồng dữ liệu

1. Chọn ảnh/thư mục hoặc Windows gửi `WM_DROPFILES` vào cửa sổ. Callback native chỉ đẩy đường dẫn vào queue; không gọi Tkinter trong callback vì có thể gây crash do GIL/reentrancy.
2. `App.poll()` nhận sự kiện `drop`; `App.start()` chụp bản sao cài đặt và chạy worker nền. Trong lúc bận, lượt mới bị từ chối bằng thông báo.
3. `collect(paths)` duyệt thư mục con, lọc phần mở rộng, loại trùng đường dẫn và bỏ tên kết thúc `_ThanhVi` hoặc `_ThanhVi_<số>`.
4. `process(source, settings)` mở ảnh tĩnh, áp dụng EXIF orientation, chuyển RGBA → `clean_logo()` → `sign()`.
5. Tạo ảnh từ pixel sạch để loại metadata; ghi tệp tạm cạnh nguồn, mở đọc kiểm tra kích thước, rename sang tên chưa tồn tại. Trên Windows rename không ghi đè tệp đích.
6. Chỉ sau khi đầu ra thành công mới xoá nguồn nếu `delete=True`. Lỗi xoá nguồn được trả về trong trạng thái; lỗi xử lý giữ nguồn. Tệp tạm được dọn trong `finally`.
7. Worker đưa tiến độ/kết quả vào queue. Chỉ luồng giao diện cập nhật widget. Không đóng app khi đang xử lý.

## Giao diện nội bộ và quy tắc

- `settings`: dict `opacity` (0–100, mặc định 80), `size` (% cạnh ngắn, 1–10, mặc định 3.5), `delete` (bool, mặc định False).
- Cài đặt: `%APPDATA%/ThanhViImage/settings.json`; `load_settings()` dùng mặc định nếu dữ liệu lỗi. `App.changed()` lưu khi chỉnh; lỗi ghi không làm app dừng.
- `collect(paths) -> list[Path]` nhận tệp hoặc thư mục.
- `process(source, settings) -> (Path, str)` trả đường dẫn và trạng thái; ném exception khi xử lý/lưu thất bại.
- `clean_logo(image) -> (Image, bool)` tìm vùng sáng ít bão hoà trong góc 82–97%, lọc connected component theo kích thước, rồi OpenCV Telea inpaint. Nếu không thấy, luôn xử lý hình vuông tại (90% rộng, 90% cao), bán kính 2.9% cạnh ngắn.
- `sign(image, opacity, size) -> RGBA Image` dùng `C:/Windows/Fonts/segoesc.ttf`. Phông thiếu “ị”, nên vẽ “Thanh Vi” và chấm dưới chữ i để tạo chữ ký đủ dấu. Đặt trắng ở góc phải dưới, lề 2.5% cạnh ngắn.
- PNG → JPG quality 95, subsampling 0, nền trắng; đầu vào khác → PNG. Giữ kích thước sau khi áp dụng hướng EXIF. Không giữ ICC; ảnh profile đặc biệt có thể đổi màu.
- Không hỗ trợ ảnh động/TIFF nhiều trang. Không cam kết loại SynthID hoặc mọi dấu hiệu AI.

## Thêm chức năng

- Xử lý ảnh mới: đặt thuật toán trong `processor.py`, nối vào `process()`, kiểm tra đầu vào/đầu ra và quy tắc giữ nguồn khi lỗi.
- Cài đặt mới: thêm mặc định và đọc/kiểm tra trong `load_settings()`, widget trong `App`, đưa vào bản sao settings của worker; cập nhật tài liệu và kiểm tra lưu/đọc.
- Nguồn đầu vào mới: chuẩn hoá về danh sách đường dẫn, gọi `App.start()`. Giữ mọi thao tác Tkinter trên luồng chính.
- Phát hành: chạy kiểm tra → đóng gói → thử `.exe` → commit/push main → tạo tag/release tăng phiên bản với asset `ThanhVi.exe`. Thay đổi chỉ tài liệu không cần build mới.

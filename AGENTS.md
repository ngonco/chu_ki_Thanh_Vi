# Hướng dẫn agent cho dự án Thanh Vị

Đọc `system_map.md` trước khi sửa app. Giữ giao diện tiếng Việt và khả năng chạy offline, không cần cài đặt.

## Hoàn tất mỗi yêu cầu

Người dùng đã yêu cầu tự commit và push GitHub sau khi xong, không cần hỏi lại cho các thay đổi trong phạm vi yêu cầu.

1. Hoàn thành thay đổi; cập nhật `system_map.md` khi thay đổi kiến trúc, luồng dữ liệu hoặc điểm mở rộng; cập nhật hướng dẫn khi hành vi thay đổi.
2. Kích hoạt `.venv`/cài `requirements.txt`; chạy `python -m unittest test_processor.py test_editor.py`. Khi sửa giao diện/kéo thả, chạy thêm `python test_drop.py` trên Windows và kiểm tra khởi động. Không dùng Win32 WndProc cũ: giao diện hiện tại là Qt.
3. Nếu app hoặc phụ thuộc chạy app thay đổi, đóng gói lại bằng `python -m PyInstaller --noconfirm --clean ThanhVi.spec`, chạy `python verify_release.py` để kiểm tra mã và phông trong chính `.exe`, kiểm tra khởi động, rồi phát hành phiên bản GitHub Release mới với asset chính xác tên `ThanhVi.exe`.
4. Commit các tệp liên quan và push lên `main` của `https://github.com/ngonco/chu_ki_Thanh_Vi.git`. Không force push, không ghi đè thay đổi từ xa; nếu remote thay đổi thì tích hợp an toàn và kiểm tra lại.
5. README phải luôn bắt đầu bằng link `https://github.com/ngonco/chu_ki_Thanh_Vi/releases/latest/download/ThanhVi.exe`.
6. Kiểm tra push thành công và asset tải được. Báo rõ nếu bị chặn bởi kết nối hoặc quyền; không khẳng định đã đăng khi chưa thành công.

Không commit ảnh cá nhân, tệp thử, build, thông tin đăng nhập hoặc token. Không tự xoá ảnh nguồn khi kiểm tra. Chỉ xoá nguồn khi người dùng bật tuỳ chọn và ảnh đầu ra đã được lưu, đọc kiểm tra thành công.

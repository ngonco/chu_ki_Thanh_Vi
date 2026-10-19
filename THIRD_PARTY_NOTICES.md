# Thư viện đi kèm Thanh Vị

## Qt for Python / PySide6 Essentials và Shiboken 6.12.0

Copyright The Qt Company Ltd. và các tác giả đóng góp. Các thành phần Qt Core, GUI và Widgets dùng trong ứng dụng được phân phối theo lựa chọn LGPL v3 từ điều khoản giấy phép của Qt for Python. Văn bản LGPL và GPL v3 liên quan nằm trong `assets/licenses/` và trong bản đóng gói.

- Dự án và mã nguồn PySide/Shiboken: https://code.qt.io/cgit/pyside/pyside-setup.git/ (phiên bản 6.12.0).
- Mã nguồn Qt: https://code.qt.io/cgit/qt/qtbase.git/ (phiên bản 6.12.0).
- Thông tin giấy phép: https://doc.qt.io/qtforpython-6/licenses.html

Bạn có thể thay đổi/thay thế các thư viện này và xây lại ứng dụng. Không áp dụng hạn chế đối với việc phân tích ngược nhằm gỡ lỗi các thay đổi thư viện đó. Toàn bộ mã ứng dụng và cấu hình đóng gói công khai tại https://github.com/ngonco/chu_ki_Thanh_Vi .

Để xây lại trên Windows: tạo môi trường Python 3.11 bằng `python -m venv .venv`, kích hoạt `.venv/Scripts/activate`, cài `pip install -r requirements.txt`. Có thể thay PySide/Qt bằng bản thư viện tương thích do bạn tự xây trong môi trường này. Sau đó chạy `python -m PyInstaller --noconfirm --clean ThanhVi.spec`. Qt được nạp bằng thư viện động; mã nguồn ứng dụng không khoá chữ ký thư viện thay thế.

## Dancing Script

Phông Dancing Script được phân phối theo SIL Open Font License 1.1. Giấy phép và thông tin tác giả đầy đủ trong `assets/fonts/OFL.txt`.

## Các phụ thuộc khác

- Python: PSF License — https://docs.python.org/3/license.html
- Pillow: MIT-CMU — https://github.com/python-pillow/Pillow/blob/main/LICENSE
- NumPy: BSD — https://github.com/numpy/numpy/blob/main/LICENSE.txt
- OpenCV: Apache 2.0 — https://github.com/opencv/opencv/blob/4.x/LICENSE
- PyInstaller: GPL v2 với ngoại lệ bootloader cho ứng dụng đóng gói — https://pyinstaller.org/en/stable/license.html

Các thư viện giữ bản quyền và điều khoản riêng; thông báo này không thay thế các giấy phép đó.

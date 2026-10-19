import ctypes, threading, queue
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from processor import collect, process, load_settings, save_settings

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Thanh Vị • Xử lý ảnh')
        self.root.geometry('850x620')
        self.root.minsize(700,500)
        self.root.configure(bg='#f5f3ef')
        self.settings = load_settings()
        self.events = queue.Queue()
        self.busy = False
        self.opacity = tk.DoubleVar(value=self.settings['opacity'])
        self.size = tk.DoubleVar(value=self.settings['size'])
        self.delete = tk.BooleanVar(value=self.settings['delete'])
        frame = ttk.Frame(self.root,padding=24)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Thanh Vị',font=('Segoe UI',24,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Xoá logo góc phải dưới • Ký tên • Lưu ảnh mới').pack(anchor='w',pady=(0,14))
        self.drop = tk.Label(frame,text='THẢ ẢNH HOẶC THƯ MỤC VÀO ĐÂY',bg='#e5eee8',fg='#27543c',font=('Segoe UI',15,'bold'),height=4)
        self.drop.pack(fill='x')
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x',pady=10)
        ttk.Button(buttons,text='Chọn ảnh',command=self.choose_files).pack(side='left')
        ttk.Button(buttons,text='Chọn thư mục',command=self.choose_folder).pack(side='left',padx=8)
        row = ttk.Frame(frame)
        row.pack(fill='x')
        self.opacity_label = ttk.Label(row,width=25)
        self.opacity_label.pack(side='left')
        ttk.Scale(row,from_=0,to=100,variable=self.opacity,command=self.changed).pack(side='left',fill='x',expand=True)
        row2 = ttk.Frame(frame)
        row2.pack(fill='x',pady=8)
        self.size_label = ttk.Label(row2,width=25)
        self.size_label.pack(side='left')
        ttk.Scale(row2,from_=1,to=10,variable=self.size,command=self.changed).pack(side='left',fill='x',expand=True)
        ttk.Checkbutton(frame,text='Xoá ảnh gốc sau khi lưu thành công',variable=self.delete,command=self.changed).pack(anchor='w')
        ttk.Label(frame,text='Luôn xoá vùng logo; có thể thay đổi nền. Không bảo đảm xoá watermark ẩn.',wraplength=760).pack(anchor='w',pady=8)
        self.progress = ttk.Progressbar(frame)
        self.progress.pack(fill='x')
        self.status = ttk.Label(frame,text='Sẵn sàng • Ảnh mới lưu cạnh ảnh nguồn')
        self.status.pack(anchor='w',pady=5)
        self.log = tk.Text(frame,height=9,wrap='word',font=('Segoe UI',10),state='disabled')
        self.log.pack(fill='both',expand=True)
        self.changed()
        self.install_drop()
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.after(100,self.poll)

    def changed(self,*args):
        self.opacity_label.config(text=f'Độ hiện chữ ký: {round(self.opacity.get())}%')
        self.size_label.config(text=f'Cỡ chữ: {self.size.get():.1f}% cạnh ngắn')
        self.settings = {'opacity':round(self.opacity.get()),'size':round(self.size.get(),1),'delete':self.delete.get()}
        try: save_settings(self.settings)
        except OSError: pass

    def choose_files(self):
        self.start(filedialog.askopenfilenames(filetypes=[('Ảnh','*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff')]))

    def choose_folder(self):
        p = filedialog.askdirectory()
        if p: self.start([p])

    def start(self,paths):
        if self.busy:
            messagebox.showinfo('Đang xử lý','Vui lòng đợi lượt hiện tại hoàn tất.')
            return
        if not paths: return
        self.busy = True
        settings = self.settings.copy()
        self.status.config(text='Đang tìm ảnh…')
        threading.Thread(target=self.work,args=(list(paths),settings),daemon=True).start()

    def work(self,paths,settings):
        success = 0
        try:
            files = collect(paths)
            self.events.put(('total',len(files)))
            for i,p in enumerate(files):
                try:
                    target,status = process(p,settings)
                    success += 1
                    text = f'✓ {target}\n  {status}'
                except Exception as e:
                    text = f'✗ {p}\n  {e}'
                self.events.put(('item',(i+1,text)))
            self.events.put(('done',f'Hoàn tất: {success}/{len(files)} ảnh thành công'))
        except Exception as e:
            self.events.put(('done',f'Lỗi: {e}'))

    def poll(self):
        while not self.events.empty():
            kind,data = self.events.get()
            if kind == 'drop': self.start(data)
            elif kind == 'total': self.progress.config(maximum=max(1,data),value=0)
            elif kind == 'item':
                i,text = data
                self.progress.config(value=i)
                self.status.config(text=f'Đã xử lý {i} ảnh')
                self.log.config(state='normal')
                self.log.insert('end',text+'\n')
                self.log.see('end')
                self.log.config(state='disabled')
            else:
                self.busy = False
                self.status.config(text=data)
        self.root.after(100,self.poll)

    def install_drop(self):
        self.root.update()
        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        hwnd = user32.GetParent(self.root.winfo_id())
        ptr = ctypes.c_ssize_t
        proc_type = ctypes.WINFUNCTYPE(ptr,wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM)
        setter = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else user32.SetWindowLongW
        setter.argtypes = [wintypes.HWND,ctypes.c_int,ptr]
        setter.restype = ptr
        user32.CallWindowProcW.argtypes = [ptr,wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
        user32.CallWindowProcW.restype = ptr
        shell32.DragQueryFileW.argtypes = [wintypes.HANDLE,wintypes.UINT,wintypes.LPWSTR,wintypes.UINT]
        shell32.DragFinish.argtypes = [wintypes.HANDLE]
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND,wintypes.BOOL]
        def handler(h,msg,wp,lp):
            if msg == 0x233:
                paths = []
                try:
                    for i in range(shell32.DragQueryFileW(wp,0xffffffff,None,0)):
                        length = shell32.DragQueryFileW(wp,i,None,0)
                        buf = ctypes.create_unicode_buffer(length+1)
                        shell32.DragQueryFileW(wp,i,buf,length+1)
                        paths.append(buf.value)
                finally: shell32.DragFinish(wp)
                self.events.put(('drop',paths))
                return 0
            return user32.CallWindowProcW(self.old_proc,h,msg,wp,lp)
        self.callback = proc_type(handler)
        self.old_proc = setter(hwnd,-4,ctypes.cast(self.callback,ctypes.c_void_p).value)
        shell32.DragAcceptFiles(hwnd,True)

    def close(self):
        if self.busy:
            messagebox.showinfo('Đang xử lý','Đợi xử lý xong trước khi đóng để tránh gián đoạn lưu ảnh.')
            return
        self.root.destroy()

if __name__ == '__main__':
    App().root.mainloop()

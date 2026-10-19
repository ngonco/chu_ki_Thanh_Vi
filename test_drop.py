"""Exercise the Windows file-drop message without touching user images."""
import ctypes, struct, tempfile
from pathlib import Path
from PIL import Image
from app import App

with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
    source=Path(td)/'drop.png'
    Image.new('RGB',(320,320),(50,40,30)).save(source)
    app=App()
    app.delete.set(False)
    app.settings['delete']=False
    kernel=ctypes.windll.kernel32
    kernel.GlobalAlloc.argtypes=[ctypes.c_uint,ctypes.c_size_t]
    kernel.GlobalAlloc.restype=ctypes.c_void_p
    kernel.GlobalLock.argtypes=[ctypes.c_void_p]
    kernel.GlobalLock.restype=ctypes.c_void_p
    kernel.GlobalUnlock.argtypes=[ctypes.c_void_p]
    payload=struct.pack('<IiiII',20,0,0,0,1)+(str(source.resolve())+'\0\0').encode('utf-16-le')
    handle=kernel.GlobalAlloc(0x42,len(payload))
    address=kernel.GlobalLock(handle)
    ctypes.memmove(address,payload,len(payload))
    kernel.GlobalUnlock(handle)
    user=ctypes.windll.user32
    user.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
    hwnd=user.GetParent(app.root.winfo_id())
    user.PostMessageW(hwnd,0x233,handle,0)
    app.root.after(2500,app.root.destroy)
    app.root.mainloop()
    assert source.with_name('drop_ThanhVi.jpg').exists(), 'Drop did not produce output'
    assert source.exists()
    print('Windows file drop OK')

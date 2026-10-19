from pathlib import Path
import os, re, tempfile, json
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

SUPPORTED = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'}
OUTPUT = re.compile(r'_ThanhVi(?:_\d+)?$', re.I)
DEFAULTS = {'opacity': 80, 'size': 3.5, 'delete': False}

def settings_path():
    return Path(os.environ.get('APPDATA', str(Path.home()))) / 'ThanhViImage' / 'settings.json'

def load_settings():
    try:
        d = json.loads(settings_path().read_text(encoding='utf-8'))
        return {'opacity': max(0, min(100, int(d['opacity']))), 'size': max(1, min(10, float(d['size']))), 'delete': d.get('delete') is True}
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULTS.copy()

def save_settings(settings):
    p = settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(settings), encoding='utf-8')

def collect(paths):
    found = {}
    for item in paths:
        p = Path(item)
        candidates = p.rglob('*') if p.is_dir() else [p]
        for f in candidates:
            if f.is_file() and f.suffix.lower() in SUPPORTED and not OUTPUT.search(f.stem):
                found[str(f.resolve()).casefold()] = f
    return list(found.values())

def clean_logo(im):
    # Gemini reference: center (90%, 90%), star diameter about 5% of short edge.
    a = np.array(im.convert('RGB'))
    h, w = a.shape[:2]
    s = min(w, h)
    x0, y0 = int(w * .82), int(h * .82)
    roi = a[y0:int(h*.97), x0:int(w*.97)]
    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    bright = ((gray > 140) & ((roi.max(2).astype(int)-roi.min(2)) < 45)).astype('uint8')*255
    n, labels, stats, centers = cv2.connectedComponentsWithStats(bright)
    choices = []
    for i in range(1, n):
        x,y,bw,bh,area = stats[i]
        cx,cy = centers[i] + [x0,y0]
        if .018*s < bw < .085*s and .018*s < bh < .085*s and .4 < bw/bh < 2 and area > .00012*s*s:
            choices.append(((cx/w-.9)**2+(cy/h-.9)**2, i))
    mask = np.zeros((h,w), np.uint8)
    detected = bool(choices)
    if detected:
        i = min(choices)[1]
        region = (labels == i).astype('uint8')*255
        r = max(2, round(s*.004))
        region = cv2.dilate(region, np.ones((2*r+1,2*r+1), np.uint8))
        mask[y0:y0+roi.shape[0],x0:x0+roi.shape[1]] = region
    else:
        cx,cy = round(w*.9),round(h*.9)
        r = max(3, round(s*.029))
        cv2.rectangle(mask, (max(0,cx-r),max(0,cy-r)), (min(w-1,cx+r),min(h-1,cy+r)), 255, -1)
    result = Image.fromarray(cv2.inpaint(a,mask,max(3,round(s*.006)),cv2.INPAINT_TELEA))
    if im.mode == 'RGBA':
        result.putalpha(im.getchannel('A'))
    return result, detected

def sign(im, opacity, size):
    im = im.convert('RGBA')
    font = ImageFont.truetype(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'segoesc.ttf'), max(8, round(min(im.size)*size/100)))
    layer = Image.new('RGBA',im.size)
    d = ImageDraw.Draw(layer)
    # Segoe Script lacks U+1ECB: compose the Vietnamese dot below manually.
    text = 'Thanh Vi'
    box = d.textbbox((0,0),text,font=font)
    margin = max(4,round(min(im.size)*.025))
    x,y = im.width-margin-box[2],im.height-margin-box[3]-max(2,round(font.size*.12))
    ink = (255,255,255,round(opacity*255/100))
    d.text((x,y),text,font=font,fill=ink)
    dot_x = x+d.textlength('Thanh V',font=font)+d.textlength('i',font=font)*.48
    dot_y = y+box[3]+max(2,font.size*.08)
    radius = max(.7,font.size*.025)
    d.ellipse((dot_x-radius,dot_y-radius,dot_x+radius,dot_y+radius),fill=ink)
    return Image.alpha_composite(im,layer)

def process(source, settings):
    source = Path(source)
    with Image.open(source) as original:
        if getattr(original,'n_frames',1) != 1:
            raise ValueError('Chỉ hỗ trợ ảnh tĩnh một khung hình')
        im = ImageOps.exif_transpose(original).convert('RGBA')
    im, detected = clean_logo(im)
    im = sign(im,settings['opacity'],settings['size'])
    ext = '.jpg' if source.suffix.lower() == '.png' else '.png'
    if ext == '.jpg':
        bg = Image.new('RGB',im.size,'white')
        bg.paste(im,mask=im.getchannel('A'))
        im = bg
    # Fresh pixels ensure EXIF, comments, ICC, XMP and other source info are omitted.
    im = Image.frombytes(im.mode, im.size, im.tobytes())
    fd, temp = tempfile.mkstemp(prefix='.ThanhVi_',suffix=ext,dir=source.parent)
    os.close(fd)
    target = None
    try:
        im.save(temp, format='JPEG' if ext=='.jpg' else 'PNG', **({'quality':95,'subsampling':0} if ext=='.jpg' else {}))
        with Image.open(temp) as check:
            check.load()
            if check.size != im.size:
                raise ValueError('Kiểm tra ảnh đầu ra thất bại')
        index = 0
        while True:
            target = source.with_name(source.stem+'_ThanhVi'+(f'_{index}' if index else '')+ext)
            try:
                # Windows rename is atomic and refuses existing destinations.
                os.rename(temp,target)
                break
            except FileExistsError:
                index += 1
        status = 'Đã xoá logo' if detected else 'Đã xoá vùng logo mặc định'
        if settings['delete']:
            try:
                source.unlink()
            except OSError as e:
                status += f'; giữ nguồn vì không xoá được: {e}'
        return target, status
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

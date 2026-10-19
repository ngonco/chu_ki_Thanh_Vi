from pathlib import Path
import os, re, tempfile, json, sys
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

SUPPORTED = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'}
OUTPUT = re.compile(r'_ThanhVi(?:_\d+)?$', re.I)
DEFAULTS = {'opacity': 80, 'size': 3.5, 'delete': False, 'mode': 'auto',
            'brush': 24, 'remove_logo': True, 'signature': True}
SIGNATURE_FONT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets' / 'fonts' / 'DancingScript.ttf'

def settings_path():
    return Path(os.environ.get('APPDATA', str(Path.home()))) / 'ThanhViImage' / 'settings.json'

def load_settings():
    try:
        d = json.loads(settings_path().read_text(encoding='utf-8'))
        return {'opacity': max(0, min(100, int(d.get('opacity',80)))),
                'size': max(1, min(10, float(d.get('size',3.5)))), 'delete': d.get('delete') is True,
                'mode': 'manual' if d.get('mode')=='manual' else 'auto',
                'brush': max(1,min(300,int(d.get('brush',24)))),
                'remove_logo': d.get('remove_logo',True) is not False,
                'signature': d.get('signature',True) is not False}
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULTS.copy()

def save_settings(settings):
    p = settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(settings), encoding='utf-8')

def collect(paths, include_outputs=False):
    found = {}
    for item in paths:
        p = Path(item)
        candidates = p.rglob('*') if p.is_dir() else [p]
        for f in candidates:
            if f.is_file() and f.suffix.lower() in SUPPORTED and (include_outputs or not OUTPUT.search(f.stem)):
                found[str(f.resolve()).casefold()] = f
    return list(found.values())

def logo_mask(im):
    # Gemini reference: center (90%, 90%), star diameter about 5% of short edge.
    a = np.array(im.convert('RGB'))
    h, w = a.shape[:2]
    s = min(w, h)
    x0, y0 = int(w * .82), int(h * .82)
    roi = a[y0:int(h*.97), x0:int(w*.97)]
    if not roi.size:
        roi = a
        x0 = y0 = 0
    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    bright = ((gray > 140) & ((roi.max(2).astype(int)-roi.min(2)) < 45)).astype('uint8')*255
    n, labels, stats, centers = cv2.connectedComponentsWithStats(bright)
    choices = []
    for i in range(1, n):
        x,y,bw,bh,area = stats[i]
        cx,cy = centers[i] + [x0,y0]
        if (.018*s < bw < .085*s and .018*s < bh < .085*s and .4 < bw/bh < 2
                and area > .00012*s*s and abs(cx-w*.9) < .025*s and abs(cy-h*.9) < .025*s):
            choices.append(((cx/w-.9)**2+(cy/h-.9)**2, i))
    mask = np.zeros((h,w), np.uint8)
    # Always cover the complete reference footprint, including low-opacity tips.
    # Thresholded components alone miss translucent parts on textured backgrounds.
    cx,cy = round(w*.9),round(h*.9)
    r = max(3, round(s*.034))
    cv2.rectangle(mask, (max(0,cx-r),max(0,cy-r)), (min(w-1,cx+r),min(h-1,cy+r)), 255, -1)
    detected = bool(choices)
    if detected:
        i = min(choices)[1]
        x,y,bw,bh,_ = stats[i]
        pad = max(2,round(s*.006))
        cv2.rectangle(mask,(max(0,x0+x-pad),max(0,y0+y-pad)),
                      (min(w-1,x0+x+bw+pad),min(h-1,y0+y+bh+pad)),255,-1)
    return mask, detected

def heal_region(im, mask):
    """Repair only masked RGB pixels; retain alpha and all unselected pixels exactly."""
    a = np.array(im.convert('RGB'))
    s = min(im.size)
    mask = np.asarray(mask)
    if mask.shape != a.shape[:2]:
        raise ValueError('Mặt nạ phải cùng kích thước ảnh')
    mask = (mask > 0).astype('uint8')*255
    if not mask.any():
        return im.copy()
    if np.all(mask):
        raise ValueError('Vùng tô phủ toàn bộ ảnh; cần chừa nền để phục hồi')
    restored = cv2.inpaint(a,mask,max(3,round(s*.006)),cv2.INPAINT_TELEA)
    # Select nearby intact texture using ONLY the visible boundary, never logo pixels.
    # Poisson blending preserves the donor's detail instead of blurring a large hole.
    x,y,w,h = cv2.boundingRect(mask)
    pad = max(3,round(s*.012))
    x0,y0 = max(0,x-pad),max(0,y-pad)
    x1,y1 = min(im.width,x+w+pad),min(im.height,y+h+pad)
    target = a[y0:y1,x0:x1]
    hole = mask[y0:y1,x0:x1].copy()
    if min(target.shape[:2]) >= 12 and np.count_nonzero(hole==0) > 20:
        radius = max(w,h)*3
        sx,sy = max(0,x0-radius),max(0,y0-radius)
        ex,ey = min(im.width,x1+radius),min(im.height,y1+radius)
        search = a[sy:ey,sx:ex]
        boundary = (hole==0).astype('uint8')*255
        scores = cv2.matchTemplate(search,target,cv2.TM_SQDIFF,mask=boundary)
        overlaps = cv2.matchTemplate((mask[sy:ey,sx:ex]>0).astype('float32'),
                                    np.ones(hole.shape,np.float32),cv2.TM_CCORR)
        scores[overlaps>.5] = np.inf
        if np.isfinite(scores).any():
            dy,dx = np.unravel_index(np.argmin(scores),scores.shape)
            donor = search[dy:dy+target.shape[0],dx:dx+target.shape[1]].copy()
            restored = cv2.seamlessClone(donor,restored,hole,(x0+target.shape[1]//2,y0+target.shape[0]//2),cv2.NORMAL_CLONE)
    restored = np.where(mask[:,:,None]>0,restored,a)
    result = Image.fromarray(restored)
    if im.mode == 'RGBA':
        result.putalpha(im.getchannel('A'))
    return result

def clean_logo(im):
    mask, detected = logo_mask(im)
    if np.all(mask):
        return im.copy(), detected
    return heal_region(im,mask), detected

def sign(im, opacity, size):
    im = im.convert('RGBA')
    scale = 4
    pixels = max(8, round(min(im.size)*size/100))
    font = ImageFont.truetype(str(SIGNATURE_FONT), pixels*scale)
    text = 'Thanh Vị'
    box = font.getbbox(text)
    padding = scale*2
    tile = Image.new('RGBA',(box[2]-box[0]+2*padding,box[3]-box[1]+2*padding))
    d = ImageDraw.Draw(tile)
    d.text((padding-box[0],padding-box[1]),text,font=font,fill=(255,255,255,255))
    tile = tile.resize((max(1,round(tile.width/scale)),max(1,round(tile.height/scale))),Image.Resampling.LANCZOS)
    margin = max(4,round(min(im.size)*.025))
    tile.thumbnail((max(1,im.width-2*margin),max(1,im.height-2*margin)),Image.Resampling.LANCZOS)
    tile.putalpha(tile.getchannel('A').point(lambda a: round(a*opacity/100)))
    layer = Image.new('RGBA',im.size)
    layer.paste(tile,(max(0,im.width-margin-tile.width),max(0,im.height-margin-tile.height)))
    return Image.alpha_composite(im,layer)

def read_image(source):
    with Image.open(source) as original:
        if getattr(original,'n_frames',1) != 1:
            raise ValueError('Chỉ hỗ trợ ảnh tĩnh một khung hình')
        return ImageOps.exif_transpose(original).convert('RGBA')

def render_image(im, settings):
    result = im.copy()
    if settings.get('remove_logo',True):
        result,_ = clean_logo(result)
    if settings.get('signature',True):
        result = sign(result,settings['opacity'],settings['size'])
    return result

def save_image(im, source, settings, target=None, overwrite=False):
    """Save validated pixels atomically; never replace source or delete it on failure."""
    source = Path(source)
    automatic = target is None
    target = Path(target) if target is not None else None
    if target is not None and target.resolve()==source.resolve():
        raise ValueError('Hãy chọn tên mới, không ghi đè ảnh nguồn')
    ext = target.suffix.lower() if target else ('.jpg' if source.suffix.lower()=='.png' else '.png')
    if ext not in ('.jpg','.jpeg','.png'):
        raise ValueError('Chọn định dạng PNG hoặc JPG')
    im = im.convert('RGBA')
    if ext in ('.jpg','.jpeg'):
        bg = Image.new('RGB',im.size,'white')
        bg.paste(im,mask=im.getchannel('A'))
        im = bg
    # Fresh pixels ensure EXIF, comments, ICC, XMP and other source info are omitted.
    im = Image.frombytes(im.mode, im.size, im.tobytes())
    fd, temp = tempfile.mkstemp(prefix='.ThanhVi_',suffix=ext,dir=target.parent if target else source.parent)
    os.close(fd)
    try:
        im.save(temp, format='JPEG' if ext in ('.jpg','.jpeg') else 'PNG', **({'quality':95,'subsampling':0} if ext in ('.jpg','.jpeg') else {}))
        with Image.open(temp) as check:
            check.load()
            if check.size != im.size:
                raise ValueError('Kiểm tra ảnh đầu ra thất bại')
        index = 0
        while True:
            if automatic:
                target = source.with_name(source.stem+'_ThanhVi'+(f'_{index}' if index else '')+ext)
            try:
                # Windows rename is atomic and refuses existing destinations.
                if overwrite:
                    os.replace(temp,target)
                else:
                    os.rename(temp,target)
                break
            except FileExistsError:
                if not automatic:
                    raise
                index += 1
        status = 'Đã lưu ảnh'
        if settings.get('delete',False) and source.exists():
            try:
                source.unlink()
            except OSError as e:
                status += f'; giữ nguồn vì không xoá được: {e}'
        return target, status
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def process(source, settings):
    im = read_image(source)
    return save_image(render_image(im,settings),source,settings)

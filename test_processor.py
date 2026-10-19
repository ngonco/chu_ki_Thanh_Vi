import tempfile, unittest, shutil
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageFont, ImageDraw
import numpy as np
import processor as p

class Tests(unittest.TestCase):
    def test_vietnamese_signature_glyph(self):
        font=ImageFont.truetype(str(p.SIGNATURE_FONT),80)
        glyph=font.getmask('ị')
        missing=font.getmask('\uffff')
        self.assertNotEqual((glyph.size,bytes(glyph)),(missing.size,bytes(missing)))
        self.assertNotEqual(bytes(glyph),bytes(font.getmask('i')))

    def test_translucent_logo_and_bright_distraction(self):
        for size in (256,512,1024):
            base=Image.new('RGB',(size,size),(92,72,41))
            d=ImageDraw.Draw(base)
            # Bright river-like object distracts the former connected-component detector.
            d.rectangle((int(size*.85),int(size*.86),int(size*.88),int(size*.9)),fill=(230,230,230))
            star=Image.new('L',base.size)
            sd=ImageDraw.Draw(star)
            cx=cy=round(size*.9)
            r=round(size*.024)
            k=max(1,round(r*.3))
            sd.polygon([(cx,cy-r),(cx+k,cy-k),(cx+r,cy),(cx+k,cy+k),
                        (cx,cy+r),(cx-k,cy+k),(cx-r,cy),(cx-k,cy-k)],fill=255)
            # Low-opacity star never reaches the old brightness threshold.
            logo=Image.composite(Image.new('RGB',base.size,(130,122,106)),base,star)
            mask,_=p.logo_mask(logo)
            self.assertTrue(np.all(mask[np.array(star)>0]==255))
            result,_=p.clean_logo(logo)
            without_logo,_=p.clean_logo(base)
            # Restored pixels must not depend on any part of the hidden star.
            self.assertTrue(np.array_equal(np.array(result),np.array(without_logo)))

    def test_sizes_and_metadata(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            for size in [(32,32),(800,400),(400,800),(1024,1024)]:
                src=Path(td)/f'{size[0]}x{size[1]}.jpg'
                exif=Image.Exif()
                exif[270]='AI test metadata'
                Image.new('RGB',size,(70,60,50)).save(src,exif=exif)
                out,_=p.process(src,p.DEFAULTS)
                with Image.open(out) as result:
                    self.assertEqual(result.size,size)
                    self.assertFalse(result.getexif())
                    self.assertFalse(result.info)

    def test_processing(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            root=Path(td)
            source=root/'Ảnh thử.png'
            im=Image.new('RGBA',(256,256),(40,50,60,128))
            im.save(source, pnginfo=None)
            out,status=p.process(source,p.DEFAULTS)
            self.assertTrue(source.exists())
            self.assertEqual(out.suffix,'.jpg')
            with Image.open(out) as result:
                self.assertEqual(result.size,(256,256))
                self.assertFalse(result.getexif())
            second,_=p.process(source,p.DEFAULTS)
            self.assertNotEqual(out,second)
            self.assertEqual(p.collect([root]),[source])
            next_out,_=p.process(out,{**p.DEFAULTS,'delete':True})
            self.assertFalse(out.exists())
            self.assertEqual(next_out.suffix,'.png')

    def test_failure_retains_source(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            source=Path(td)/'test.png'
            Image.new('RGB',(64,64)).save(source)
            with patch.object(Image.Image,'save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError): p.process(source,{**p.DEFAULTS,'delete':True})
            self.assertTrue(source.exists())
            self.assertEqual(len(list(Path(td).iterdir())),1)

    def test_opacity(self):
        im=Image.new('RGBA',(512,512),(0,0,0,255))
        self.assertEqual(p.sign(im,0,3.5).tobytes(),im.tobytes())
        self.assertNotEqual(p.sign(im,80,3.5).tobytes(),p.sign(im,100,3.5).tobytes())

    def test_settings(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td, patch.object(p,'settings_path',return_value=Path(td)/'settings.json'):
            self.assertFalse(p.load_settings()['delete'])
            value={'opacity':55,'size':4.2,'delete':True}
            p.save_settings(value)
            self.assertEqual(p.load_settings(),value)

if __name__=='__main__': unittest.main()

import tempfile, unittest, shutil
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import processor as p

class Tests(unittest.TestCase):
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

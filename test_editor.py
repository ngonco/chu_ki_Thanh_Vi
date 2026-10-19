import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from PIL import Image, ImageDraw
import processor as p
from editor import EditorDocument

class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.temp.name)
        self.source=self.root/'Ảnh thử.png'
        image=Image.new('RGBA',(256,192),(80,100,130,170))
        ImageDraw.Draw(image).ellipse((100,70,115,85),fill=(0,0,0,170))
        image.save(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def test_masked_pixels_and_alpha_only(self):
        image=p.read_image(self.source)
        for points in [[(107,77)],[(107,77),(160,80)],[(0,0),(30,0)],[(255,191)]]:
            mask=np.zeros((192,256),np.uint8)
            for point in points:
                cv2.circle(mask,point,12,255,-1)
            if len(points)>1:
                cv2.line(mask,points[0],points[-1],255,24)
            original=mask.copy()
            result=p.heal_region(image,mask)
            self.assertTrue(np.array_equal(mask,original))
            self.assertEqual(result.size,image.size)
            self.assertTrue(np.array_equal(np.array(result)[mask==0],np.array(image)[mask==0]))
            self.assertTrue(np.array_equal(np.array(result)[:,:,3],np.array(image)[:,:,3]))
        mask=np.zeros((192,256),np.uint8)
        cv2.circle(mask,(107,77),15,255,-1)
        result=p.heal_region(image,mask)
        self.assertGreater(np.array(result)[77,107,:3].mean(),50)

    def test_empty_invalid_full_mask(self):
        image=p.read_image(self.source)
        self.assertEqual(p.heal_region(image,np.zeros((192,256),np.uint8)).tobytes(),image.tobytes())
        for mask in [np.zeros((12,12),np.uint8),np.full((192,256),255,np.uint8)]:
            with self.assertRaises(ValueError):
                p.heal_region(image,mask)

    def test_history_patches_undo_redo_reset(self):
        doc=EditorDocument(self.source)
        original=doc.image.tobytes()
        mask=np.zeros((192,256),np.uint8)
        cv2.circle(mask,(107,77),14,255,-1)
        repaired=p.heal_region(doc.image,mask)
        doc.commit_heal(mask,repaired)
        changed=doc.image.tobytes()
        self.assertNotEqual(original,changed)
        self.assertLess(doc.undo_stack[-1][1].width,doc.image.width)
        doc.undo()
        self.assertEqual(doc.image.tobytes(),original)
        doc.redo()
        self.assertEqual(doc.image.tobytes(),changed)
        for i in range(25):
            doc.commit_heal(mask,repaired)
        self.assertEqual(len(doc.undo_stack),20)
        doc.undo()
        doc.commit_heal(mask,repaired)
        self.assertFalse(doc.redo_stack)
        doc.reset()
        self.assertEqual(doc.image.tobytes(),original)
        self.assertFalse(doc.undo_stack)

    def test_layers_do_not_accumulate(self):
        doc=EditorDocument(self.source)
        original=doc.image.tobytes()
        first=doc.render(p.DEFAULTS)
        second=doc.render(p.DEFAULTS)
        self.assertEqual(first.tobytes(),second.tobytes())
        self.assertEqual(doc.image.tobytes(),original)
        raw=doc.render({**p.DEFAULTS,'remove_logo':False,'signature':False})
        self.assertEqual(raw.tobytes(),original)

    def test_repeated_save_and_save_as(self):
        doc=EditorDocument(self.source)
        first,_=p.save_image(doc.image,self.source,p.DEFAULTS)
        replacement=Image.new('RGBA',doc.image.size,'red')
        second,_=p.save_image(replacement,self.source,p.DEFAULTS,first,True)
        self.assertEqual(first,second)
        self.assertEqual(len(list(self.root.glob('*_ThanhVi*'))),1)
        with Image.open(second) as check:
            self.assertGreater(check.getpixel((10,10))[0],230)
        chosen=self.root/'chosen.png'
        p.save_image(doc.image,self.source,p.DEFAULTS,chosen)
        with self.assertRaises(FileExistsError):
            p.save_image(doc.image,self.source,p.DEFAULTS,chosen)
        with self.assertRaises(ValueError):
            p.save_image(doc.image,self.source,p.DEFAULTS,self.source,True)

    def test_failed_replace_never_deletes_source(self):
        image=p.read_image(self.source)
        target=self.root/'out.png'
        Image.new('RGB',(10,10),'blue').save(target)
        original=target.read_bytes()
        with patch.object(p.os,'replace',side_effect=OSError('locked')):
            with self.assertRaises(OSError):
                p.save_image(image,self.source,{**p.DEFAULTS,'delete':True},target,True)
        self.assertTrue(self.source.exists())
        self.assertEqual(target.read_bytes(),original)

if __name__=='__main__':
    unittest.main()

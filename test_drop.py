"""Qt GUI regressions: drop input, real brush events and outgoing file MIME."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt,QPoint,QPointF,QUrl,QMimeData
from PySide6.QtGui import QDragEnterEvent,QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import processor
import app

APPLICATION=QApplication.instance() or QApplication([])

def wait_idle(window):
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        APPLICATION.processEvents()
        if not window.busy and not window.preview_timer.isActive():
            return
        QTest.qWait(10)
    raise AssertionError('GUI worker timeout')

class GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.temp.name)
        self.settings_patch=patch.object(processor,'settings_path',return_value=self.root/'settings.json')
        self.settings_patch.start()
        self.warning_patch=patch.object(app.QMessageBox,'warning')
        self.warning=self.warning_patch.start()
        self.source=self.root/'drop.png'
        image=Image.new('RGB',(400,300),(80,100,140))
        ImageDraw.Draw(image).ellipse((190,140,210,160),fill='black')
        image.save(self.source)
        self.window=app.App()
        self.window.show()
        APPLICATION.processEvents()

    def tearDown(self):
        wait_idle(self.window)
        self.window.doc=None
        self.window.close()
        APPLICATION.processEvents()
        self.window.deleteLater()
        APPLICATION.processEvents()
        self.warning_patch.stop()
        self.settings_patch.stop()
        self.temp.cleanup()

    def open_manual(self):
        self.window.mode.setCurrentIndex(1)
        self.window.remove_logo.setChecked(False)
        self.window.signature.setChecked(False)
        self.window.start([self.source])
        wait_idle(self.window)
        self.assertIsNotNone(self.window.doc)

    def test_incoming_file_drop_auto(self):
        mime=QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.source.resolve()))])
        enter=QDragEnterEvent(QPoint(40,40),Qt.DropAction.CopyAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.window,enter)
        self.assertTrue(enter.isAccepted())
        drop=QDropEvent(QPointF(40,40),Qt.DropAction.CopyAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.window,drop)
        wait_idle(self.window)
        self.assertTrue(self.source.with_name('drop_ThanhVi.jpg').exists())
        self.assertTrue(self.source.exists())

    def test_brush_mapping_zoom_pan_undo(self):
        self.open_manual()
        view=self.window.canvas
        for zoom in [1,2,.6]:
            view.actual_size()
            view.zoom(zoom)
            view.centerOn(200,150)
            APPLICATION.processEvents()
            point=view.mapFromScene(QPointF(200,150))
            original=self.window.doc.image.tobytes()
            QTest.mousePress(view.viewport(),Qt.MouseButton.LeftButton,pos=point)
            QTest.mouseRelease(view.viewport(),Qt.MouseButton.LeftButton,pos=point)
            wait_idle(self.window)
            repaired=self.window.doc.image.tobytes()
            self.assertNotEqual(repaired,original)
            self.window.undo()
            wait_idle(self.window)
            self.assertEqual(self.window.doc.image.tobytes(),original)
            self.window.redo()
            wait_idle(self.window)
            self.assertEqual(self.window.doc.image.tobytes(),repaired)
            self.window.undo()
            wait_idle(self.window)
        self.assertFalse(self.warning.called)

    def test_outgoing_drag_saves_latest_and_reuses_output(self):
        self.open_manual()
        captured=[]
        class FakeDrag:
            def __init__(self,source): pass
            def setMimeData(self,mime):
                captured.append(mime.urls()[0].toLocalFile())
            def setPixmap(self,image): pass
            def exec(self,action): return Qt.DropAction.IgnoreAction
        with patch.object(app,'QDrag',FakeDrag):
            self.window.export_drag(self.window.drag_tile)
            first=self.window.doc.output
            self.assertTrue(first.exists())
            self.assertFalse(self.window.doc.dirty)
            self.window.signature.setChecked(True)
            self.window.export_drag(self.window.drag_tile)
        self.assertEqual(self.window.doc.output,first)
        self.assertEqual(len(captured),2)
        self.assertTrue(all(Path(p)==first.resolve() for p in captured))
        self.assertTrue(self.source.exists())
        self.assertFalse(self.warning.called)

    def test_heal_failure_preserves_working_pixels(self):
        self.open_manual()
        before=self.window.doc.image.tobytes()
        mask=np.full((300,400),255,np.uint8)
        self.window.heal_stroke(mask)
        wait_idle(self.window)
        self.assertEqual(self.window.doc.image.tobytes(),before)
        self.assertFalse(self.window.doc.undo_stack)
        self.assertTrue(self.warning.called)

    def test_save_failure_cancels_drag_and_retains_source(self):
        self.open_manual()
        with patch.object(app,'save_image',side_effect=OSError('disk full')), patch.object(app,'QDrag') as drag:
            self.window.export_drag(self.window.drag_tile)
            self.assertFalse(drag.called)
        self.assertTrue(self.source.exists())
        self.assertIsNone(self.window.doc.output)
        self.assertTrue(self.window.doc.dirty)

    def test_unsaved_cancel_discard_save_and_mode_memory(self):
        self.open_manual()
        actions=[]
        for choice in ['Huỷ','Bỏ thay đổi']:
            with patch.object(app.QMessageBox,'exec',return_value=0), patch.object(app.QMessageBox,'clickedButton',
                    lambda dialog:next(b for b in dialog.buttons() if b.text()==choice)):
                self.window.ensure_leave(lambda:actions.append(choice))
        self.assertEqual(actions,['Bỏ thay đổi'])
        self.assertIsNone(self.window.doc)
        self.window.start([self.source])
        wait_idle(self.window)
        with patch.object(app.QMessageBox,'exec',return_value=0), patch.object(app.QMessageBox,'clickedButton',
                lambda dialog:next(b for b in dialog.buttons() if b.text()=='Lưu')):
            self.window.ensure_leave(lambda:actions.append('saved'))
        wait_idle(self.window)
        self.assertEqual(actions[-1],'saved')
        self.assertTrue(self.window.doc.output.exists())
        self.assertEqual(processor.load_settings()['mode'],'manual')

    def test_space_pan_does_not_paint(self):
        self.open_manual()
        view=self.window.canvas
        view.actual_size()
        view.zoom(3)
        view.setFocus()
        point=QPoint(view.viewport().width()//2,view.viewport().height()//2)
        before=self.window.doc.image.tobytes()
        QTest.keyPress(view,Qt.Key.Key_Space)
        QTest.mousePress(view.viewport(),Qt.MouseButton.LeftButton,pos=point)
        QTest.mouseMove(view.viewport(),point+QPoint(50,30))
        QTest.mouseRelease(view.viewport(),Qt.MouseButton.LeftButton,pos=point+QPoint(50,30))
        QTest.keyRelease(view,Qt.Key.Key_Space)
        wait_idle(self.window)
        self.assertEqual(self.window.doc.image.tobytes(),before)
        self.assertFalse(self.window.doc.undo_stack)

if __name__=='__main__':
    unittest.main()

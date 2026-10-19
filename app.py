"""Vietnamese offline image editor and batch processor, Qt desktop UI."""
import sys
from pathlib import Path
if '--smoke-test' in sys.argv:
    def smoke_exception(exc_type,error,tb):
        import traceback
        marker=Path(sys.argv[sys.argv.index('--smoke-test')+1])
        marker.with_suffix('.error.txt').write_text(''.join(traceback.format_exception(exc_type,error,tb)),encoding='utf-8')
    sys.excepthook=smoke_exception
import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, Slot, QObject, QRunnable, QThreadPool, QTimer, QUrl, QMimeData, QEventLoop
from PySide6.QtGui import QImage, QPixmap, QPainterPath, QPen, QColor, QPainter, QKeySequence, QShortcut, QDrag
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QListWidget, QSplitter, QStackedWidget, QPlainTextEdit,
    QProgressBar, QGraphicsView, QGraphicsScene, QGraphicsPathItem, QDialog)
from processor import collect, process, heal_region, render_image, save_image, load_settings, save_settings
from editor import EditorDocument

VERSION = '1.1.0'

def pixmap(im):
    rgba = im.convert('RGBA')
    data = rgba.tobytes()
    return QPixmap.fromImage(QImage(data,rgba.width,rgba.height,rgba.width*4,QImage.Format.Format_RGBA8888).copy())

class JobSignals(QObject):
    finished = Signal(object)
    progress = Signal(object)

class Job(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = JobSignals()

    def run(self):
        try:
            self.signals.finished.emit((True,self.function(self.signals.progress.emit)))
        except Exception as error:
            self.signals.finished.emit((False,str(error)))

class Canvas(QGraphicsView):
    stroke = Signal(object)
    zoom_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.picture = self.scene().addPixmap(QPixmap())
        self.path_item = QGraphicsPathItem()
        self.path_item.setZValue(2)
        self.scene().addItem(self.path_item)
        pen = QPen(QColor('white'),1)
        pen.setCosmetic(True)
        self.ring = self.scene().addEllipse(0,0,1,1,pen)
        self.ring.setZValue(3)
        self.ring.hide()
        self.setBackgroundBrush(QColor('#272c33'))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAcceptDrops(False)
        self.diameter = 24
        self.image_size = None
        self.mask = None
        self.last_point = None
        self.path = QPainterPath()
        self.space = False
        self.pan_origin = None
        self.locked = False

    def show_image(self, im, fit=False):
        self.picture.setPixmap(pixmap(im))
        self.image_size = im.size
        self.setSceneRect(0,0,*im.size)
        self.clear_stroke()
        if fit:
            self.fit_image()

    def clear_stroke(self):
        self.mask = None
        self.last_point = None
        self.path = QPainterPath()
        self.path_item.setPath(self.path)

    def fit_image(self):
        if self.image_size:
            self.fitInView(self.picture,Qt.AspectRatioMode.KeepAspectRatio)
            self.zoom_changed.emit(self.transform().m11())

    def zoom(self, factor):
        current = self.transform().m11()
        target = max(.02,min(32,current*factor))
        self.scale(target/current,target/current)
        self.zoom_changed.emit(target)

    def actual_size(self):
        self.resetTransform()
        self.zoom_changed.emit(1)

    def wheelEvent(self,event):
        if self.image_size:
            self.zoom(1.2 if event.angleDelta().y()>0 else 1/1.2)
        event.accept()

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space=True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self,event):
        if event.key()==Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space=False
            self.unsetCursor()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def focusOutEvent(self,event):
        self.space=False
        self.pan_origin=None
        self.unsetCursor()
        super().focusOutEvent(event)

    def image_point(self,position):
        point=self.mapToScene(position.toPoint())
        return round(point.x()),round(point.y())

    def paint_point(self,point):
        radius=max(1,round(self.diameter/2))
        if self.last_point is not None:
            cv2.line(self.mask,self.last_point,point,255,self.diameter,cv2.LINE_8)
            self.path.lineTo(*point)
        else:
            self.path.moveTo(*point)
            self.path.lineTo(point[0]+.01,point[1]+.01)
        cv2.circle(self.mask,point,radius,255,-1)
        self.last_point=point
        pen=QPen(QColor(245,77,98,150),self.diameter,
                 Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)
        self.path_item.setPen(pen)
        self.path_item.setPath(self.path)

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton or not self.image_size or self.locked:
            return super().mousePressEvent(event)
        self.setFocus()
        if self.space:
            self.pan_origin=event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            point=self.image_point(event.position())
            w,h=self.image_size
            if 0<=point[0]<w and 0<=point[1]<h:
                self.mask=np.zeros((h,w),np.uint8)
                self.path=QPainterPath()
                self.paint_point(point)
        event.accept()

    def mouseMoveEvent(self,event):
        if self.image_size:
            x,y=self.image_point(event.position())
            r=self.diameter/2
            self.ring.setRect(x-r,y-r,self.diameter,self.diameter)
            self.ring.setVisible(not self.space and not self.locked)
        if self.pan_origin is not None:
            delta=event.position()-self.pan_origin
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-round(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-round(delta.y()))
            self.pan_origin=event.position()
        elif self.mask is not None and not self.locked:
            self.paint_point(self.image_point(event.position()))
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            if self.pan_origin is not None:
                self.pan_origin=None
                self.setCursor(Qt.CursorShape.OpenHandCursor if self.space else Qt.CursorShape.ArrowCursor)
            elif self.mask is not None:
                mask=self.mask
                self.mask=None
                self.last_point=None
                self.stroke.emit(mask)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def leaveEvent(self,event):
        self.ring.hide()
        super().leaveEvent(event)

class DragTile(QLabel):
    """Separate drag handle: painting can never trigger file export."""
    def __init__(self,owner):
        super().__init__('KÉO ẢNH SANG WEB\nTự lưu trước khi kéo')
        self.owner=owner
        self.origin=None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(160,100)
        self.setStyleSheet('background:#e5eee8; border:2px dashed #41765a; border-radius:8px; color:#244d37;')
        self.setToolTip('Kéo ảnh nhỏ sang vùng nhận ảnh trên website. Tự lưu trước khi kéo.')

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.origin=event.position().toPoint()

    def mouseMoveEvent(self,event):
        if self.origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if (event.position().toPoint()-self.origin).manhattanLength()>=QApplication.startDragDistance():
                self.origin=None
                self.owner.export_drag(self)

    def mouseReleaseEvent(self,event):
        self.origin=None

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'Thanh Vị {VERSION} • Xử lý ảnh')
        self.resize(1200,820)
        self.setMinimumSize(900,650)
        self.setAcceptDrops(True)
        self.settings=load_settings()
        self.doc=None
        self.preview_image=None
        self.preview_revision=-1
        self.busy=False
        self.current_index=-1
        self.paths=[]
        self.pool=QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.current_job=None
        self.pending_success=None
        self.pending_failure=None
        self.preview_pending=False
        self.preview_timer=QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.refresh_preview)
        self.shortcuts=[]
        central=QWidget()
        self.setCentralWidget(central)
        layout=QVBoxLayout(central)
        title=QLabel('Thanh Vị  •  Xử lý ảnh offline')
        title.setStyleSheet('font-size:24px; font-weight:600; padding:8px;')
        layout.addWidget(title)
        top=QHBoxLayout()
        self.mode=QComboBox()
        self.mode.addItems(['Tự động','Chỉnh tay'])
        self.mode.setCurrentIndex(1 if self.settings['mode']=='manual' else 0)
        top.addWidget(QLabel('Chế độ:'))
        top.addWidget(self.mode)
        self.open_button=self.button('Chọn ảnh',self.choose_files,top)
        self.folder_button=self.button('Chọn thư mục',self.choose_folder,top)
        self.button('Giấy phép',self.show_licenses,top)
        top.addWidget(QLabel('Hoặc thả ảnh / thư mục vào cửa sổ'))
        top.addStretch()
        layout.addLayout(top)
        split=QSplitter()
        layout.addWidget(split,1)
        sidebar=QWidget()
        side=QVBoxLayout(sidebar)
        form=QFormLayout()
        self.opacity=QSpinBox()
        self.opacity.setRange(0,100)
        self.opacity.setSuffix('%')
        self.opacity.setValue(self.settings['opacity'])
        self.size=QDoubleSpinBox()
        self.size.setRange(1,10)
        self.size.setSingleStep(.1)
        self.size.setSuffix('% cạnh ngắn')
        self.size.setValue(self.settings['size'])
        form.addRow('Độ hiện chữ ký',self.opacity)
        form.addRow('Cỡ chữ ký',self.size)
        side.addLayout(form)
        self.delete=QCheckBox('Xoá nguồn sau khi lưu thành công')
        self.delete.setChecked(self.settings['delete'])
        side.addWidget(self.delete)
        self.remove_logo=QCheckBox('Xoá logo góc phải dưới')
        self.remove_logo.setChecked(self.settings['remove_logo'])
        side.addWidget(self.remove_logo)
        self.signature=QCheckBox('Thêm chữ ký Thanh Vị')
        self.signature.setChecked(self.settings['signature'])
        side.addWidget(self.signature)
        self.brush=QSpinBox()
        self.brush.setRange(1,300)
        self.brush.setSuffix(' px ảnh gốc')
        self.brush.setValue(self.settings['brush'])
        self.brush_label=QLabel('Đường kính cọ phục hồi')
        side.addWidget(self.brush_label)
        side.addWidget(self.brush)
        self.manual_hint=QLabel('Tô rồi nhả chuột để xoá.\nLăn chuột: zoom. Space + kéo: di chuyển.\nHợp vết bẩn và vật nhỏ; nền phức tạp có thể lộ chỗ vá.')
        self.manual_hint.setWordWrap(True)
        side.addWidget(self.manual_hint)
        self.drag_label=QLabel('Kéo ảnh nhỏ dưới đây sang web:')
        side.addWidget(self.drag_label)
        self.drag_tile=DragTile(self)
        side.addWidget(self.drag_tile)
        self.files_label=QLabel('Danh sách ảnh')
        side.addWidget(self.files_label)
        self.files=QListWidget()
        side.addWidget(self.files,1)
        split.addWidget(sidebar)
        right=QWidget()
        right_layout=QVBoxLayout(right)
        self.toolbar=QWidget()
        tools=QHBoxLayout(self.toolbar)
        tools.setContentsMargins(0,0,0,0)
        self.save_button=self.button('Lưu',self.save_current,tools)
        self.save_as_button=self.button('Lưu thành…',self.save_as,tools)
        self.undo_button=self.button('Hoàn tác',self.undo,tools)
        self.redo_button=self.button('Làm lại',self.redo,tools)
        self.reset_button=self.button('Khôi phục',self.reset_document,tools)
        self.button('Vừa khung',lambda:self.canvas.fit_image(),tools)
        self.button('100%',lambda:self.canvas.actual_size(),tools)
        self.button('−',lambda:self.canvas.zoom(1/1.2),tools)
        self.button('+',lambda:self.canvas.zoom(1.2),tools)
        self.zoom_label=QLabel('100%')
        tools.addWidget(self.zoom_label)
        right_layout.addWidget(self.toolbar)
        self.pages=QStackedWidget()
        self.log=QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText('Tự động: thả ảnh để xoá logo, ký tên và lưu bản mới.\nChọn Chỉnh tay để dùng cọ phục hồi.')
        self.canvas=Canvas()
        self.canvas.diameter=self.settings['brush']
        self.pages.addWidget(self.log)
        self.pages.addWidget(self.canvas)
        right_layout.addWidget(self.pages,1)
        split.addWidget(right)
        split.setSizes([285,900])
        self.progress=QProgressBar()
        layout.addWidget(self.progress)
        self.status=QLabel('Sẵn sàng • Kiểm tra lựa chọn giữ/xoá ảnh nguồn trước khi lưu')
        layout.addWidget(self.status)
        self.canvas.stroke.connect(self.heal_stroke)
        self.canvas.zoom_changed.connect(lambda z:self.zoom_label.setText(f'{z*100:.0f}%'))
        self.mode.currentIndexChanged.connect(self.change_mode)
        self.files.currentRowChanged.connect(self.select_row)
        self.opacity.valueChanged.connect(self.visual_changed)
        self.size.valueChanged.connect(self.visual_changed)
        self.signature.toggled.connect(self.visual_changed)
        self.remove_logo.toggled.connect(self.visual_changed)
        self.delete.toggled.connect(self.config_changed)
        self.brush.valueChanged.connect(self.brush_changed)
        for key,callback in [('Ctrl+S',self.save_current),('Ctrl+Shift+S',self.save_as),('Ctrl+Z',self.undo),('Ctrl+Y',self.redo)]:
            shortcut=QShortcut(QKeySequence(key),self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.apply_mode()

    def button(self,text,callback,layout):
        button=QPushButton(text)
        button.clicked.connect(lambda checked=False:callback())
        layout.addWidget(button)
        return button

    def show_licenses(self):
        base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
        dialog=QDialog(self)
        dialog.setWindowTitle('Giấy phép thư viện')
        dialog.resize(740,540)
        layout=QVBoxLayout(dialog)
        text=QPlainTextEdit()
        text.setReadOnly(True)
        contents=[]
        for relative in ['THIRD_PARTY_NOTICES.md','assets/licenses/LGPL-3.0.txt','assets/licenses/GPL-3.0.txt','assets/fonts/OFL.txt']:
            path=base/relative
            if path.exists():
                contents.append(path.read_text(encoding='utf-8'))
        text.setPlainText('\n\n'.join(contents))
        layout.addWidget(text)
        self.button('Đóng',dialog.accept,layout)
        dialog.exec()

    def config_changed(self,*args):
        self.settings={'opacity':self.opacity.value(),'size':self.size.value(),'delete':self.delete.isChecked(),
            'mode':'manual' if self.mode.currentIndex() else 'auto','brush':self.brush.value(),
            'remove_logo':self.remove_logo.isChecked(),'signature':self.signature.isChecked()}
        try:
            save_settings(self.settings)
        except OSError:
            self.status.setText('Không lưu được cài đặt; ảnh vẫn có thể xử lý bình thường')

    def brush_changed(self,*args):
        self.canvas.diameter=self.brush.value()
        self.config_changed()

    def visual_changed(self,*args):
        self.config_changed()
        if self.doc and self.mode.currentIndex()==1:
            self.doc.revision+=1
            self.preview_timer.start(180)

    def apply_mode(self):
        manual=self.mode.currentIndex()==1
        self.pages.setCurrentIndex(1 if manual else 0)
        self.toolbar.setVisible(manual)
        for widget in (self.remove_logo,self.signature,self.brush,self.drag_tile,self.files,
                       self.brush_label,self.manual_hint,self.drag_label,self.files_label):
            widget.setVisible(manual)
        self.update_controls()

    def change_mode(self,index):
        previous=0 if index else 1
        self.mode.blockSignals(True)
        self.mode.setCurrentIndex(previous)
        self.mode.blockSignals(False)
        def change():
            self.mode.blockSignals(True)
            self.mode.setCurrentIndex(index)
            self.mode.blockSignals(False)
            self.config_changed()
            self.apply_mode()
            if index==1 and self.doc:
                self.doc.revision+=1
                self.refresh_preview()
        self.ensure_leave(change)

    def update_controls(self):
        available=self.doc is not None and self.mode.currentIndex()==1 and not self.busy
        for widget in (self.open_button,self.folder_button,self.mode,self.files,self.opacity,self.size,
                       self.delete,self.brush,self.signature,self.remove_logo):
            widget.setEnabled(not self.busy)
        for widget in (self.save_button,self.save_as_button,self.reset_button,self.drag_tile):
            widget.setEnabled(available)
        self.undo_button.setEnabled(available and bool(self.doc.undo_stack))
        self.redo_button.setEnabled(available and bool(self.doc.redo_stack))
        self.canvas.locked=not available

    def run_job(self,function,success,failure=None,message='Đang xử lý…'):
        if self.busy:
            return False
        self.busy=True
        self.pending_success=success
        self.pending_failure=failure
        self.status.setText(message)
        self.update_controls()
        self.current_job=Job(function)
        self.current_job.signals.finished.connect(self.job_done)
        self.current_job.signals.progress.connect(self.job_progress)
        self.pool.start(self.current_job)
        return True

    @Slot(object)
    def job_progress(self,event):
        current,total,text=event
        self.progress.setRange(0,max(1,total))
        self.progress.setValue(current)
        self.log.appendPlainText(text)

    @Slot(object)
    def job_done(self,event):
        ok,result=event
        success,failure=self.pending_success,self.pending_failure
        self.pending_success=self.pending_failure=None
        self.current_job=None
        self.busy=False
        if ok:
            success(result)
        else:
            self.canvas.clear_stroke()
            self.status.setText('Không hoàn tất: '+result)
            if failure:
                failure(result)
            else:
                QMessageBox.warning(self,'Không hoàn tất',result)
        self.update_controls()
        if self.preview_pending and not self.busy:
            self.preview_pending=False
            self.preview_timer.start(1)

    def choose_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Chọn ảnh','','Ảnh (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)')
        if paths:
            self.start(paths)

    def choose_folder(self):
        path=QFileDialog.getExistingDirectory(self,'Chọn thư mục')
        if path:
            self.start([path])

    def dragEnterEvent(self,event):
        if not self.busy and event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self,event):
        if self.busy:
            return
        paths=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.start(paths)

    def start(self,paths):
        if self.busy or not paths:
            return
        paths=list(paths)
        if self.mode.currentIndex()==0:
            settings={**self.settings,'remove_logo':True,'signature':True}
            def batch(progress):
                files=collect(paths)
                success=0
                for i,path in enumerate(files):
                    try:
                        target,status=process(path,settings)
                        success+=1
                        text=f'✓ {target}\n  {status}'
                    except Exception as error:
                        text=f'✗ {path}\n  {error}'
                    progress((i+1,len(files),text))
                return f'Hoàn tất: {success}/{len(files)} ảnh thành công'
            self.run_job(batch,lambda text:self.status.setText(text))
        else:
            self.ensure_leave(lambda:self.run_job(lambda progress:collect(paths,include_outputs=True),self.set_files,message='Đang tìm ảnh…'))

    def set_files(self,paths):
        self.paths=paths
        self.current_index=-1
        self.doc=None
        self.files.blockSignals(True)
        self.files.clear()
        for path in paths:
            self.files.addItem(path.name)
            self.files.item(self.files.count()-1).setToolTip(str(path))
        self.files.blockSignals(False)
        if paths:
            self.open_row(0)
        else:
            self.canvas.picture.setPixmap(QPixmap())
            self.canvas.image_size=None
            self.status.setText('Không tìm thấy ảnh được hỗ trợ')

    def select_row(self,index):
        if index<0 or index==self.current_index or self.busy:
            return
        self.files.blockSignals(True)
        self.files.setCurrentRow(self.current_index)
        self.files.blockSignals(False)
        self.ensure_leave(lambda:self.open_row(index))

    def open_row(self,index):
        self.preview_timer.stop()
        self.preview_pending=False
        settings=self.settings.copy()
        path=self.paths[index]
        def load(progress):
            document=EditorDocument(path)
            return document,document.render(settings)
        def loaded(result):
            self.doc,image=result
            self.current_index=index
            self.files.blockSignals(True)
            self.files.setCurrentRow(index)
            self.files.blockSignals(False)
            self.show_preview(image,True)
            self.status.setText(f'{path.name} • {image.width} × {image.height} • Tô rồi nhả chuột để xoá')
        self.run_job(load,loaded,message='Đang mở ảnh…')

    def show_preview(self,image,fit=False):
        self.preview_image=image
        self.preview_revision=self.doc.revision if self.doc else -1
        self.canvas.show_image(image,fit)
        thumbnail=pixmap(image).scaled(190,110,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
        self.drag_tile.setPixmap(thumbnail)
        self.drag_tile.setToolTip('Kéo ảnh nhỏ sang vùng nhận ảnh trên web. Tự lưu trước khi kéo.')

    def refresh_preview(self):
        if not self.doc:
            return
        if self.busy:
            self.preview_pending=True
            return
        settings=self.settings.copy()
        image=self.doc.image.copy()
        self.run_job(lambda progress:render_image(image,settings),self.show_preview,message='Đang cập nhật ảnh xem trước…')

    def heal_stroke(self,mask):
        if self.busy or not self.doc:
            self.canvas.clear_stroke()
            return
        self.preview_timer.stop()
        image=self.doc.image.copy()
        settings=self.settings.copy()
        def heal(progress):
            result=heal_region(image,mask)
            return result,render_image(result,settings)
        def healed(result):
            repaired,preview=result
            self.doc.commit_heal(mask,repaired)
            self.show_preview(preview)
            self.status.setText('Đã phục hồi vùng tô • Ctrl+Z để hoàn tác')
        self.run_job(heal,healed,message='Đang phục hồi vùng tô…')

    def undo(self):
        if self.doc and not self.busy and self.mode.currentIndex()==1:
            self.doc.undo()
            self.refresh_preview()

    def redo(self):
        if self.doc and not self.busy and self.mode.currentIndex()==1:
            self.doc.redo()
            self.refresh_preview()

    def reset_document(self):
        if self.doc and not self.busy:
            if QMessageBox.question(self,'Khôi phục','Bỏ các nét chỉnh tay và về ảnh ban đầu?')==QMessageBox.StandardButton.Yes:
                self.doc.reset()
                self.refresh_preview()

    def save_as(self):
        if not self.doc or self.busy or self.mode.currentIndex()!=1:
            return
        default=self.doc.output or self.doc.source.with_name(self.doc.source.stem+'_ThanhVi'+('.jpg' if self.doc.source.suffix.lower()=='.png' else '.png'))
        name,filter_=QFileDialog.getSaveFileName(self,'Lưu ảnh thành',str(default),'PNG (*.png);;JPEG (*.jpg *.jpeg)')
        if not name:
            return
        target=Path(name)
        if target.suffix.lower() not in ('.png','.jpg','.jpeg'):
            target=Path(str(target)+('.jpg' if filter_.startswith('JPEG') else '.png'))
        if str(target)!=name and target.exists():
            if QMessageBox.question(self,'Thay tệp','Tệp đã tồn tại. Thay bằng kết quả hiện tại?')!=QMessageBox.StandardButton.Yes:
                return
        self.save_current(target=target,overwrite=True)

    def save_current(self,after=None,target=None,overwrite=False):
        if not self.doc or self.busy or self.mode.currentIndex()!=1:
            return False
        self.preview_timer.stop()
        self.preview_pending=False
        doc=self.doc
        settings=self.settings.copy()
        destination=target if target is not None else doc.output
        replace=overwrite or (destination is not None and destination==doc.output)
        revision=doc.revision
        image=doc.image.copy()
        cached=self.preview_image.copy() if self.preview_revision==revision and self.preview_image else None
        def save(progress):
            rendered=cached if cached is not None else render_image(image,settings)
            path,status=save_image(rendered,doc.source,settings,destination,replace)
            return path,status,rendered
        def saved(result):
            path,status,rendered=result
            doc.output=path
            doc.saved_revision=revision
            self.show_preview(rendered)
            self.status.setText(f'{status}: {path}')
            if after:
                after()
        return self.run_job(save,saved,message='Đang lưu ảnh…')

    def ensure_leave(self,action):
        if self.busy:
            return
        if self.doc and self.doc.dirty:
            dialog=QMessageBox(self)
            dialog.setWindowTitle('Ảnh chưa lưu')
            dialog.setText('Lưu kết quả hiện tại trước khi tiếp tục?')
            save=dialog.addButton('Lưu',QMessageBox.ButtonRole.AcceptRole)
            discard=dialog.addButton('Bỏ thay đổi',QMessageBox.ButtonRole.DestructiveRole)
            dialog.addButton('Huỷ',QMessageBox.ButtonRole.RejectRole)
            dialog.exec()
            if dialog.clickedButton()==save:
                self.save_current(after=action)
                return
            if dialog.clickedButton()!=discard:
                return
            self.doc=None
            self.current_index=-1
            self.files.blockSignals(True)
            self.files.setCurrentRow(-1)
            self.files.blockSignals(False)
            self.canvas.picture.setPixmap(QPixmap())
            self.canvas.image_size=None
        action()

    def export_drag(self,source):
        if self.busy or not self.doc:
            return
        complete=[]
        if not self.save_current(after=lambda:complete.append(self.doc.output)):
            return
        # Wait for the worker without blocking Qt's event processing, then start OLE drag.
        loop=QEventLoop(self)
        timer=QTimer(self)
        timer.setInterval(15)
        timer.timeout.connect(lambda:loop.quit() if not self.busy else None)
        timer.start()
        loop.exec()
        timer.stop()
        timer.deleteLater()
        loop.deleteLater()
        if not complete:
            return
        mime=QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(complete[0].resolve()))])
        drag=QDrag(source)
        drag.setMimeData(mime)
        drag.setPixmap(source.pixmap())
        drag.exec(Qt.DropAction.CopyAction)

    def closeEvent(self,event):
        if self.busy:
            event.ignore()
            self.status.setText('Đợi xử lý xong trước khi đóng')
        elif self.doc and self.doc.dirty:
            event.ignore()
            self.ensure_leave(self.close)
        else:
            event.accept()

if __name__=='__main__':
    application=QApplication(sys.argv)
    application.setStyle('Fusion')
    window=App()
    window.show()
    if '--smoke-test' in sys.argv:
        # Release automation: exercise the frozen runtime without opening user files.
        def smoke_test():
            import json
            from PIL import Image
            try:
                image=Image.new('RGBA',(128,96),(100,120,90,255))
                mask=np.zeros((96,128),np.uint8)
                cv2.circle(mask,(60,40),5,255,-1)
                repaired=heal_region(image,mask)
                rendered=render_image(repaired,{**window.settings,'delete':False})
                window.show_preview(rendered)
                marker=Path(sys.argv[sys.argv.index('--smoke-test')+1])
                marker.write_text(json.dumps({'version':VERSION,'size':rendered.size,'qt':True}),encoding='utf-8')
                window.close()
            except Exception:
                smoke_exception(*sys.exc_info())
                application.exit(1)
        QTimer.singleShot(200,smoke_test)
    sys.exit(application.exec())

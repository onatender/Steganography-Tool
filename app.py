"""Modern PyQt6 desktop interface for image steganography."""
import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QUrl, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QIcon, QImage, QPainter, QPen, QPixmap, QPainterPath
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget, QCheckBox, QLineEdit, QGraphicsOpacityEffect, QScrollArea,
)

from steg_core import StegError, capacity, embed, extract, pack, unpack, is_encrypted

STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #253149; }
QMainWindow, #root { background: #f5f6fb; }
#sidebar { background: #ffffff; border-right: 1px solid #e6e9f2; }
#brand { font-size: 21px; font-weight: 700; color: #202740; }
#brandSub { font-size: 11px; color: #8991a5; }
#eyebrow { font-size: 11px; font-weight: 700; color: #81769c; }
#pageTitle { font-size: 30px; font-weight: 700; color: #202740; }
#subtitle, #muted { color: #7b8499; }
#card { background: white; border: 1px solid #e5e8f1; border-radius: 18px; }
#cardTitle { font-size: 17px; font-weight: 700; color: #202740; }
#step { background: #ede9ff; color: #7057df; border-radius: 12px; font-size: 12px; font-weight: 700; }
#badge { background: #eeeafb; color: #7557d4; border-radius: 10px; padding: 6px 12px; font-size: 11px; font-weight: 600; }
#fileName { font-weight: 600; }
#fileInfo { color: #8b93a7; font-size: 12px; }
#capacityTitle { font-weight: 600; }
#capacityValue { color: #7658d8; font-weight: 600; }
#note { background: #f5f3fc; border-radius: 12px; color: #7e7597; padding: 14px; font-size: 12px; }
#notice { border-radius: 10px; padding: 12px; background: #eeebfb; color: #6b57a0; }
#notice[state="success"] { background: #eaf7ef; color: #27784c; }
#notice[state="error"] { background: #fff0ef; color: #b55150; }
#result { background: #f0f8f3; border-radius: 12px; }
#resultTitle { font-size: 17px; font-weight: 600; color: #28714a; }
QPushButton { background: white; border: 1px solid #e0e4ef; border-radius: 10px; padding: 11px 16px; font-weight: 600; }
QPushButton:hover { background: #f4f1ff; border-color: #bcaeeb; }
QPushButton:pressed { background: #eae4fc; }
QPushButton:disabled { color: #a2a8b9; background: #f1f2f7; border-color: #eaecf3; }
QPushButton#primary { background: #7958dc; border: 1px solid #7958dc; color: white; padding: 14px 20px; }
QPushButton#primary:hover { background: #6846ca; border-color: #6846ca; }
QPushButton#primary:pressed { background: #5b3bb9; }
QPushButton#primary:disabled { background: #d5cbed; border-color: #d5cbed; color: #fdfbff; }
QPushButton#nav { text-align: left; background: transparent; border: none; color: #7a8297; padding: 14px 18px; }
QPushButton#nav:hover { background: #f6f3ff; color: #7653d2; }
QPushButton#nav:checked { background: #efeafb; color: #7550d3; }
#segmented { background: #f2f3f8; border-radius: 11px; }
QPushButton#segment { background: #ffffff; border: 1px solid #e0e4ef; border-radius: 9px; color: #65718a; padding: 11px 16px; }
QPushButton#segment:hover { background: #f7f3ff; border-color: #c6b4ec; color: #6846ca; }
QPushButton#segment:checked { background: #7958dc; color: white; border: 1px solid #7958dc; }
#contentModes { background: #f0f1f7; border: 1px solid #e5e7ef; border-radius: 13px; }
QPlainTextEdit { background: #fafbfe; border: 1px solid #e4e7f0; border-radius: 12px; padding: 14px; font-size: 14px; selection-background-color: #dfd5fc; color: #38435a; }
QPlainTextEdit:focus { border: 1px solid #a58ae7; background: #ffffff; }
QLineEdit { background: #fafbfe; color: #38435a; border: 1px solid #d8dce9; border-radius: 8px; padding: 8px 12px; min-height: 22px; selection-background-color: #dfd5fc; }
QLineEdit:focus { border: 1px solid #a58ae7; background: #ffffff; }
QProgressBar { background: #eeedf5; border: none; border-radius: 4px; min-height: 7px; max-height: 7px; }
QProgressBar::chunk { background: #9679e3; border-radius: 4px; }
QProgressBar[over="true"]::chunk { background: #dc7770; }
QToolTip { background: #283149; color: white; padding: 7px; border: none; }
"""


def icon(kind: str, color: str = "#7958dc", size: int = 24) -> QIcon:
    pixmap = QPixmap(size, size); pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.scale(size / 24, size / 24)
    p.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if kind == "image":
        p.drawRoundedRect(3, 4, 18, 16, 3, 3); p.drawEllipse(7, 7, 3, 3)
        path = QPainterPath(); path.moveTo(4, 18); path.lineTo(10, 12); path.lineTo(14, 16); path.lineTo(17, 13); path.lineTo(21, 17); p.drawPath(path)
    elif kind in ("lock", "unlock"):
        shackle = QPainterPath(); shackle.moveTo(8, 11)
        if kind == "unlock":
            # Keep the left leg attached and lift the right end clear of the body.
            shackle.cubicTo(8, 2, 16, 2, 16, 7)
        else:
            shackle.cubicTo(8, 2, 16, 2, 16, 11)
        p.drawPath(shackle); p.drawRoundedRect(5, 10, 14, 11, 2, 2); p.drawLine(12, 14, 12, 17)
    elif kind == "file":
        path = QPainterPath(); path.moveTo(6, 3); path.lineTo(14, 3); path.lineTo(19, 8); path.lineTo(19, 21); path.lineTo(6, 21); path.closeSubpath()
        p.drawPath(path); p.drawLine(14, 3, 14, 8); p.drawLine(14, 8, 19, 8); p.drawLine(9, 12, 16, 12); p.drawLine(9, 16, 14, 16)
    elif kind == "download":
        p.drawLine(12, 3, 12, 15); p.drawLine(7, 10, 12, 15); p.drawLine(12, 15, 17, 10)
        p.drawLine(4, 16, 4, 21); p.drawLine(4, 21, 20, 21); p.drawLine(20, 21, 20, 16)
    elif kind == "check":
        p.drawEllipse(3, 3, 18, 18); p.drawLine(7, 12, 11, 16); p.drawLine(11, 16, 17, 9)
    elif kind == "text":
        p.drawLine(4, 5, 20, 5); p.drawLine(12, 5, 12, 20); p.drawLine(8, 20, 16, 20)
    p.end(); return QIcon(pixmap)


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    result = QLabel(text); result.setObjectName(name); result.setWordWrap(wrap); result.setTextFormat(Qt.TextFormat.PlainText)
    return result


def button(text, callback, name="", glyph="", white=False):
    result = QPushButton(text); result.setObjectName(name); result.setCursor(Qt.CursorShape.PointingHandCursor)
    if glyph:
        result.setIcon(icon(glyph, "#ffffff" if white else "#7958dc")); result.setIconSize(QSize(19, 19))
    result.clicked.connect(callback); return result


def human_size(value: int) -> str:
    if value < 1024: return f"{value} B"
    if value < 1024 * 1024: return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


class Preview(QWidget):
    dropped = pyqtSignal(str)
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__(); self.setMinimumSize(230, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True); self.setCursor(Qt.CursorShape.PointingHandCursor); self.pixmap = QPixmap()
        self.setToolTip("Choose an image or drag a file here")

    def set_image(self, image):
        self.pixmap = QPixmap.fromImage(image); self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#f8f9fd")); p.setPen(QPen(QColor("#d8dce9"), 1, Qt.PenStyle.DashLine))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 13, 13)
        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(self.rect().adjusted(16, 16, -16, -16).size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled)
        else:
            x, y = self.width() // 2, self.height() // 2 - 34
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#eeebfa")); p.drawRoundedRect(x - 34, y - 34, 68, 68, 20, 20)
            icon("image", "#9c85d7", 36).paint(p, x - 18, y - 18, 36, 36)
            p.setPen(QColor("#65708b")); p.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            p.drawText(self.rect().adjusted(0, 65, 0, 0), Qt.AlignmentFlag.AlignCenter, "Drop an image here")
            p.setPen(QColor("#939bb0")); p.setFont(QFont("Segoe UI", 9))
            p.drawText(self.rect().adjusted(0, 112, 0, 0), Qt.AlignmentFlag.AlignCenter, "or click to browse")
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.clicked.emit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and event.mimeData().urls()[0].isLocalFile(): event.acceptProposedAction()

    def dropEvent(self, event):
        self.dropped.emit(event.mimeData().urls()[0].toLocalFile()); event.acceptProposedAction()


def read_image(path):
    image = QImage(path)
    if image.isNull():
        extension = Path(path).suffix.lower()
        if extension in {".py", ".txt", ".pdf", ".zip", ".rar", ".7z", ".doc", ".docx", ".xlsx", ".exe", ".mp3", ".mp4"}:
            raise StegError(
                f"A {extension} file cannot be used as a carrier image. "
                "First, choose a PNG, JPEG, or BMP image in the Image step. "
                "Then, open the File tab in the Content step and select the file you want to hide."
            )
        raise StegError(
            "Could not open the carrier image. Choose a valid PNG, JPEG, or BMP image. "
            "Choose the file you want to hide in the Content step."
        )
    return image.convertToFormat(QImage.Format.Format_RGBA8888)


def image_bytes(image):
    ptr = image.constBits(); ptr.setsize(image.sizeInBytes()); return bytes(ptr)


class Worker(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, operation, parent, reports_progress=False):
        super().__init__(parent); self.operation = operation; self.reports_progress = reports_progress

    def run(self):
        try: self.completed.emit(self.operation(self.progress.emit) if self.reports_progress else self.operation())
        except Exception as exc: self.failed.emit(str(exc) or "The operation could not be completed.")


class FocusStack(QStackedWidget):
    """Only the visible page determines height; hidden forms add no empty space."""
    def sizeHint(self):
        return self.currentWidget().sizeHint() if self.currentWidget() else super().sizeHint()

    def minimumSizeHint(self):
        return self.currentWidget().minimumSizeHint() if self.currentWidget() else super().minimumSizeHint()

    def hasHeightForWidth(self):
        return bool(self.currentWidget() and self.currentWidget().hasHeightForWidth())

    def heightForWidth(self, width):
        return self.currentWidget().heightForWidth(width) if self.currentWidget() else -1


class ActionCard(QPushButton):
    def __init__(self, title, description, callback, glyph, compact=False):
        super().__init__(); self.setObjectName("actionCard"); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("compact", compact)
        self.clicked.connect(callback)
        layout = QHBoxLayout(self) if compact else QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18); layout.setSpacing(12)
        symbol = QLabel(); symbol.setPixmap(icon(glyph, size=34 if compact else 42).pixmap(34 if compact else 42, 34 if compact else 42))
        layout.addWidget(symbol)
        texts = QVBoxLayout(); texts.setSpacing(7)
        texts.addWidget(label(title, "actionTitle", True)); texts.addWidget(label(description, "actionDescription", True))
        layout.addLayout(texts, 1)
        if not compact:
            layout.addSpacing(8); layout.addWidget(label("Start  →", "actionLink"))
        for child in self.findChildren(QLabel): child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setMinimumHeight(92 if compact else 210)


class StepIndicator(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedHeight(74); self.steps = []; self.position = 0; self.complete = False

    def set_steps(self, steps, position, complete=False):
        self.steps = steps; self.position = position; self.complete = complete; self.update()

    def paintEvent(self, event):
        if not self.steps: return
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width() / len(self.steps); y = 22
        for index in range(len(self.steps) - 1):
            p.setPen(QPen(QColor("#bca7ef" if index < self.position else "#e0e3ed"), 2))
            p.drawLine(int((index + .5) * width + 20), y, int((index + 1.5) * width - 20), y)
        for index, title in enumerate(self.steps):
            x = int((index + .5) * width); done = index < self.position or self.complete; active = index == self.position
            p.setBrush(QColor("#e9f6ef" if done else "#7958dc" if active else "#e9ecf4"))
            p.setPen(QPen(QColor("#218653" if done else "#7958dc" if active else "#e0e3ed"), 2 if done else 1))
            p.drawEllipse(x - 15, y - 15, 30, 30)
            if done:
                p.setPen(QPen(QColor("#187343"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.drawLine(x - 6, y, x - 1, y + 5); p.drawLine(x - 1, y + 5, x + 7, y - 5)
            else:
                p.setPen(QColor("#ffffff" if active else "#9099ae")); p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                p.drawText(x - 15, y - 15, 30, 30, Qt.AlignmentFlag.AlignCenter, str(index + 1))
            p.setPen(QColor("#7958dc" if active else "#516078" if done else "#8b94a7")); p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold if active else QFont.Weight.Normal))
            p.drawText(int(index * width), 45, int(width), 24, Qt.AlignmentFlag.AlignCenter, title)
        p.end()


class ProcessingIcon(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedSize(76, 76); self.angle = 0
        self.timer = QTimer(self); self.timer.setInterval(30); self.timer.timeout.connect(self.tick)

    def tick(self):
        self.angle = (self.angle + 7) % 360; self.update()

    def showEvent(self, event):
        self.timer.start(); super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop(); super().hideEvent(event)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#eee8fc"), 4)); p.drawEllipse(7, 7, 62, 62)
        p.setPen(QPen(QColor("#7958dc"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); p.drawArc(7, 7, 62, 62, -self.angle * 16, 100 * 16)
        icon("image", size=30).paint(p, 23, 23, 30, 30); p.end()


class BaseWindow(QMainWindow):
    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a carrier image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path: self.load_image(path)

    def load_image(self, path):
        if not self.busy: self.start_job(lambda: read_image(path), lambda result: self.image_loaded(path, result), title="Opening image", message="Reading and preparing your image.")

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a file to hide", "", "All files (*)")
        if path:
            try: size = Path(path).stat().st_size
            except OSError as exc: self.show_notice(str(exc), "error"); return
            self.file_path = path; self.payload_name.setText(Path(path).name); self.payload_name.setToolTip(path)
            self.payload_info.setText(human_size(size)); self.file_button.setText("Choose another file"); self.update_capacity()

    def payload_size(self):
        if self.content_mode == 0: return 4 + len(self.editor.toPlainText().encode("utf-8"))
        if self.file_path: return 4 + len(Path(self.file_path).name.encode("utf-8")) + Path(self.file_path).stat().st_size
        return 4

    def show_notice(self, text, state="success"):
        self.notice.setText(text); self.notice.setProperty("state", state)
        self.notice.style().unpolish(self.notice); self.notice.style().polish(self.notice); self.notice.show()

    def start_job(self, operation, success, reports_progress=False, title="Working", message="Preparing your file."):
        if self.busy: return
        self.job_origin = self.step
        self.job_has_progress = reports_progress
        self.show_page("processing"); self.page_title.setText(title); self.subtitle.setText(message)
        self.processing_title.setText(title); self.processing_detail.setText(message)
        self.job_stages.setText("Prepare  →  Embed  →  Save PNG" if title == "Creating hidden image" else "Read image  →  Verify  →  Unlock content" if title == "Unlocking hidden content" else "Your file is being processed on this device")
        self.activity.setRange(0, 100 if reports_progress else 0); self.activity.setValue(0)
        self.processing_percent.setText("0%" if reports_progress else "Please wait")
        self.set_busy(True); self.notice.hide(); self.worker = Worker(operation, self, reports_progress)
        def completed(result):
            self.activity.setRange(0, 100); self.activity.setValue(100)
            self.show_page(self.job_origin); success(result)
        def failed(message):
            self.show_page(self.job_origin); self.show_notice(message, "error")
        self.worker.progress.connect(self.update_job_progress)
        self.worker.completed.connect(completed); self.worker.failed.connect(failed)
        self.worker.finished.connect(lambda: self.set_busy(False)); self.worker.finished.connect(self.worker.deleteLater); self.worker.start()

    def hide_content(self):
        if self.image.isNull(): return
        password = self.encrypt_password.text() if self.encrypt_check.isChecked() else None
        if password is not None and (not password or password != self.confirm_password.text()):
            self.show_notice("The password cannot be empty, and both password fields must match.", "error"); return
        path, _ = QFileDialog.getSaveFileName(self, "Save PNG with hidden content", "hidden-image.png", "PNG image (*.png)")
        if not path: return
        if not path.lower().endswith(".png"):
            path += ".png"
            if Path(path).exists() and QMessageBox.question(self, "File already exists", "Do you want to overwrite this PNG?") != QMessageBox.StandardButton.Yes: return
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(self.image_path)):
            self.show_notice("Choose a different file name to keep the original image unchanged.", "error"); return
        image = self.image.copy(); message = self.editor.toPlainText(); source_file = self.file_path if self.content_mode == 1 else ""
        def operation(report):
            report(0, "Reading file")
            if source_file:
                item = Path(source_file)
                if 4 + len(item.name.encode("utf-8")) + item.stat().st_size > capacity(image.width(), image.height(), password is not None): raise StegError("This file will not fit in the image. Choose a larger image.")
                payload = pack(item.name, item.read_bytes())
            else: payload = pack("", message.encode("utf-8"))
            pixels = embed(image_bytes(image), image.width(), image.height(), payload, password=password, progress=report)
            report(90, "Creating PNG image")
            result = QImage(pixels, image.width(), image.height(), image.width() * 4, QImage.Format.Format_RGBA8888).copy()
            report(95, "Saving PNG to disk")
            if not result.save(path, "PNG"): raise StegError("Could not save the PNG. Check the destination and file permissions.")
            report(100, "Image saved successfully")
            return path
        def success(saved):
            self.encrypt_password.clear(); self.confirm_password.clear()
            self.output_path = saved; self.open_button.show(); self.show_notice("Content hidden. PNG saved: " + saved)
            self.finish_hidden(saved)
        self.start_job(operation, success, reports_progress=True, title="Creating hidden image", message="Preparing your content, embedding it in the image, and saving the PNG.")

    def extract_content(self):
        if self.image.isNull(): return
        password = self.decrypt_password.text() or None
        image = self.image.copy(); self.result_data = None; self.result_stack.setCurrentIndex(0); self.result_actions.hide()
        def operation(report):
            name, data = unpack(extract(image_bytes(image), image.width(), image.height(), password=password, progress=report))
            if not name:
                try: data.decode("utf-8")
                except UnicodeDecodeError as exc: raise StegError("The hidden message is not valid UTF-8 text.") from exc
            return name, data
        def success(result):
            self.decrypt_password.clear()
            name, data = result; self.result_name = name; self.result_data = data
            if name:
                self.extracted_name.setText(name); self.extracted_size.setText(human_size(len(data))); self.result_stack.setCurrentIndex(2)
            else:
                self.extracted_text.setPlainText(data.decode("utf-8")); self.result_stack.setCurrentIndex(1)
            self.copy_button.setVisible(not name); self.result_actions.show(); self.show_notice("Hidden content recovered and verified.")
            self.finish_extracted()
        self.start_job(operation, success, reports_progress=True, title="Unlocking hidden content", message="Reading and verifying the content in your image.")

    def copy_text(self):
        QApplication.clipboard().setText(self.extracted_text.toPlainText()); self.show_notice("Message copied to clipboard.")

    def save_result(self):
        if self.result_data is None: return
        safe_name = self.result_name.replace("\\", "/").split("/")[-1] if self.result_name else "hidden-message.txt"
        safe_name = "".join(c for c in safe_name if c not in '<>:"/\\|?*' and ord(c) >= 32).strip(" .") or "hidden-file.bin"
        path, _ = QFileDialog.getSaveFileName(self, "Save recovered content", safe_name, "All files (*)")
        if path:
            data = self.result_data
            def operation(): Path(path).write_bytes(data); return path
            self.start_job(operation, lambda saved: self.show_notice("Recovered content saved: " + saved))

    def show_output(self):
        if self.output_path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.output_path).parent)))

    def closeEvent(self, event):
        if self.busy: self.show_notice("An operation is still running. Close the window when it is complete.", "info"); event.ignore()
        else: event.accept()


STYLE += """
#wizardHeader { background: #ffffff; border-bottom: 1px solid #e6e9f2; }
#heroTitle { font-size: 34px; font-weight: 700; color: #202740; }
#heroText { font-size: 15px; color: #7b8499; }
#choice { text-align: left; padding: 24px; font-size: 17px; background: white; border-radius: 16px; }
#choice:checked { background: #f0eafb; border: 2px solid #7958dc; color: #6846ca; }
#securityChoice { text-align: left; padding: 14px; font-size: 15px; background: white; border-radius: 14px; }
#securityChoice:checked { background: #f0eafb; border: 2px solid #7958dc; color: #6846ca; }
#stepLabel { color: #9299aa; padding: 8px 5px; font-size: 12px; }
#stepLabel[active="true"] { color: #7958dc; font-weight: 700; }
#summary { background: #f7f8fc; border-radius: 12px; padding: 16px; font-size: 14px; }
#actionCard { text-align: left; background: #ffffff; border: 1px solid #dedfed; border-radius: 16px; padding: 0; }
#actionCard:hover { background: #faf8ff; border: 1px solid #a88de9; }
#actionCard:checked { background: #f4efff; border: 2px solid #7958dc; }
#actionCard:focus { border: 2px solid #a88de9; }
#actionCard QLabel { background: transparent; border: none; }
#actionTitle { font-size: 19px; font-weight: 700; color: #26324a; }
QPushButton[compact="true"] #actionTitle { font-size: 16px; }
#actionDescription { font-size: 13px; color: #77829a; }
#actionLink { color: #7958dc; font-size: 13px; font-weight: 700; }
#introBadge { color: #7958dc; background: #ede6fc; border-radius: 7px; padding: 5px 9px; font-size: 10px; font-weight: 700; }
#featureRow { background: #edf0f8; border-radius: 10px; }
#feature { color: #69758f; font-size: 12px; padding: 10px; }
#processingTitle { font-size: 21px; font-weight: 700; }
#processingPercent { color: #7958dc; font-weight: 700; font-size: 23px; }
QProgressBar#jobProgress { min-height: 12px; max-height: 12px; border-radius: 6px; background: #ede8f7; }
QProgressBar#jobProgress::chunk { border-radius: 6px; background: #7958dc; }
#jobStages { background: #f5f6fb; border-radius: 12px; padding: 13px; color: #758098; }
#heroTitle { font-size: 28px; }
#heroText { font-size: 13px; }
#bottomBar { background: #ffffff; border-top: 1px solid #e6e9f2; }
"""


class MainWindow(BaseWindow):
    """A focused wizard; the codec and background operations stay shared."""

    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("BuryIt")
        self.setWindowIcon(icon("lock", size=64)); self.resize(900, 750); self.setMinimumSize(740, 650)
        self.image = QImage(); self.image_path = ""; self.file_path = ""; self.mode = 0; self.content_mode = 1
        self.busy = False; self.worker = None; self.result_data = None; self.result_name = ""; self.output_path = ""
        self.step = "welcome"; self.security_choice = None; self.encrypted_input = False
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        header = QFrame(); header.setObjectName("wizardHeader"); bar = QHBoxLayout(header); bar.setContentsMargins(30, 18, 30, 18)
        logo = QLabel(); logo.setPixmap(icon("lock", size=30).pixmap(30, 30)); bar.addWidget(logo)
        bar.addWidget(label("BuryIt", "brand")); bar.addStretch(); bar.addWidget(label("PRIVATE BY DESIGN", "eyebrow")); outer.addWidget(header)
        area = QScrollArea(); area.setWidgetResizable(True); area.setFrameShape(QFrame.Shape.NoFrame); outer.addWidget(area, 1)
        content = QWidget(); content.setObjectName("root"); area.setWidget(content)
        centering = QHBoxLayout(content); centering.setContentsMargins(26, 22, 26, 22)
        workspace = QWidget(); workspace.setMaximumWidth(780); centering.addStretch(); centering.addWidget(workspace, 1); centering.addStretch()
        body = QVBoxLayout(workspace); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(12); body.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.stepper = StepIndicator()
        body.addWidget(self.stepper)
        self.heading_panel = QWidget(); heading = QVBoxLayout(self.heading_panel); heading.setContentsMargins(0, 0, 0, 8); heading.setSpacing(6)
        self.page_title = label("", "heroTitle", True); heading.addWidget(self.page_title)
        self.subtitle = label("", "heroText", True); heading.addWidget(self.subtitle); body.addWidget(self.heading_panel)
        self.pages = FocusStack(); self.pages.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        body.addWidget(self.pages); self.page_map = {}
        self.make_welcome(); self.make_image_step(); self.make_content_step(); self.make_security_step(); self.make_review_step(); self.make_unlock_step(); self.make_result_step(); self.make_processing_step()
        self.notice = label("", "notice", True); self.notice.hide(); body.addWidget(self.notice)
        body.addStretch(1)
        self.navigation_widget = QWidget(); self.navigation_widget.setObjectName("bottomBar")
        navigation = QHBoxLayout(self.navigation_widget); navigation.setContentsMargins(32, 12, 32, 12)
        self.back_button = button("← Geri", self.go_back); navigation.addWidget(self.back_button)
        navigation.addStretch(); self.progress_text = label("", "muted"); navigation.addWidget(self.progress_text); navigation.addSpacing(12)
        self.next_button = button("Devam et →", self.go_next, "primary"); navigation.addWidget(self.next_button); outer.addWidget(self.navigation_widget)
        footer = label("Your files stay on this device. You can change your choices at any step.", "fileInfo", True)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter); footer.setContentsMargins(20, 0, 20, 16); outer.addWidget(footer)
        self.fade = QGraphicsOpacityEffect(self.pages); self.pages.setGraphicsEffect(self.fade)
        self.transition = QPropertyAnimation(self.fade, b"opacity", self); self.transition.setDuration(230)
        self.transition.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.show_page("welcome", animate=False)

    def page(self, key):
        frame = QFrame(); frame.setObjectName("card"); layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 20, 22, 20); layout.setSpacing(12); layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.page_map[key] = self.pages.addWidget(frame)
        return layout

    def choice(self, title, description, callback, glyph, compact=False):
        return ActionCard(title, description, callback, glyph, compact)

    def make_welcome(self):
        layout = self.page("welcome"); layout.setSpacing(18)
        badge = label("HIDE DATA IN PLAIN SIGHT", "introBadge"); layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(label("Keep your files hidden.\nStay in control.", "heroTitle", True))
        layout.addWidget(label("Hide a file inside an image or recover content already stored there. Choose what you want to do to get started.", "heroText", True))
        choices = QHBoxLayout(); choices.setSpacing(14)
        self.hide_choice = self.choice("Hide data", "Hide a file or message in an image. Add password protection if you like.", lambda: self.set_mode(0), "lock")
        self.extract_choice = self.choice("Recover data", "Retrieve a file or message from a PNG that contains hidden data.", lambda: self.set_mode(1), "unlock")
        choices.addWidget(self.hide_choice, 1); choices.addWidget(self.extract_choice, 1); layout.addLayout(choices)
        features = QFrame(); features.setObjectName("featureRow"); row = QHBoxLayout(features); row.setContentsMargins(4, 0, 4, 0)
        for text in ("✓  Runs on your device", "✓  Optional AES encryption", "✓  Guided steps"):
            row.addWidget(label(text, "feature"), 1)
        layout.addWidget(features)

    def make_image_step(self):
        layout = self.page("image")
        self.preview = Preview(); self.preview.setMinimumHeight(180); self.preview.setMaximumHeight(210)
        self.preview.clicked.connect(self.choose_image); self.preview.dropped.connect(self.load_image); layout.addWidget(self.preview)
        self.image_name = label("No image selected yet", "fileName", True); self.image_info = label("PNG, JPEG, or BMP", "fileInfo")
        layout.addWidget(self.image_name); layout.addWidget(self.image_info)
        self.choose_button = button("Choose image", self.choose_image, glyph="image"); layout.addWidget(self.choose_button)
        self.image_help = label("", "note", True); layout.addWidget(self.image_help); layout.addStretch()

    def make_content_step(self):
        layout = self.page("content"); modes = QFrame(); modes.setObjectName("contentModes")
        tabs = QHBoxLayout(modes); tabs.setContentsMargins(5, 5, 5, 5); tabs.setSpacing(7); self.content_group = QButtonGroup(self)
        self.file_tab = button("Hide a file", lambda: self.set_content(1), "segment", "file")
        self.text_tab = button("Write a message", lambda: self.set_content(0), "segment", "text")
        for index, tab in ((1, self.file_tab), (0, self.text_tab)):
            tab.setObjectName("segment"); tab.setCheckable(True); self.content_group.addButton(tab, index); tabs.addWidget(tab, 1)
        self.file_tab.setChecked(True); layout.addWidget(modes); self.content_stack = QStackedWidget()
        text_panel = QWidget(); text_layout = QVBoxLayout(text_panel); text_layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit(); self.editor.setPlaceholderText("Type the message you want to hide…")
        self.editor.setMinimumHeight(140); self.editor.textChanged.connect(self.update_capacity); text_layout.addWidget(self.editor)
        self.text_count = label("", "fileInfo"); text_layout.addWidget(self.text_count); self.content_stack.addWidget(text_panel)
        file_panel = QWidget(); file_layout = QVBoxLayout(file_panel); file_layout.setContentsMargins(0, 16, 0, 16); file_layout.addStretch()
        glyph = QLabel(); glyph.setPixmap(icon("file", size=50).pixmap(50, 50)); glyph.setAlignment(Qt.AlignmentFlag.AlignCenter); file_layout.addWidget(glyph)
        self.payload_name = label("Which file would you like to hide?", "fileName", True); self.payload_name.setAlignment(Qt.AlignmentFlag.AlignCenter); file_layout.addWidget(self.payload_name)
        self.payload_info = label("Choose a PDF, ZIP, Python file, or any other file.", "fileInfo", True); self.payload_info.setAlignment(Qt.AlignmentFlag.AlignCenter); file_layout.addWidget(self.payload_info)
        self.file_button = button("Choose a file to hide", self.choose_file, glyph="file"); file_layout.addWidget(self.file_button); file_layout.addStretch()
        self.content_stack.addWidget(file_panel); self.content_stack.setCurrentIndex(1); self.content_stack.setMinimumHeight(200); self.content_stack.setMaximumHeight(250); layout.addWidget(self.content_stack)
        row = QHBoxLayout(); row.addWidget(label("Image capacity", "fileName")); row.addStretch(); self.capacity_value = label("", "capacityValue"); row.addWidget(self.capacity_value); layout.addLayout(row)
        self.capacity_bar = QProgressBar(); self.capacity_bar.setRange(0, 100); self.capacity_bar.setTextVisible(False); layout.addWidget(self.capacity_bar)
        self.capacity_detail = label("", "fileInfo", True); layout.addWidget(self.capacity_detail)

    def password_field(self, layout, title, hint):
        caption = label(title, "fileName"); layout.addWidget(caption)
        field = QLineEdit(); field.setEchoMode(QLineEdit.EchoMode.Password); field.setPlaceholderText(hint); caption.setBuddy(field)
        layout.addWidget(field); return field

    def make_security_step(self):
        layout = self.page("security")
        self.secure_choice = self.choice("Protect with a password", "Only someone with the password can open the content.", lambda: self.choose_security(True), "lock", compact=True)
        self.plain_choice = self.choice("Continue without a password", "The content will be hidden, but no password will be needed to recover it.", lambda: self.choose_security(False), "unlock", compact=True)
        self.security_group = QButtonGroup(self)
        choices = QHBoxLayout(); choices.setSpacing(12)
        for item in (self.secure_choice, self.plain_choice):
            item.setCheckable(True); self.security_group.addButton(item); choices.addWidget(item, 1)
        layout.addLayout(choices)
        self.encrypt_check = QCheckBox(); self.encrypt_check.hide(); self.encrypt_check.toggled.connect(self.encryption_changed)
        self.encryption_fields = QWidget(); fields = QVBoxLayout(self.encryption_fields); fields.setContentsMargins(0, 0, 0, 0); fields.setSpacing(7)
        self.encrypt_password = self.password_field(fields, "Password", "Create a password")
        self.confirm_password = self.password_field(fields, "Confirm password", "Enter the same password again")
        for field in (self.encrypt_password, self.confirm_password): field.textChanged.connect(self.update_capacity)
        self.password_feedback = label("", "fileInfo", True); fields.addWidget(self.password_feedback)
        fields.addWidget(label("Keep your password safe. If you lose it, the content cannot be recovered.", "muted", True))
        self.encryption_fields.hide(); layout.addWidget(self.encryption_fields)

    def make_review_step(self):
        layout = self.page("review"); layout.addWidget(label("Ready to go", "cardTitle"))
        self.summary = label("", "summary", True); layout.addWidget(self.summary)
        layout.addWidget(label("The output is saved as a PNG. Share the original file without resizing it or converting it to JPEG.", "note", True))
        self.hide_button = button("Hide data and save PNG", self.hide_content, "primary", "download", True); layout.addWidget(self.hide_button)

    def make_unlock_step(self):
        layout = self.page("unlock")
        layout.addWidget(label("The content in this image is password protected.", "cardTitle", True))
        self.decrypt_password = self.password_field(layout, "Password", "Enter the password used when hiding the data")
        self.decrypt_password.textChanged.connect(self.update_capacity)
        layout.addWidget(label("Enter the correct password to unlock your file or message.", "note", True))
        self.extract_button = button("Unlock content", self.extract_content, "primary", "unlock", True); layout.addWidget(self.extract_button)

    def make_result_step(self):
        layout = self.page("result"); self.result_stack = QStackedWidget()
        self.hidden_result = label("", "summary", True); self.result_stack.addWidget(self.hidden_result)
        self.extracted_text = QPlainTextEdit(); self.extracted_text.setReadOnly(True); self.extracted_text.setMinimumHeight(200); self.result_stack.addWidget(self.extracted_text)
        file_panel = QWidget(); file_layout = QVBoxLayout(file_panel); file_layout.addStretch()
        glyph = QLabel(); glyph.setPixmap(icon("check", "#4b9870", 56).pixmap(56, 56)); glyph.setAlignment(Qt.AlignmentFlag.AlignCenter); file_layout.addWidget(glyph)
        self.extracted_name = label("", "cardTitle", True); self.extracted_name.setAlignment(Qt.AlignmentFlag.AlignCenter); file_layout.addWidget(self.extracted_name)
        self.extracted_size = label("", "fileInfo"); self.extracted_size.setAlignment(Qt.AlignmentFlag.AlignCenter); file_layout.addWidget(self.extracted_size); file_layout.addStretch()
        self.result_stack.addWidget(file_panel); layout.addWidget(self.result_stack, 1)
        self.result_actions = QWidget(); actions = QHBoxLayout(self.result_actions); actions.setContentsMargins(0, 0, 0, 0)
        self.copy_button = button("Metni kopyala", self.copy_text, glyph="text"); actions.addWidget(self.copy_button)
        actions.addWidget(button("Save file", self.save_result, "primary", "download", True)); self.result_actions.hide(); layout.addWidget(self.result_actions)
        self.open_button = button("Open saved PNG folder", self.show_output, glyph="file"); self.open_button.hide(); layout.addWidget(self.open_button)

    def make_processing_step(self):
        layout = self.page("processing"); layout.setSpacing(16)
        top = QHBoxLayout(); top.setSpacing(18); self.processing_icon = ProcessingIcon(); top.addWidget(self.processing_icon)
        text = QVBoxLayout(); text.setSpacing(6)
        self.processing_title = label("Creating your image", "processingTitle", True)
        self.processing_detail = label("Preparing your content", "heroText", True)
        text.addWidget(self.processing_title); text.addWidget(self.processing_detail); top.addLayout(text, 1); layout.addLayout(top)
        progress = QHBoxLayout(); progress.addWidget(label("PROGRESS", "eyebrow")); progress.addStretch()
        self.processing_percent = label("0%", "processingPercent"); progress.addWidget(self.processing_percent); layout.addLayout(progress)
        self.activity = QProgressBar(); self.activity.setObjectName("jobProgress"); self.activity.setRange(0, 100); self.activity.setTextVisible(False); layout.addWidget(self.activity)
        self.job_stages = label("Prepare  →  Embed  →  Save PNG", "jobStages", True); layout.addWidget(self.job_stages)
        layout.addWidget(label("Your image is being created. The result will appear here when it is ready.", "muted", True))

    def update_job_progress(self, percent, message):
        self.activity.setRange(0, 100); self.activity.setValue(max(self.activity.value(), min(100, percent)))
        self.processing_percent.setText(f"{self.activity.value()}%"); self.processing_detail.setText(message)

    def show_page(self, key, animate=True):
        self.step = key; self.pages.setCurrentIndex(self.page_map[key]); self.pages.updateGeometry(); self.notice.hide()
        self.heading_panel.setVisible(key not in ("welcome", "processing"))
        self.navigation_widget.setVisible(key not in ("welcome", "processing"))
        titles = {
            "welcome": ("What would you like to do?", "Choose an action to get started. We will guide you through each step."),
            "image": ("Choose an image" if self.mode == 0 else "Choose the PNG with hidden data", "First, choose the image for this operation."),
            "content": ("What would you like to hide?", "Choose a file or write a short message."),
            "security": ("Add password protection?", "Optionally encrypt your content with AES before hiding it."),
            "review": ("Review your choices", "Check the details, then save your image."),
            "unlock": ("Unlock your content", "Enter the password you chose when hiding the content."),
            "result": ("Your image is ready" if self.mode == 0 else "Your content is ready", "The operation is complete. Your files stay on this device."),
            "processing": ("Working on it", "Preparing your content."),
        }
        title, subtitle = titles[key]; self.page_title.setText(title); self.subtitle.setText(subtitle)
        steps = ["Image", "Content", "Protection", "Save"] if self.mode == 0 else ["Image", "Unlock", "Result"]
        position = ({"image": 0, "content": 1, "security": 2, "review": 3, "result": 3} if self.mode == 0 else {"image": 0, "unlock": 1, "result": 2}).get(key, 0)
        if key == "processing":
            position = (3 if self.mode == 0 else 1) if getattr(self, "job_has_progress", False) else ({"image": 0, "content": 1, "security": 2, "review": 3, "unlock": 1, "result": len(steps) - 1}).get(getattr(self, "job_origin", "image"), 0)
        self.stepper.setVisible(key != "welcome"); self.stepper.set_steps(steps, position, key == "result")
        self.progress_text.setText("" if key == "welcome" else f"Step {position + 1} of {len(steps)}")
        self.back_button.setVisible(key not in ("welcome", "result")); self.next_button.setVisible(key not in ("welcome", "review", "unlock"))
        self.next_button.setText("Start another operation" if key == "result" else "Continue →")
        self.image_help.setText("This image will carry your content. Choose a PNG, JPEG, or BMP; the output will be a PNG." if self.mode == 0 else "Choose the original PNG that contains the hidden data. Screenshots and resized copies will not work.")
        if key == "review": self.refresh_summary()
        self.update_capacity()
        if animate:
            self.transition.stop(); self.transition.setStartValue(0.25); self.transition.setEndValue(1.0); self.transition.start()
        else: self.fade.setOpacity(1.0)
        if key == "unlock": self.decrypt_password.setFocus()
        QTimer.singleShot(0, self.fit_page)

    def fit_page(self):
        """Reserve exactly the visible content height, including wrapped text."""
        width = max(300, self.pages.width())
        page = self.pages.currentWidget()
        page.layout().activate()
        height = page.layout().heightForWidth(width)
        self.pages.setFixedHeight(max(page.minimumSizeHint().height(), height if height >= 0 else page.sizeHint().height()))
        heading = self.heading_panel.layout().heightForWidth(width)
        self.heading_panel.setFixedHeight(heading if heading >= 0 else self.heading_panel.sizeHint().height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "pages"): QTimer.singleShot(0, self.fit_page)

    def set_mode(self, mode):
        if self.busy: return
        self.mode = mode; self.reset_session(); self.show_page("image")

    def reset_session(self):
        self.image = QImage(); self.image_path = ""; self.file_path = ""; self.output_path = ""; self.result_data = None; self.result_name = ""
        self.preview.set_image(self.image); self.image_name.setText("No image selected yet"); self.image_info.setText("PNG, JPEG, or BMP" if self.mode == 0 else "Original PNG")
        self.choose_button.setText("Choose image"); self.payload_name.setText("Which file would you like to hide?"); self.payload_info.setText("Choose a PDF, ZIP, Python file, or any other file.")
        self.editor.clear(); self.encrypt_password.clear(); self.confirm_password.clear(); self.decrypt_password.clear(); self.encrypt_check.setChecked(False)
        self.security_choice = None; self.security_group.setExclusive(False)
        for item in (self.secure_choice, self.plain_choice): item.setChecked(False)
        self.security_group.setExclusive(True); self.result_actions.hide(); self.open_button.hide(); self.encrypted_input = False
        self.set_content(1); self.result_stack.setCurrentIndex(0)

    def set_content(self, mode):
        if self.busy: return
        self.content_mode = mode; self.content_stack.setCurrentIndex(mode); self.content_group.button(mode).setChecked(True)
        self.update_capacity()

    def choose_security(self, enabled):
        if self.busy: return
        self.security_choice = enabled; self.encrypt_check.setChecked(enabled)
        self.secure_choice.setChecked(enabled); self.plain_choice.setChecked(not enabled)
        self.update_capacity()
        if enabled: self.encrypt_password.setFocus()

    def encryption_changed(self, enabled):
        self.encryption_fields.setVisible(enabled); self.pages.updateGeometry(); self.update_capacity()
        QTimer.singleShot(0, self.fit_page)

    def image_loaded(self, path, image):
        self.image = image; self.image_path = path; self.preview.set_image(image)
        self.image_name.setText(Path(path).name); self.image_name.setToolTip(path)
        self.image_info.setText(f"{image.width():,} × {image.height():,} piksel · {Path(path).suffix.upper().lstrip('.')}")
        self.choose_button.setText("Choose another image"); self.result_data = None; self.result_actions.hide(); self.notice.hide(); self.update_capacity()

    def refresh_summary(self):
        name = Path(self.file_path).name if self.content_mode == 1 else "Your message"
        self.summary.setText(f"Image\n{Path(self.image_path).name}\n\nContent\n{name} · {human_size(self.payload_size())}\n\nProtection\n{'AES-256 · Password protected' if self.encrypt_check.isChecked() else 'No password'}")

    def update_capacity(self):
        if not hasattr(self, "next_button"): return
        text = self.editor.toPlainText(); self.text_count.setText(f"{len(text):,} karakter · {human_size(len(text.encode('utf-8')))}")
        available = capacity(self.image.width(), self.image.height(), self.encrypt_check.isChecked()) if not self.image.isNull() else 0
        try: used = self.payload_size()
        except OSError: used = available + 1
        has_content = bool(text) if self.content_mode == 0 else bool(self.file_path)
        fits = has_content and used <= available; password = self.encrypt_password.text()
        valid_password = not self.encrypt_check.isChecked() or (bool(password) and password == self.confirm_password.text())
        self.capacity_value.setText(human_size(max(0, available - 4)))
        ratio = min(100, round(used / available * 100)) if available and has_content else 0; self.capacity_bar.setValue(ratio)
        self.capacity_detail.setText("This content will not fit. Go back and choose a larger image." if has_content and not fits else f"{human_size(used)} used · {ratio}% full" if has_content else "Choose a file or write a message.")
        self.password_feedback.setText("Create a password." if not password else "Passwords do not match." if password != self.confirm_password.text() else "Passwords match. You can continue.")
        if has_content and not fits:
            self.password_feedback.setText("There is not enough room for encryption. Choose a larger image or continue without a password.")
        allowed = {"welcome": True, "image": not self.image.isNull(), "content": fits, "security": self.security_choice is not None and valid_password and fits, "review": fits and valid_password, "unlock": bool(self.decrypt_password.text()), "result": True}
        self.next_button.setEnabled(not self.busy and allowed.get(self.step, False))
        self.hide_button.setEnabled(not self.busy and not self.image.isNull() and fits and valid_password)
        self.extract_button.setEnabled(not self.busy and not self.image.isNull() and bool(self.decrypt_password.text()))
        self.back_button.setEnabled(not self.busy)

    def go_next(self):
        if self.busy or not self.next_button.isEnabled(): return
        if self.step == "image":
            if self.mode == 0: self.show_page("content")
            else:
                try: self.encrypted_input = is_encrypted(image_bytes(self.image), self.image.width(), self.image.height())
                except StegError as exc: self.show_notice(str(exc), "error"); return
                if self.encrypted_input: self.show_page("unlock")
                else: self.extract_content()
        elif self.step == "content": self.show_page("security")
        elif self.step == "security": self.show_page("review")
        elif self.step == "result": self.reset_session(); self.show_page("welcome")

    def go_back(self):
        if self.busy: return
        previous = {"image": "welcome", "content": "image", "security": "content", "review": "security", "unlock": "image"}
        if self.step in previous:
            self.show_page(previous[self.step])
            if self.step == "image": self.decrypt_password.clear()

    def set_busy(self, busy):
        self.busy = busy
        for widget in (self.choose_button, self.preview, self.content_stack, self.text_tab, self.file_tab, self.encrypt_password, self.confirm_password, self.decrypt_password, self.secure_choice, self.plain_choice, self.hide_choice, self.extract_choice, self.result_actions, self.open_button):
            widget.setEnabled(not busy)
        self.update_capacity()

    def finish_hidden(self, path):
        self.hidden_result.setText("Your content was hidden in the image.\n\n" + path)
        self.result_stack.setCurrentIndex(0); self.show_page("result")

    def finish_extracted(self):
        self.show_page("result")


def main():
    app = QApplication(sys.argv); app.setStyle("Fusion"); app.setFont(QFont("Segoe UI", 10)); app.setStyleSheet(STYLE)
    window = MainWindow(); window.show()
    if "--screenshot" in sys.argv:
        destination = sys.argv[sys.argv.index("--screenshot") + 1]
        def capture(): window.grab().save(destination); app.quit()
        QTimer.singleShot(800, capture)
    return app.exec()


if __name__ == "__main__": sys.exit(main())

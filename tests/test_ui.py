"""Qt integration checks; run after installing requirements."""
import os
import tempfile
import unittest
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication
from app import MainWindow, STYLE, image_bytes, read_image
from steg_core import StegError, embed, extract, pack, unpack


class QtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([]); cls.app.setStyleSheet(STYLE)

    def setUp(self): self.window = MainWindow()
    def tearDown(self): self.window.close()

    def wait_job(self):
        loop = QEventLoop(); self.window.worker.finished.connect(loop.quit); QTimer.singleShot(5000, loop.quit); loop.exec()
        QApplication.processEvents(); self.assertFalse(self.window.busy)

    def test_empty_state_and_mode_switch(self):
        self.assertFalse(self.window.hide_button.isEnabled()); self.assertFalse(self.window.extract_button.isEnabled())
        self.assertEqual(self.window.step, "welcome")
        self.window.set_mode(1); self.assertEqual(self.window.step, "image"); self.assertEqual(self.window.mode, 1)
        self.window.set_content(1); self.assertEqual(self.window.content_stack.currentIndex(), 1)

    def test_png_roundtrip_and_extraction_ui(self):
        image = QImage(100, 100, QImage.Format.Format_RGBA8888); image.fill(QColor(80, 150, 190, 127))
        for name, data in [("", "Gizli mesaj 🌿".encode()), ("örnek.bin", bytes(range(256))), ("ornek.py", b'print("Merhaba")\n')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                pixels = embed(image_bytes(image), 100, 100, pack(name, data))
                encoded = QImage(pixels, 100, 100, 400, QImage.Format.Format_RGBA8888).copy()
                path = str(Path(temp) / "hidden.png"); self.assertTrue(encoded.save(path, "PNG"))
                reloaded = QImage(path).convertToFormat(QImage.Format.Format_RGBA8888)
                self.assertEqual(unpack(extract(image_bytes(reloaded), 100, 100)), (name, data))
                self.window.set_mode(1); self.window.image_loaded(path, reloaded); self.window.go_next(); self.wait_job()
                self.assertEqual(self.window.result_data, data); self.assertEqual(self.window.result_name, name)
                self.assertEqual(self.window.result_stack.currentIndex(), 2 if name else 1); self.assertEqual(self.window.step, "result")

    def test_python_file_is_payload_not_carrier(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ornek.py"
            path.write_text('print("Merhaba")\n', encoding="utf-8")
            with self.assertRaisesRegex(StegError, "Content step"):
                read_image(str(path))
            image = QImage(100, 100, QImage.Format.Format_RGBA8888)
            image.fill(QColor("#8075ad"))
            self.window.image_loaded("carrier.png", image)
            self.window.file_path = str(path)
            self.window.set_content(1)
            self.assertTrue(self.window.hide_button.isEnabled())

    def test_capacity_and_busy_state(self):
        self.window.set_mode(0); self.window.set_content(0)
        image = QImage(30, 30, QImage.Format.Format_RGBA8888); image.fill(QColor("#8075ad")); self.window.image_loaded("example.png", image)
        self.window.editor.setPlainText("Merhaba"); self.assertTrue(self.window.hide_button.isEnabled())
        self.window.editor.setPlainText("x" * 400); self.assertFalse(self.window.hide_button.isEnabled())
        self.window.editor.setPlainText("Merhaba"); self.window.set_busy(True)
        self.assertFalse(self.window.hide_button.isEnabled()); self.assertFalse(self.window.choose_button.isEnabled())
        self.window.set_busy(False); self.assertTrue(self.window.hide_button.isEnabled())

    def test_encryption_controls_and_encrypted_png(self):
        self.window.set_mode(0); self.window.set_content(0)
        image = QImage(100, 100, QImage.Format.Format_RGBA8888); image.fill(QColor("#8075ad"))
        self.window.image_loaded("carrier.png", image); self.window.editor.setPlainText("Merhaba")
        self.window.choose_security(True)
        self.assertFalse(self.window.hide_button.isEnabled())
        self.window.encrypt_password.setText("secret"); self.window.confirm_password.setText("wrong")
        self.assertFalse(self.window.hide_button.isEnabled())
        self.window.confirm_password.setText("secret"); self.assertTrue(self.window.hide_button.isEnabled())
        self.window.set_busy(True); self.assertFalse(self.window.encrypt_password.isEnabled()); self.window.set_busy(False)
        with tempfile.TemporaryDirectory() as temp:
            from unittest.mock import patch
            path = str(Path(temp) / "encrypted.png")
            with patch("app.QFileDialog.getSaveFileName", return_value=(path, "")):
                self.window.hide_content(); self.wait_job()
            self.assertTrue(Path(path).exists()); self.assertEqual(self.window.encrypt_password.text(), "")
            self.window.set_mode(1); self.window.image_loaded(path, read_image(path)); self.window.go_next()
            self.assertEqual(self.window.step, "unlock")
            for password in ("", "wrong"):
                self.window.decrypt_password.setText(password); self.window.extract_content(); self.wait_job()
                self.assertIsNone(self.window.result_data); self.assertFalse(self.window.result_actions.isVisible())
            self.window.decrypt_password.setText("secret"); self.window.extract_content(); self.wait_job()
            self.assertEqual(self.window.result_data, b"Merhaba"); self.assertEqual(self.window.decrypt_password.text(), "")

    def test_guided_steps_backtracking_and_reset(self):
        w = self.window; w.show(); QApplication.processEvents()
        self.assertFalse(w.encrypt_password.isVisible()); self.assertFalse(w.preview.isVisible())
        w.set_mode(0); self.assertEqual(w.step, "image"); self.assertFalse(w.next_button.isEnabled())
        image = QImage(100, 100, QImage.Format.Format_RGBA8888); image.fill(QColor("#8075ad"))
        w.image_loaded("carrier.png", image); w.go_next(); self.assertEqual(w.step, "content")
        self.assertFalse(w.preview.isVisible()); self.assertFalse(w.encrypt_password.isVisible())
        self.assertFalse(w.next_button.isEnabled()); w.set_content(0); w.editor.setPlainText("Merhaba")
        w.go_next(); self.assertEqual(w.step, "security"); self.assertFalse(w.editor.isVisible())
        self.assertFalse(w.next_button.isEnabled()); w.choose_security(True)
        w.encrypt_password.setText("secret"); w.confirm_password.setText("secret"); w.go_next()
        self.assertEqual(w.step, "review"); self.assertIn("AES-256", w.summary.text())
        w.go_back(); self.assertEqual(w.step, "security"); self.assertEqual(w.encrypt_password.text(), "secret")
        w.go_back(); self.assertEqual(w.editor.toPlainText(), "Merhaba")
        w.go_back(); self.assertFalse(w.image.isNull())
        w.go_back(); self.assertEqual(w.step, "welcome"); w.set_mode(1)
        self.assertTrue(w.image.isNull()); self.assertEqual(w.encrypt_password.text(), ""); self.assertEqual(w.editor.toPlainText(), "")

    def test_plain_flow_cancel_then_save_file_and_new_operation(self):
        from unittest.mock import patch
        w = self.window; w.set_mode(0)
        image = QImage(100, 100, QImage.Format.Format_RGBA8888); image.fill(QColor("#8075ad"))
        w.image_loaded("carrier.png", image); w.go_next()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "örnek.bin"; source.write_bytes(bytes(range(256)))
            with patch("app.QFileDialog.getOpenFileName", return_value=(str(source), "")): w.choose_file()
            w.go_next(); w.choose_security(False); w.go_next(); self.assertEqual(w.step, "review")
            with patch("app.QFileDialog.getSaveFileName", return_value=("", "")): w.hide_content()
            self.assertFalse(w.busy); self.assertEqual(w.step, "review")
            path = str(Path(temp) / "hidden.png")
            with patch("app.QFileDialog.getSaveFileName", return_value=(path, "")): w.hide_content(); self.wait_job()
            self.assertEqual(w.step, "result"); self.assertEqual(w.output_path, path)
            w.go_next(); self.assertEqual(w.step, "welcome"); self.assertTrue(w.image.isNull())
            w.set_mode(1); w.image_loaded(path, read_image(path)); w.go_next(); self.wait_job()
            self.assertEqual(w.step, "result"); self.assertEqual(w.result_data, bytes(range(256)))
            restored = str(Path(temp) / "restored.bin")
            with patch("app.QFileDialog.getSaveFileName", return_value=(restored, "")): w.save_result(); self.wait_job()
            self.assertEqual(Path(restored).read_bytes(), source.read_bytes())

    def test_invalid_image_and_encryption_overhead_block_progress(self):
        w = self.window; w.set_mode(1)
        image = QImage(30, 30, QImage.Format.Format_RGBA8888); image.fill(QColor("#8075ad"))
        w.image_loaded("empty.png", image); w.go_next()
        self.assertEqual(w.step, "image"); self.assertIsNone(w.worker); self.assertIn("No hidden data was found", w.notice.text())
        w.set_mode(0); w.image_loaded("carrier.png", image); w.go_next(); w.set_content(0)
        w.editor.setPlainText("x" * 280); w.go_next(); self.assertEqual(w.step, "security")
        w.choose_security(True); w.encrypt_password.setText("secret"); w.confirm_password.setText("secret")
        self.assertFalse(w.next_button.isEnabled()); w.choose_security(False); self.assertTrue(w.next_button.isEnabled())
        w.set_busy(True); w.go_back(); self.assertEqual(w.step, "security"); self.assertFalse(w.back_button.isEnabled())
        w.set_busy(False)

    def test_processing_feedback_and_failure_recovery(self):
        import threading
        w = self.window; w.show(); w.set_mode(0); gate = threading.Event()
        def operation(report):
            report(37, "Embedding content in the image")
            gate.wait(3)
            raise StegError("Saving failed")
        w.start_job(operation, lambda result: self.fail("Failure must not complete"), reports_progress=True, title="Creating hidden image")
        loop = QEventLoop(); QTimer.singleShot(100, loop.quit); loop.exec()
        try:
            self.assertEqual(w.step, "processing"); self.assertTrue(w.busy)
            self.assertEqual(w.activity.value(), 37); self.assertEqual(w.processing_percent.text(), "%37")
            self.assertIn("Embedding", w.processing_detail.text()); self.assertFalse(w.next_button.isVisible())
            self.assertTrue(w.processing_icon.timer.isActive())
        finally: gate.set()
        self.wait_job(); self.assertEqual(w.step, "image"); self.assertIn("Saving failed", w.notice.text())
        self.assertFalse(w.processing_icon.timer.isActive()); self.assertTrue(w.choose_button.isEnabled())


if __name__ == "__main__": unittest.main()

import mss
import mss.tools
import time
import os
from PIL import Image
import pytesseract # pytesseract をインポート
from io import BytesIO # BytesIO をインポート

from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import Qt, QRect, QBuffer, QIODevice, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen

# 外部モジュールからのインポート
from src.threads.gemini_worker import GeminiWorker
from src.widgets.custom_message_box import CustomMessageBox
from src.widgets.loading_indicator import LoadingIndicator
from src.config.config_manager import ConfigManager
from src.utils.helper_functions import add_translation_entry, save_translation_history, load_translation_history

class SelectionWindow(QWidget):
    """
    スクリーンショット範囲を選択するための半透明オーバーレイウィンドウ。
    """
    def __init__(self, parent=None, config_manager=None, history_file_path=None, result_window=None):
        super().__init__(parent)
        print("DEBUG: SelectionWindow: __init__ が呼び出されました。")
        self.config_manager = config_manager
        self.history_file_path = history_file_path
        self.result_window = result_window

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.X11BypassWindowManagerHint
        )
        self.setCursor(Qt.CrossCursor)
        self.setWindowOpacity(0.2)
        self.setStyleSheet("background-color: black;")

        screen_geometry = QApplication.instance().desktop().screenGeometry()
        self.setGeometry(screen_geometry)
        print(f"DEBUG: SelectionWindow: 画面サイズを {screen_geometry.width()}x{screen_geometry.height()} に設定しました。")

        # Tesseractのパス設定は_perform_ocr内で動的に行う
        
        self.start_point = None
        self.end_point = None
        self.selecting = False
        self.worker_thread = None
        self.loading_indicator = LoadingIndicator(self)
        self.loading_indicator.hide()
        print("DEBUG: SelectionWindow: 初期化完了。")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.selecting = True
            self.repaint()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.end_point = event.pos()
            self.repaint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selecting:
            self.end_point = event.pos()
            self.selecting = False
            self.hide()
            print("DEBUG: mouseReleaseEvent: ウィンドウを非表示にしました。")

            if self.start_point and self.end_point:
                x1 = min(self.start_point.x(), self.end_point.x())
                y1 = min(self.start_point.y(), self.end_point.y())
                x2 = max(self.start_point.x(), self.end_point.x())
                y2 = max(self.start_point.y(), self.end_point.y())

                if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                    print("DEBUG: 選択範囲が小さすぎます。処理を中断します。")
                    self.show_custom_messagebox("エラー", "選択範囲が小さすぎます。", QMessageBox.Warning)
                    return

                screenshot_data = self.take_selected_screenshot_in_memory(x1, y1, x2 - x1, y2 - y1)
                
                original_text_from_ocr = self._perform_ocr(screenshot_data) # ここでOCRを実行

                if screenshot_data:
                    if self.config_manager.get("behavior.show_api_confirmation"):
                        dialog = CustomMessageBox(
                            self,
                            "API送信確認",
                            "スクリーンショットをGemini APIに送信して翻訳しますか？",
                            QMessageBox.Question,
                            QMessageBox.Yes | QMessageBox.No
                        )
                        script_dir = os.path.dirname(__file__)
                        qss_file_path = os.path.join(script_dir, '..', 'styles', 'custom_message_box.qss')
                        try:
                            with open(qss_file_path, 'r', encoding='utf-8') as f:
                                dialog.setStyleSheet(f.read())
                        except FileNotFoundError:
                            print(f"ERROR: スタイルシートファイル '{qss_file_path}' が見つかりませんでした。")
                        except Exception as e:
                            print(f"ERROR: スタイルシートの読み込み中にエラーが発生しました: {e}")

                        reply = dialog.exec_()
                    else:
                        reply = QMessageBox.Yes

                    if reply == QMessageBox.Yes:
                        print("DEBUG: API送信が承認されました。")
                        self.loading_indicator.show()
                        self.worker_thread = GeminiWorker(screenshot_data, original_text_from_ocr, self.config_manager, self.history_file_path)
                        self.worker_thread.finished.connect(self.on_gemini_finished)
                        self.worker_thread.error.connect(self.on_gemini_error)
                        self.worker_thread.start()
                    else:
                        print("DEBUG: API送信がキャンセルされました。")
                else:
                    self.show_custom_messagebox("エラー", "スクリーンショットの取得に失敗しました。", QMessageBox.Critical)
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("DEBUG: Escキーが押されました。選択をキャンセルします。")
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.selecting and self.start_point and self.end_point:
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(QColor(255, 255, 255, 50))
            painter.drawRect(rect)

    def take_selected_screenshot_in_memory(self, x, y, width, height):
        print(f"DEBUG: take_selected_screenshot: スクリーンショット範囲 ({x},{y},{width},{height})")
        
        output_folder = self.config_manager.get("OUTPUT_FOLDER", "screenshots")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"DEBUG: フォルダ '{output_folder}' を作成しました。")

        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": width, "height": height}
            sct_img = sct.grab(monitor)

            img_pil = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(output_folder, filename)

            try:
                img_pil.save(filepath, "PNG")
                print(f"DEBUG: スクリーンショットをファイルに保存しました: {filepath}")
            except Exception as e:
                print(f"ERROR: スクリーンショットのファイル保存中にエラーが発生しました: {e}")
                return None

            byte_array = QBuffer()
            byte_array.open(QIODevice.WriteOnly)
            img_pil.save(byte_array, "PNG")
            print("DEBUG: スクリーンショットをメモリに取得しました。")
            return byte_array.buffer().data()

    def _perform_ocr(self, image_data):
        """
        バイトデータからOCRを実行し、抽出されたテキストを返す。
        Tesseract OCRエンジンとpytesseractが必要。
        OCRが利用できない場合は空の文字列を返す。
        """
        tesseract_path = self.config_manager.get("ocr_settings.tesseract_path")
        lang = self.config_manager.get("ocr_settings.lang", "eng+jpn")
        ocr_config_str = self.config_manager.get("ocr_settings.config", "--psm 3")

        # Tesseractのパスが指定されていない場合、OCRをスキップ
        if not tesseract_path:
            print("DEBUG: OCRスキップ: setting.yamlでtesseract_pathが指定されていません。")
            return ""
        
        # pytesseract.pytesseract.tesseract_cmd を設定 (OCR実行時のみ)
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

        try:
            img_pil = Image.open(BytesIO(image_data))
            extracted_text = pytesseract.image_to_string(img_pil, lang=lang, config=ocr_config_str)
            return extracted_text.strip()
        except pytesseract.TesseractNotFoundError:
            error_msg = "OCR機能が利用できません。\n" \
                        "Tesseract OCRエンジンが見つかりません。\n" \
                        "Tesseractがインストールされ、PATHに設定されているか、\n" \
                        "またはsetting.yamlのocr_settings.tesseract_pathに正しいパスが指定されているか確認してください。"
            print(f"ERROR: OCR処理中にエラーが発生しました: {error_msg}")
            # ユーザーにはエラーを通知するが、Gemini APIには空の文字列を渡す
            self.show_custom_messagebox("OCRエラー", error_msg, QMessageBox.Critical)
            return ""
        except Exception as e:
            error_msg = f"OCR処理中に予期せぬエラーが発生しました: {e}"
            print(f"ERROR: OCR処理中にエラーが発生しました: {error_msg}")
            self.show_custom_messagebox("OCRエラー", error_msg, QMessageBox.Critical)
            # ユーザーにはエラーを通知するが、Gemini APIには空の文字列を渡す
            return ""


    def on_gemini_finished(self, original_text, translation, explanation):
        """Slot called when Gemini API processing is complete"""
        self.loading_indicator.hide()

        # 翻訳結果を履歴に追加
        history_data = load_translation_history(self.history_file_path)
        add_translation_entry(history_data, original_text, translation, explanation)
        save_translation_history(self.history_file_path, history_data)

        if self.result_window:
            self.result_window.update_content(translation, explanation)
            self.result_window.show()
            self.result_window.raise_()
            self.result_window.activateWindow()
        else:
            self.show_custom_messagebox("翻訳結果", f"翻訳結果:\n{translation}\n\n解説:\n{explanation}", QMessageBox.Information)

    def on_gemini_error(self, error_message):
        """Slot called when an error occurs during Gemini API processing"""
        self.loading_indicator.hide()
        self.show_custom_messagebox("エラー", error_message, QMessageBox.Critical)

    def show_custom_messagebox(self, title, message, icon_type, buttons=QMessageBox.Ok):
        """
        Function to display a custom message box.
        Uses the CustomMessageBox class.
        """
        dialog = CustomMessageBox(self, title, message, icon_type, buttons)
        script_dir = os.path.dirname(__file__)
        qss_file_path = os.path.join(script_dir, '..', 'styles', 'custom_message_box.qss')
        try:
            with open(qss_file_path, 'r', encoding='utf-8') as f:
                dialog.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"ERROR: スタイルシートファイル '{qss_file_path}' が見つかりませんでした。")
        except Exception as e:
            print(f"ERROR: スタイルシートの読み込み中にエラーが発生しました: {e}")
        return dialog.exec_()


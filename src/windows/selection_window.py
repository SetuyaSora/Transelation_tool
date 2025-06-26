import mss
import mss.tools
import time
import os
from PIL import Image # Pillowをインポート
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import Qt, QRect, QBuffer, QIODevice, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen # QPainter と QColor を追加

# 外部モジュールからのインポート
from src.threads.gemini_worker import GeminiWorker
from src.widgets.custom_message_box import CustomMessageBox
from src.widgets.loading_indicator import LoadingIndicator
from src.config.config_manager import ConfigManager # ConfigManagerをインポート
from src.utils.helper_functions import add_translation_entry, save_translation_history, load_translation_history # 履歴関連関数をインポート

class SelectionWindow(QWidget):
    """
    スクリーンショット範囲を選択するための半透明オーバーレイウィンドウ。
    """
    def __init__(self, parent=None, config_manager=None, history_file_path=None, result_window=None):
        super().__init__(parent)
        print("DEBUG: SelectionWindow: __init__ が呼び出されました。")
        self.config_manager = config_manager
        self.history_file_path = history_file_path
        self.result_window = result_window # 翻訳結果ウィンドウの参照を保持

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

        self.start_point = None
        self.end_point = None
        self.selecting = False
        self.worker_thread = None # GeminiWorkerスレッドを保持するための変数
        self.loading_indicator = LoadingIndicator(self) # Initialize loading indicator
        self.loading_indicator.hide() # Hide initially
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

                # スクリーンショットを撮影し、ファイルに保存してからデータを取得
                screenshot_data = self.take_selected_screenshot_in_memory(x1, y1, x2 - x1, y2 - y1)
                
                if screenshot_data:
                    # Check if confirmation dialog should be shown
                    if self.config_manager.get("behavior.show_api_confirmation"): # ConfigManagerから設定を取得
                        dialog = CustomMessageBox(
                            self,
                            "API送信確認",
                            "スクリーンショットをGemini APIに送信して翻訳しますか？",
                            QMessageBox.Question,
                            QMessageBox.Yes | QMessageBox.No
                        )
                        # QSSファイルを読み込んでスタイルを適用
                        script_dir = os.path.dirname(__file__)
                        qss_file_path = os.path.join(script_dir, '..', 'styles', 'custom_message_box.qss')
                        try:
                            with open(qss_file_path, 'r', encoding='utf-8') as f:
                                dialog.setStyleSheet(f.read())
                        except FileNotFoundError:
                            print(f"ERROR: スタイルシートファイル '{qss_file_path}' が見つかりませんでした。")
                        except Exception as e:
                            print(f"ERROR: スタイルシートの読み込み中にエラーが発生しました: {e}")

                        reply = dialog.exec_() # Show as modal
                    else:
                        reply = QMessageBox.Yes # If not showing dialog, assume YES to proceed

                    if reply == QMessageBox.Yes:
                        print("DEBUG: API送信が承認されました。")
                        self.loading_indicator.show() # Show loading indicator
                        # Start asynchronous API processing
                        # ConfigManagerとhistory_file_pathをGeminiWorkerに渡す
                        self.worker_thread = GeminiWorker(screenshot_data, self.config_manager, self.history_file_path)
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
        
        # Create screenshot save folder if it does not exist
        output_folder = self.config_manager.get("OUTPUT_FOLDER", "screenshots") # OUTPUT_FOLDERもConfigManagerから取得
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"DEBUG: フォルダ '{output_folder}' を作成しました。")

        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": width, "height": height}
            sct_img = sct.grab(monitor)

            img_pil = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            
            # Use timestamp for filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(output_folder, filename)

            try:
                img_pil.save(filepath, "PNG")
                print(f"DEBUG: スクリーンショットをファイルに保存しました: {filepath}")
            except Exception as e:
                print(f"ERROR: スクリーンショットのファイル保存中にエラーが発生しました: {e}")
                return None # Return None on save failure

            byte_array = QBuffer()
            byte_array.open(QIODevice.WriteOnly)
            img_pil.save(byte_array, "PNG")
            print("DEBUG: スクリーンショットをメモリに取得しました。")
            return byte_array.buffer().data()

    def on_gemini_finished(self, original_text, translation, explanation):
        """Slot called when Gemini API processing is complete"""
        self.loading_indicator.hide() # Hide loading indicator

        # 翻訳結果を履歴に追加
        # グローバル変数ではなく、ヘルパー関数を直接呼び出す
        history_data = load_translation_history(self.history_file_path)
        add_translation_entry(history_data, original_text, translation, explanation)
        save_translation_history(self.history_file_path, history_data) # 履歴をファイルに保存

        if self.result_window: # result_windowの参照を使用
            self.result_window.update_content(translation, explanation)
            self.result_window.show()
            self.result_window.raise_()
            self.result_window.activateWindow()
        else:
            # Display information dialog if result_window does not exist
            self.show_custom_messagebox("翻訳結果", f"翻訳結果:\n{translation}\n\n解説:\n{explanation}", QMessageBox.Information)

    def on_gemini_error(self, error_message):
        """Slot called when an error occurs during Gemini API processing"""
        self.loading_indicator.hide() # Hide loading indicator on error
        self.show_custom_messagebox("エラー", error_message, QMessageBox.Critical)

    def show_custom_messagebox(self, title, message, icon_type, buttons=QMessageBox.Ok):
        """
        Function to display a custom message box.
        Uses the CustomMessageBox class.
        """
        dialog = CustomMessageBox(self, title, message, icon_type, buttons)
        # QSSファイルを読み込んでスタイルを適用
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


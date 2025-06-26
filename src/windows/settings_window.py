from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QApplication, QStyle
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QEvent
import os

# 外部モジュールからのインポート
from src.config.config_manager import ConfigManager
from src.utils.helper_functions import get_key_name_from_vk_code, hotkey_signal, HotkeyCaptureListener

class SettingsWindow(QDialog):
    """
    アプリケーションの設定（ホットキーなど）を行うウィンドウ。
    """
    # Signal to notify main app that settings have been saved
    settings_saved = pyqtSignal()

    def __init__(self, parent=None, config_manager=None): # config_managerを引数に追加
        super().__init__(parent)
        print("DEBUG: SettingsWindow: __init__ が呼び出されました。")
        self.config_manager = config_manager
        
        self.setWindowTitle("設定")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True) # モーダルにする

        self.new_hotkey_vk_code = None
        self.capturing_hotkey = False
        self.hotkey_capture_listener = HotkeyCaptureListener() # ホットキーキャプチャリスナーのインスタンス

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("設定", self)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        close_button = QPushButton("X", self)
        close_button.setFixedSize(20, 20)
        close_button.clicked.connect(self.reject) # Use reject to signify cancellation
        header_layout.addWidget(close_button)
        main_layout.addLayout(header_layout)

        # Hotkey setting section
        hotkey_group_layout = QVBoxLayout()
        hotkey_label = QLabel("ホットキー設定:", self)
        hotkey_group_layout.addWidget(hotkey_label)

        current_hotkey_code = self.config_manager.get("hotkey.key_code")
        current_hotkey_name = get_key_name_from_vk_code(current_hotkey_code)
        self.current_hotkey_display = QLabel(f"現在のホットキー: {current_hotkey_name} (0x{current_hotkey_code:X})", self)
        hotkey_group_layout.addWidget(self.current_hotkey_display)

        self.capture_button = QPushButton("新しいホットキーを設定", self)
        self.capture_button.clicked.connect(self._start_key_capture)
        hotkey_group_layout.addWidget(self.capture_button)

        self.new_hotkey_display = QLabel("新しいホットキー: 未設定", self)
        hotkey_group_layout.addWidget(self.new_hotkey_display)

        main_layout.addLayout(hotkey_group_layout)
        main_layout.addStretch()

        # Save/Cancel buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.save_button = QPushButton("保存", self)
        self.save_button.clicked.connect(self._save_settings)
        self.save_button.setEnabled(False) # Disable until a new key is captured
        button_layout.addWidget(self.save_button)
        cancel_button = QPushButton("キャンセル", self)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.resize(400, 250)
        self.center_on_screen()
        # スタイルシートは外部ファイルから読み込む
        self._load_stylesheet(os.path.join(os.path.dirname(__file__), '..', 'styles', 'settings_window.qss'))

        # hotkey_signalからのキーキャプチャイベントを受け取る
        hotkey_signal.key_captured.connect(self._on_key_captured)


    def _load_stylesheet(self, qss_file_path):
        """指定されたQSSファイルを読み込んでスタイルを適用する。"""
        try:
            with open(qss_file_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"ERROR: スタイルシートファイル '{qss_file_path}' が見つかりませんでした。")
        except Exception as e:
            print(f"ERROR: スタイルシートの読み込み中にエラーが発生しました: {e}")

    def center_on_screen(self):
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _start_key_capture(self):
        self.capturing_hotkey = True
        self.capture_button.setText("新しいキーを押してください...")
        self.new_hotkey_display.setText("新しいホットキー: キー入力待機中...")
        self.save_button.setEnabled(False)
        self.hotkey_capture_listener.start_capture(self._on_key_captured) # キャプチャ開始

    def _on_key_captured(self, vk_code):
        """HotkeyCaptureListenerからキーがキャプチャされたときに呼び出されるスロット。"""
        if not self.capturing_hotkey:
            return

        self.new_hotkey_vk_code = vk_code
        key_name = get_key_name_from_vk_code(vk_code)
        self.new_hotkey_display.setText(f"新しいホットキー: {key_name} (0x{vk_code:X})")
        self.capture_button.setText("ホットキーを再設定")
        self.save_button.setEnabled(True)
        self.capturing_hotkey = False
        self.hotkey_capture_listener.stop_capture() # キャプチャ停止を確実に

    def _save_settings(self):
        if self.new_hotkey_vk_code is not None:
            self.config_manager.set("hotkey.key_code", self.new_hotkey_vk_code) # ConfigManager経由で設定
            self.config_manager.save_settings() # ConfigManager経由で保存
            self.settings_saved.emit() # Emit signal that settings are saved
            self.accept() # Close the dialog with accept result
        else:
            QMessageBox.warning(self, "警告", "新しいホットキーが選択されていません。")

    def showEvent(self, event):
        # Reset state when window is shown
        self.new_hotkey_vk_code = None
        self.capturing_hotkey = False
        self.capture_button.setText("新しいホットキーを設定")
        self.new_hotkey_display.setText("新しいホットキー: 未設定")
        self.save_button.setEnabled(False)
        # Update current hotkey display in case it was changed externally
        current_hotkey_code = self.config_manager.get("hotkey.key_code")
        current_hotkey_name = get_key_name_from_vk_code(current_hotkey_code)
        self.current_hotkey_display.setText(f"現在のホットキー: {current_hotkey_name} (0x{current_hotkey_code:X})")
        super().showEvent(event)
    
    def reject(self):
        if self.capturing_hotkey: # もしキャプチャ中にキャンセルされたら、キャプチャを停止
            self.hotkey_capture_listener.stop_capture()
        super().reject()

    # --- デバッグ用ログ追加 ---
    def show(self):
        print("DEBUG: SettingsWindow: show() が呼び出されました。")
        super().show()

    def hide(self):
        print("DEBUG: SettingsWindow: hide() が呼び出されました。")
        super().hide()

    def accept(self):
        print("DEBUG: SettingsWindow: accept() が呼び出されました。")
        super().accept()

    def reject(self):
        print("DEBUG: SettingsWindow: reject() が呼び出されました。")
        super().reject()

    def closeEvent(self, event):
        print("DEBUG: SettingsWindow: closeEvent() が呼び出されました。")
        super().closeEvent(event)
    
    def __del__(self):
        print("DEBUG: SettingsWindow: __del__() が呼び出されました。SettingsWindowが破棄されています。")
        super().__del__()
    # --- デバッグ用ログここまで ---


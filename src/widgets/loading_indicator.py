from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt
import os
import sys
import logging # logging モジュールを追加
# from PyQt5.QtGui import QMovie # GIFアニメーションを使う場合に必要

logger = logging.getLogger(__name__) # このモジュール用のロガーを取得

class LoadingIndicator(QWidget):
    """
    API処理中に表示されるシンプルなローディングインジケーター。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("LoadingIndicator: __init__ が呼び出されました。")
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground) # 背景を透過させる

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setAlignment(Qt.AlignCenter)

        # Loading message
        self.message_label = QLabel("翻訳中...", self)
        self.message_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.message_label)
        
        # Simple pulsating animation (can be replaced with GIF if available)
        self.setFixedSize(200, 100)
        self._load_stylesheet(os.path.join('..', 'styles', 'loading_indicator.qss'))

        self.center_on_screen()

    def _load_stylesheet(self, qss_relative_path):
        """
        指定されたQSSファイルを読み込んでスタイルを適用する。
        PyInstallerでバンドルされた環境を考慮する。
        """
        base_path = ""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)

        qss_full_path = os.path.join(base_path, qss_relative_path)
        
        try:
            with open(qss_full_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
            logger.debug(f"スタイルシート '{qss_full_path}' を読み込みました。")
        except FileNotFoundError:
            logger.error(f"スタイルシートファイル '{qss_full_path}' が見つかりませんでした。")
        except Exception as e:
            logger.exception(f"スタイルシートの読み込み中にエラーが発生しました。")

    def center_on_screen(self):
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def show(self):
        super().show()
        self.raise_()
        self.activateWindow()


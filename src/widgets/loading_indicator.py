from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt
import os
import sys
import logging

logger = logging.getLogger(__name__)

class LoadingIndicator(QWidget):
    """
    API処理中に表示されるシンプルなローディングインジケーター。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("LoadingIndicator: __init__ が呼び出されました。")
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setAlignment(Qt.AlignCenter)

        # Loading message
        self.message_label = QLabel("翻訳中...", self)
        self.message_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.message_label)
        
        self.setFixedSize(200, 100)
        # スタイルシートは外部ファイルから読み込む
        # 修正: 'styles/loading_indicator.qss' に変更
        self._load_stylesheet(os.path.join('styles', 'loading_indicator.qss'))

        self.center_on_screen()

    def _load_stylesheet(self, qss_relative_path): # 引数は 'styles/loading_indicator.qss' のような形式
        """
        指定されたQSSファイルを読み込んでスタイルを適用する。
        PyInstallerでバンドルされた環境を考慮する。
        """
        base_path = ""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS # PyInstallerが展開する一時ディレクトリのパス
        else:
            # 通常のPythonスクリプトとして実行されている場合
            # loading_indicator.py は src/widgets にあるため、styles は src/styles にある
            # よって、os.path.dirname(__file__) (src/widgets) から一つ上 (src) に行き、styles に入る
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

        # QSSファイルの絶対パスを構築
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

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt
import os # os モジュールを追加
import sys # sys モジュールを追加
# from PyQt5.QtGui import QMovie # GIFアニメーションを使う場合に必要

class LoadingIndicator(QWidget):
    """
    API処理中に表示されるシンプルなローディングインジケーター。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        print("DEBUG: LoadingIndicator: __init__ が呼び出されました。")
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
        self.setFixedSize(200, 100) # Fixed size for the loading indicator
        # スタイルシートは外部ファイルから読み込む
        # 相対パスを渡す
        self._load_stylesheet(os.path.join('..', 'styles', 'loading_indicator.qss'))

        self.center_on_screen()

    def _load_stylesheet(self, qss_relative_path): # 引数をQSSへの相対パスに変更
        """
        指定されたQSSファイルを読み込んでスタイルを適用する。
        PyInstallerでバンドルされた環境を考慮する。
        """
        base_path = ""
        if getattr(sys, 'frozen', False):
            # PyInstallerで実行されている場合
            base_path = sys._MEIPASS # PyInstallerが展開する一時ディレクトリのパス
        else:
            # 通常のPythonスクリプトとして実行されている場合
            base_path = os.path.dirname(__file__)

        # QSSファイルの絶対パスを構築
        qss_full_path = os.path.join(base_path, qss_relative_path)
        
        try:
            with open(qss_full_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
            print(f"DEBUG: スタイルシート '{qss_full_path}' を読み込みました。")
        except FileNotFoundError:
            print(f"ERROR: スタイルシートファイル '{qss_full_path}' が見つかりませんでした。")
        except Exception as e:
            print(f"ERROR: スタイルシートの読み込み中にエラーが発生しました: {e}")

    def center_on_screen(self):
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def show(self):
        super().show()
        # Bring to front
        self.raise_()
        self.activateWindow()

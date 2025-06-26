from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt
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
        # self.message_label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;") # スタイルはQSSから
        self.message_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.message_label)
        
        # Simple pulsating animation (can be replaced with GIF if available)
        self.setFixedSize(200, 100) # Fixed size for the loading indicator
        # self.setStyleSheet(""" ... """) # スタイルはQSSから
        self.center_on_screen()

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


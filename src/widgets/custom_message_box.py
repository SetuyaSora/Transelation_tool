from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QStyle, QApplication # QApplication を追加
from PyQt5.QtCore import Qt

class CustomMessageBox(QDialog):
    """
    カスタムデザインのメッセージボックスを提供するクラス。
    標準のQMessageBoxの代わりに利用される。
    """
    def __init__(self, parent=None, title="メッセージ", message="メッセージ", icon_type=QMessageBox.Information, buttons=QMessageBox.Ok):
        super().__init__(parent)
        print("DEBUG: CustomMessageBox: __init__ が呼び出されました。")
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True) # モーダルダイアログにする

        self.result = QMessageBox.NoButton # デフォルトの結果

        # レイアウト
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10) # Adjust margins for better spacing
        main_layout.setSpacing(10) # Adjust spacing between elements

        # Header layout for title and close button
        header_layout = QHBoxLayout()
        title_label = QLabel(title, self)
        title_label.setStyleSheet("font-weight: bold; color: white;") # Style for the title label
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Close button for the custom message box
        close_button = QPushButton("X", self)
        close_button.setFixedSize(20, 20) # Fixed size for the close button
        close_button.clicked.connect(lambda: self.done(QMessageBox.Cancel)) # Close on click
        header_layout.addWidget(close_button)
        main_layout.addLayout(header_layout)

        # Icon and message
        content_layout = QHBoxLayout()
        icon_label = QLabel(self)
        if icon_type == QMessageBox.Information:
            icon_label.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxInformation).pixmap(32, 32))
        elif icon_type == QMessageBox.Warning:
            icon_label.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxWarning).pixmap(32, 32))
        elif icon_type == QMessageBox.Critical:
            icon_label.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxCritical).pixmap(32, 32))
        elif icon_type == QMessageBox.Question:
            icon_label.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxQuestion).pixmap(32, 32))
        content_layout.addWidget(icon_label)

        message_label = QLabel(message, self)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        content_layout.addWidget(message_label)
        main_layout.addLayout(content_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch() # Push buttons to the right

        if buttons & QMessageBox.Ok:
            ok_button = QPushButton("OK", self)
            ok_button.clicked.connect(lambda: self.done(QMessageBox.Ok))
            button_layout.addWidget(ok_button)
        if buttons & QMessageBox.Yes:
            yes_button = QPushButton("はい", self)
            yes_button.clicked.connect(lambda: self.done(QMessageBox.Yes))
            button_layout.addWidget(yes_button)
        if buttons & QMessageBox.No:
            no_button = QPushButton("いいえ", self)
            no_button.clicked.connect(lambda: self.done(QMessageBox.No))
            button_layout.addWidget(no_button)
        if buttons & QMessageBox.Cancel:
            cancel_button = QPushButton("キャンセル", self)
            cancel_button.clicked.connect(lambda: self.done(QMessageBox.Cancel))
            button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        self.resize(350, 150) # Set recommended initial size
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    # Close dialog with Esc key
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.done(QMessageBox.Cancel) # Close as cancel with Esc key
        else:
            super().keyPressEvent(event)


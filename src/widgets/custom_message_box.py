from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QStyle, QApplication, QRadioButton, QButtonGroup
from PyQt5.QtCore import Qt

class CustomMessageBox(QDialog):
    """
    カスタムデザインのメッセージボックスを提供するクラス。
    標準のQMessageBoxの代わりに利用される。
    モード選択機能も追加。
    """
    def __init__(self, parent=None, title="メッセージ", message="メッセージ", icon_type=QMessageBox.Information, buttons=QMessageBox.Ok, current_mode="translation"): # current_modeを引数に追加
        super().__init__(parent)
        print("DEBUG: CustomMessageBox: __init__ が呼び出されました。")
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True) # モーダルダイアログにする

        self.result = QMessageBox.NoButton # デフォルトの結果 (Yes/No/Cancelなど)
        self.selected_mode = current_mode # 選択されたモードを初期化

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

        # --- モード選択ラジオボタンの追加 ---
        mode_selection_layout = QHBoxLayout()
        mode_selection_label = QLabel("モード選択:", self)
        mode_selection_label.setStyleSheet("color: white; font-weight: bold;")
        mode_selection_layout.addWidget(mode_selection_label)

        self.translation_radio = QRadioButton("翻訳モード", self)
        self.translation_radio.setStyleSheet("color: white;")
        self.explanation_radio = QRadioButton("解説モード", self)
        self.explanation_radio.setStyleSheet("color: white;")

        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.addButton(self.translation_radio, 0) # 0 for translation
        self.mode_button_group.addButton(self.explanation_radio, 1) # 1 for explanation

        # 初期モードを設定
        if current_mode == "explanation":
            self.explanation_radio.setChecked(True)
        else:
            self.translation_radio.setChecked(True) # デフォルトは翻訳モード

        self.mode_button_group.buttonClicked.connect(self._on_mode_selected)

        mode_selection_layout.addWidget(self.translation_radio)
        mode_selection_layout.addWidget(self.explanation_radio)
        mode_selection_layout.addStretch() # 右寄せ

        main_layout.addLayout(mode_selection_layout)
        # --- モード選択ラジオボタンここまで ---


        # Buttons (Yes/No/Ok/Cancel)
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
        self.resize(350, 200) # モード選択分、高さを少し調整
        self.center_on_screen()

    def _on_mode_selected(self, button):
        """ラジオボタンがクリックされたときに呼び出される。"""
        if button == self.translation_radio:
            self.selected_mode = "translation"
        elif button == self.explanation_radio:
            self.selected_mode = "explanation"
        print(f"DEBUG: CustomMessageBox: モードが '{self.selected_mode}' に選択されました。")


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


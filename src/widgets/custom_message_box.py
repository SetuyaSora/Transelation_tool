from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QStyle, QApplication, QRadioButton, QButtonGroup
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent # QPoint, QRect, QEvent を追加

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

        # ドラッグ・リサイズ関連のフラグと位置情報
        self._resizing = False
        self._dragging = False
        self._resize_start_pos = None
        self._resize_start_geometry = None
        self._resize_edge = []
        self._drag_start_pos = None

        self.setMouseTracking(True) # マウス移動イベントを常に受け取る


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

    _border_width = 8 # クラス変数として定義 (リサイズ境界線の幅)

    def _is_at_border(self, pos):
        """マウスカーソルがウィンドウの境界線付近にあるか判定する。"""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        border = self._border_width
        
        at_left = x < border
        at_right = x > w - border
        at_top = y < border
        at_bottom = y > h - border
        
        return at_left or at_right or at_top or at_bottom

    def _get_cursor_shape(self, pos):
        """マウスカーソルの位置に応じてカーソル形状を決定する。"""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        border = self._border_width

        at_left = x < border
        at_right = x > w - border
        at_top = y < border
        at_bottom = y > h - border

        if at_top and at_left: return Qt.SizeFDiagCursor
        if at_top and at_right: return Qt.SizeBDiagCursor
        if at_bottom and at_left: return Qt.SizeBDiagCursor
        if at_bottom and at_right: return Qt.SizeFDiagCursor
        if at_left or at_right: return Qt.SizeHorCursor
        if at_top or at_bottom: return Qt.SizeVerCursor
        
        return Qt.ArrowCursor

    def _get_resize_edge(self, pos):
        """リサイズする境界線の方向をリストで返す。"""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        border = self._border_width

        edge = []
        if x < border: edge.append("left")
        if x > w - border: edge.append("right")
        if y < border: edge.append("top")
        if y > h - border: edge.append("bottom")
        return edge

    def _handle_resize(self, global_pos):
        """ウィンドウのリサイズ処理を行う。"""
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()

        new_x, new_y, new_width, new_height = self._resize_start_geometry.x(), \
                                             self._resize_start_geometry.y(), \
                                             self._resize_start_geometry.width(), \
                                             self._resize_start_geometry.height()

        for edge in self._resize_edge:
            if edge == "left":
                new_x += dx
                new_width -= dx
            elif edge == "right":
                new_width += dx
            elif edge == "top":
                new_y += dy
                new_height -= dy
            elif edge == "bottom":
                new_height += dy

        # CustomMessageBoxの最小サイズは固定値で指定 (例: 350x200)
        min_width = 350 # CustomMessageBoxの最小幅
        min_height = 200 # CustomMessageBoxの最小高さ
        
        if new_width < min_width:
            if "left" in self._resize_edge:
                new_x = self._resize_start_geometry.x() + self._resize_start_geometry.width() - min_width
            new_width = min_width
        
        if new_height < min_height:
            if "top" in self._resize_edge:
                new_y = self._resize_start_geometry.y() + self._resize_start_geometry.height() - min_height
            new_height = min_height

        self.setGeometry(new_x, new_y, new_width, new_height)

    def mousePressEvent(self, event):
        """マウスが押された時のイベントハンドラ。ドラッグまたはリサイズを開始する。"""
        if event.button() == Qt.LeftButton:
            local_pos = self.mapFromGlobal(event.globalPos())
            if self._is_at_border(local_pos):
                self._resizing = True
                self._resize_start_pos = event.globalPos()
                self._resize_start_geometry = self.geometry()
                self._resize_edge = self._get_resize_edge(local_pos)
                self.setCursor(self._get_cursor_shape(local_pos))
                self._dragging = False # リサイズ中なのでドラッグではない
            else:
                self._dragging = True
                # ウィンドウの左上隅とマウスのグローバル位置のオフセットを記録
                self._drag_start_pos = event.globalPos() - self.pos() 
                self._resizing = False # ドラッグ中なのでリサイズではない
        super().mousePressEvent(event) # 基底クラスのイベントハンドラも呼び出す

    def mouseMoveEvent(self, event):
        """マウスが移動した時のイベントハンドラ。ドラッグまたはリサイズを実行する。"""
        if event.buttons() == Qt.LeftButton: # 左クリックが押されている場合
            if self._resizing:
                self._handle_resize(event.globalPos())
            elif self._dragging:
                # ウィンドウの新しい位置を計算
                self.move(event.globalPos() - self._drag_start_pos)
        else: # ボタンが押されていない場合 (マウスオーバー)
            local_pos = self.mapFromGlobal(event.globalPos())
            # ドラッグもリサイズもしていない場合のみカーソル形状を更新
            if not self._dragging and not self._resizing:
                current_cursor = self._get_cursor_shape(local_pos)
                self.setCursor(current_cursor)
        super().mouseMoveEvent(event) # 基底クラスのイベントハンドラも呼び出す

    def mouseReleaseEvent(self, event):
        """マウスボタンが離された時のイベントハンドラ。ドラッグまたはリサイズを終了する。"""
        self._dragging = False
        self._resizing = False
        self.setCursor(Qt.ArrowCursor) # カーソルをデフォルトに戻す
        super().mouseReleaseEvent(event) # 基底クラスのイベントハンドラも呼び出す

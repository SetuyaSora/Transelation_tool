from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QStyle, QApplication, QRadioButton, QButtonGroup
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent
import os
import sys
import logging

logger = logging.getLogger(__name__)

class CustomMessageBox(QDialog):
    """
    カスタムデザインのメッセージボックスを提供するクラス。
    標準のQMessageBoxの代わりに利用される。
    モード選択機能も追加。
    """
    def __init__(self, parent=None, title="メッセージ", message="メッセージ", icon_type=QMessageBox.Information, buttons=QMessageBox.Ok, current_mode="translation"):
        super().__init__(parent)
        logger.debug("CustomMessageBox: __init__ が呼び出されました。")
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True)

        self.result = QMessageBox.NoButton
        self.selected_mode = current_mode

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_label = QLabel(title, self)
        title_label.setStyleSheet("font-weight: bold; color: white;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        close_button = QPushButton("X", self)
        close_button.setFixedSize(20, 20)
        close_button.clicked.connect(lambda: self.done(QMessageBox.Cancel))
        header_layout.addWidget(close_button)
        main_layout.addLayout(header_layout)

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

        mode_selection_layout = QHBoxLayout()
        mode_selection_label = QLabel("モード選択:", self)
        mode_selection_label.setStyleSheet("color: white; font-weight: bold;")
        mode_selection_layout.addWidget(mode_selection_label)

        self.translation_radio = QRadioButton("翻訳モード", self)
        self.translation_radio.setStyleSheet("color: white;")
        self.explanation_radio = QRadioButton("解説モード", self)
        self.explanation_radio.setStyleSheet("color: white;")

        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.addButton(self.translation_radio, 0)
        self.mode_button_group.addButton(self.explanation_radio, 1)

        if current_mode == "explanation":
            self.explanation_radio.setChecked(True)
        else:
            self.translation_radio.setChecked(True)

        self.mode_button_group.buttonClicked.connect(self._on_mode_selected)

        mode_selection_layout.addWidget(self.translation_radio)
        mode_selection_layout.addWidget(self.explanation_radio)
        mode_selection_layout.addStretch()

        main_layout.addLayout(mode_selection_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

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
        self.resize(350, 200)
        self.center_on_screen()

        # 修正: __init__ からの _load_stylesheet の呼び出しを削除
        # self._load_stylesheet(os.path.join('..', 'styles', 'custom_message_box.qss'))

        self._resizing = False
        self._dragging = False
        self._resize_start_pos = None
        self._resize_start_geometry = None
        self._resize_edge = []
        self._drag_start_pos = None

        self.setMouseTracking(True)


    def _load_stylesheet(self, qss_relative_path): # 引数は 'styles/custom_message_box.qss' のような形式
        """
        指定されたQSSファイルを読み込んでスタイルを適用する。
        PyInstallerでバンドルされた環境を考慮する。
        """
        base_path = ""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS # PyInstallerが展開する一時ディレクトリのパス
        else:
            # 通常のPythonスクリプトとして実行されている場合
            # custom_message_box.py は src/widgets にあるため、styles は src/styles にある
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


    def _on_mode_selected(self, button):
        """ラジオボタンがクリックされたときに呼び出される。"""
        if button == self.translation_radio:
            self.selected_mode = "translation"
        elif button == self.explanation_radio:
            self.selected_mode = "explanation"
        logger.debug(f"CustomMessageBox: モードが '{self.selected_mode}' に選択されました。")


    def center_on_screen(self):
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.done(QMessageBox.Cancel)
        else:
            super().keyPressEvent(event)

    _border_width = 8

    def _is_at_border(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        border = self._border_width
        
        at_left = x < border
        at_right = x > w - border
        at_top = y < border
        at_bottom = y > h - border
        
        return at_left or at_right or at_top or at_bottom

    def _get_cursor_shape(self, pos):
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

        min_width = 350
        min_height = 200
        
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
        if event.button() == Qt.LeftButton:
            local_pos = self.mapFromGlobal(event.globalPos())
            if self._is_at_border(local_pos):
                self._resizing = True
                self._resize_start_pos = event.globalPos()
                self._resize_start_geometry = self.geometry()
                self._resize_edge = self._get_resize_edge(local_pos)
                self.setCursor(self._get_cursor_shape(local_pos))
                self._dragging = False
            else:
                self._dragging = True
                self._drag_start_pos = event.globalPos() - self.pos() 
                self._resizing = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if self._resizing:
                self._handle_resize(event.globalPos())
            elif self._dragging:
                self.move(event.globalPos() - self._drag_start_pos)
        else:
            local_pos = self.mapFromGlobal(event.globalPos())
            if not self._dragging and not self._resizing:
                current_cursor = self._get_cursor_shape(local_pos)
                self.setCursor(current_cursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

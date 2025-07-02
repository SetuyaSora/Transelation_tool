from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QTextBrowser
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QEvent, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen
import os
import sys
import logging

logger = logging.getLogger(__name__)

class ResultWindow(QWidget):
    """
    翻訳結果と解説を表示するウィンドウ。
    ドラッグ移動、リサイズ、最前面表示、フレームレスに対応。
    """
    show_history_signal = pyqtSignal()
    show_settings_signal = pyqtSignal()

    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        logger.debug("ResultWindow: __init__ が呼び出されました。")
        self.config_manager = config_manager
        
        self.setWindowTitle("翻訳結果と解説")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.FramelessWindowHint
        )
        
        min_width = self.config_manager.get("result_window.min_width")
        min_height = self.config_manager.get("result_window.min_height")
        self.setMinimumSize(min_width, min_height)
        self.setGeometry(100, 100, min_width, min_height)

        self._load_stylesheet(os.path.join('..', 'styles', 'result_window.qss'))

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)

        history_button = QPushButton("履歴", self)
        history_button.setObjectName("historyButton")
        history_button.setFixedSize(60, 20)
        history_button.clicked.connect(self.show_history_signal.emit)
        header_layout.addWidget(history_button)
        
        settings_button = QPushButton("設定", self)
        settings_button.setObjectName("settingsButton")
        settings_button.setFixedSize(60, 20)
        settings_button.clicked.connect(self.show_settings_signal.emit)
        header_layout.addWidget(settings_button)
        
        header_layout.addStretch()

        close_button = QPushButton("X", self)
        close_button.setObjectName("closeButton")
        close_button_size = self.config_manager.get("result_window.close_button.size")
        close_button.setFixedSize(close_button_size, close_button_size)
        close_button.clicked.connect(self.close)
        header_layout.addWidget(close_button)

        self.translation_label = QTextBrowser(self)
        self.translation_label.setReadOnly(True)
        self.translation_label.setObjectName("translation_label")
        self.translation_label.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.translation_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.explanation_label = QTextBrowser(self)
        self.explanation_label.setReadOnly(True)
        self.explanation_label.setObjectName("explanation_label")
        self.explanation_label.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.explanation_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.copy_button = QPushButton("すべてコピー", self)
        self.copy_button.setObjectName("copyButton")
        self.copy_button.setFixedSize(90, 25)
        self.copy_button.clicked.connect(self._copy_to_clipboard)
        self.copy_button.setStyleSheet("""
            #copyButton {
                background-color: #28a745;
                color: white;
                border-radius: 5px;
                font-size: 9pt;
                font-weight: bold;
                padding: 0px;
            }
            #copyButton:hover {
                background-color: #218838;
            }
        """)

        self.feedback_label = QLabel("", self)
        self.feedback_label.setAlignment(Qt.AlignCenter)
        self.feedback_label.setStyleSheet("color: #ADD8E6; font-size: 10pt; font-weight: bold;")
        self.feedback_label.hide()

        main_layout = QVBoxLayout()
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.translation_label)
        main_layout.addWidget(self.explanation_label)
        
        copy_layout = QHBoxLayout()
        copy_layout.addStretch()
        copy_layout.addWidget(self.copy_button)
        copy_layout.addWidget(self.feedback_label)
        copy_layout.addStretch()
        main_layout.addLayout(copy_layout)

        main_layout.addStretch()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)
        
        self.hide()

        # --- ドラッグ・リサイズ関連のフラグと位置情報の初期化を追加 ---
        self._resizing = False
        self._dragging = False
        self._resize_start_pos = None
        self._resize_start_geometry = None
        self._resize_edge = []
        self._drag_start_pos = None
        # --- 初期化ここまで ---

        self.setMouseTracking(True)

    def _load_stylesheet(self, qss_relative_path):
        """指定されたQSSファイルを読み込んでスタイルを適用する。"""
        base_path = ""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)

        qss_full_path = os.path.join(base_path, qss_relative_path)
        
        try:
            with open(qss_full_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
            self.setWindowOpacity(self.config_manager.get("result_window.opacity"))
            logger.debug(f"スタイルシート '{qss_full_path}' を読み込みました。")
        except FileNotFoundError:
            logger.error(f"スタイルシートファイル '{qss_full_path}' が見つかりませんでした。")
        except Exception as e:
            logger.exception(f"スタイルシートの読み込み中にエラーが発生しました。")

    def update_content(self, translation, explanation):
        self.translation_label.setPlainText(f"翻訳結果: \n{translation}")
        self.explanation_label.setPlainText(f"解説: \n{explanation}")
        self.show()
        self.activateWindow()

    def _copy_to_clipboard(self):
        """翻訳結果と解説をクリップボードにコピーする。"""
        translation_text = self.translation_label.toPlainText().replace("翻訳結果: \n", "")
        explanation_text = self.explanation_label.toPlainText().replace("解説: \n", "")
        
        combined_text = ""
        if translation_text.strip():
            combined_text += translation_text.strip()
        if explanation_text.strip():
            if combined_text:
                combined_text += "\n\n"
            combined_text += explanation_text.strip()

        if combined_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(combined_text)
            logger.info("翻訳結果と解説をクリップボードにコピーしました。")
            self._show_feedback_message("コピーしました！")
        else:
            logger.info("コピーする内容がありませんでした。")
            self._show_feedback_message("コピーする内容がありません")

    def _show_feedback_message(self, message):
        """一時的なフィードバックメッセージを表示する。"""
        self.feedback_label.setText(message)
        self.feedback_label.show()
        QTimer.singleShot(2000, self.feedback_label.hide)


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            logger.debug("Escキーが押されました。結果ウィンドウを閉じます。")
            self.close()

    def show(self):
        logger.debug("ResultWindow: show() が呼び出されました。")
        super().show()

    def hide(self):
        logger.debug("ResultWindow: hide() が呼び出されました。")
        super().hide()

    def closeEvent(self, event):
        logger.debug("ResultWindow: closeEvent() が呼び出されました。")
        self.hide()
        event.ignore()
        logger.info("ResultWindowをシステムトレイに隠しました。")
    
    def __del__(self):
        logger.debug("ResultWindow: __del__() が呼び出されました。ResultWindowが破棄されています。")
        super().__del__()

    _border_width = 8

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

        min_width = self.minimumSize().width()
        min_height = self.minimumSize().height()

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

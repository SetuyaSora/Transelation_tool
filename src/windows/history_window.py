from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QApplication, QAbstractItemView, QStyle
)
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent
from PyQt5.QtGui import QPainter, QColor, QPen
import os # os モジュールを追加
from src.utils.helper_functions import load_translation_history # 履歴読み込み関数をインポート

class HistoryWindow(QDialog):
    """
    翻訳履歴を表示するウィンドウ。
    """
    def __init__(self, parent=None, history_file_path: str = "translation_history.json"): # 履歴ファイルパスを引数に追加
        super().__init__(parent)
        print("DEBUG: HistoryWindow: __init__ が呼び出されました。")
        self.setWindowTitle("翻訳履歴")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowMinimizeButtonHint)
        self.setModal(False) # 非モーダルダイアログにする (他のウィンドウと同時に操作可能)
        self.history_file_path = history_file_path # 履歴ファイルパスを保持

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header layout
        header_layout = QHBoxLayout()
        title_label = QLabel("翻訳履歴", self)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        close_button = QPushButton("X", self)
        close_button.setFixedSize(20, 20)
        close_button.clicked.connect(self.hide)
        header_layout.addWidget(close_button)
        main_layout.addLayout(header_layout)

        # History list widget
        self.history_list_widget = QListWidget(self)
        self.history_list_widget.setEditTriggers(QAbstractItemView.NoEditTriggers) # 編集不可にする
        self.history_list_widget.itemClicked.connect(self.display_history_item_details)
        main_layout.addWidget(self.history_list_widget)

        # Detail display area (for selected history item)
        self.detail_label = QLabel("詳細: ", self)
        self.detail_label.setWordWrap(True)
        main_layout.addWidget(self.detail_label)

        self.setLayout(main_layout)
        self.resize(500, 400) # Default size for history window
        self.center_on_screen()
        # スタイルシートは外部ファイルから読み込む
        self._load_stylesheet(os.path.join(os.path.dirname(__file__), '..', 'styles', 'history_window.qss'))

        self.load_and_display_history()

        # ドラッグ・リサイズ関連のフラグと位置情報
        self._resizing = False
        self._dragging = False # 新しいフラグ：ドラッグ中か
        self._resize_start_pos = None
        self._resize_start_geometry = None
        self._resize_edge = []
        self._drag_start_pos = None # 新しい変数：ドラッグ開始時のオフセット

        self.setMouseTracking(True) # マウス移動イベントを常に受け取る


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

    def load_and_display_history(self):
        self.history_list_widget.clear()
        current_history = load_translation_history(self.history_file_path) 
        
        for i, item_data in enumerate(reversed(current_history)): # 最新のものが上にくるように逆順で表示
            original_text_display = item_data.get("original_text", "N/A").replace('\n', ' ')
            if len(original_text_display) > 50:
                original_text_display = original_text_display[:47] + "..."
            
            timestamp = item_data.get("timestamp", "")
            display_text = f"[{timestamp}] {original_text_display}"
            
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item_data) # 完全なデータをUserDataとして保存
            self.history_list_widget.addItem(list_item)
        
        if current_history:
            self.history_list_widget.setCurrentRow(0) # 最初の項目を選択状態にする
            self.display_history_item_details(self.history_list_widget.item(0)) # 最初の項目の詳細を表示

    def display_history_item_details(self, item):
        item_data = item.data(Qt.UserRole)
        original = item_data.get("original_text", "N/A")
        translated = item_data.get("translation", "N/A")
        explanation = item_data.get("explanation", "N/A")
        timestamp = item_data.get("timestamp", "N/A")

        details = (
            f"**日時:** {timestamp}\n"
            f"**原文:**\n{original}\n\n"
            f"**翻訳結果:**\n{translated}\n\n"
            f"**解説:**\n{explanation}"
        )
        self.detail_label.setText(details)

    # --- デバッグ用ログ追加 ---
    def show(self):
        print("DEBUG: HistoryWindow: show() が呼び出されました。")
        super().show()

    def hide(self):
        print("DEBUG: HistoryWindow: hide() が呼び出されました。")
        super().hide()

    def closeEvent(self, event):
        print("DEBUG: HistoryWindow: closeEvent() が呼び出されました。")
        super().closeEvent(event)
    
    def __del__(self):
        print("DEBUG: HistoryWindow: __del__() が呼び出されました。HistoryWindowが破棄されています。")
        super().__del__()
    # --- デバッグ用ログここまで ---

    _border_width = 8 # クラス変数として定義

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

        # HistoryWindowの最小サイズを設定 (例: 300x200)
        history_min_width = 300
        history_min_height = 200

        if new_width < history_min_width:
            if "left" in self._resize_edge:
                new_x = self._resize_start_geometry.x() + self._resize_start_geometry.width() - history_min_width
            new_width = history_min_width
        
        if new_height < history_min_height:
            if "top" in self._resize_edge:
                new_y = self._resize_start_geometry.y() + self._resize_start_geometry.height() - history_min_height
            new_height = history_min_height

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


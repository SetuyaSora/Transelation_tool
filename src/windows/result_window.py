from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QEvent
from PyQt5.QtGui import QPainter, QColor, QPen
import os
import sys # sys モジュールを追加

class ResultWindow(QWidget):
    """
    翻訳結果と解説を表示するウィンドウ。
    ドラッグ移動、リサイズ、最前面表示、フレームレスに対応。
    """
    # 履歴ウィンドウを表示するためのシグナルを追加
    show_history_signal = pyqtSignal()
    # 設定ウィンドウを表示するためのシグナルを追加
    show_settings_signal = pyqtSignal()

    def __init__(self, parent=None, config_manager=None): # config_managerを引数に追加
        super().__init__(parent)
        print("DEBUG: ResultWindow: __init__ が呼び出されました。")
        self.config_manager = config_manager
        
        self.setWindowTitle("翻訳結果と解説")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.FramelessWindowHint
        )
        
        # 設定マネージャーから最小サイズを取得
        min_width = self.config_manager.get("result_window.min_width")
        min_height = self.config_manager.get("result_window.min_height")
        self.setMinimumSize(min_width, min_height)
        self.setGeometry(100, 100, min_width, min_height)

        # スタイルシートは外部ファイルから読み込む
        # 相対パスを渡す
        self._load_stylesheet(os.path.join('..', 'styles', 'result_window.qss'))

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)

        # 履歴ボタンを追加
        history_button = QPushButton("履歴", self)
        history_button.setObjectName("historyButton")
        history_button.setFixedSize(60, 20)
        history_button.clicked.connect(self.show_history_signal.emit) # シグナルを発行
        header_layout.addWidget(history_button)
        
        # 設定ボタンを追加
        settings_button = QPushButton("設定", self)
        settings_button.setObjectName("settingsButton")
        settings_button.setFixedSize(60, 20)
        settings_button.clicked.connect(self.show_settings_signal.emit) # シグナルを発行
        header_layout.addWidget(settings_button)
        
        header_layout.addStretch() # 右寄せのために追加

        close_button = QPushButton("X", self)
        close_button.setObjectName("closeButton")
        close_button_size = self.config_manager.get("result_window.close_button.size")
        close_button.setFixedSize(close_button_size, close_button_size)
        close_button.clicked.connect(self.hide)
        header_layout.addWidget(close_button)

        self.translation_label = QLabel(self)
        self.translation_label.setText("翻訳結果: ")
        self.translation_label.setWordWrap(True)
        self.translation_label.setObjectName("translation_label")

        self.explanation_label = QLabel(self)
        self.explanation_label.setText("解説: ")
        self.explanation_label.setWordWrap(True)
        self.explanation_label.setObjectName("explanation_label")

        main_layout = QVBoxLayout()
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.translation_label)
        main_layout.addWidget(self.explanation_label)
        main_layout.addStretch()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)
        
        self.hide()

        # ドラッグ・リサイズ関連のフラグと位置情報
        self._resizing = False
        self._dragging = False # 新しいフラグ：ドラッグ中か
        self._resize_start_pos = None
        self._resize_start_geometry = None
        self._resize_edge = []
        self._drag_start_pos = None # 新しい変数：ドラッグ開始時のオフセット

        self.setMouseTracking(True) # マウス移動イベントを常に受け取る

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
            # ResultWindow固有の設定を上書き
            self.setWindowOpacity(self.config_manager.get("result_window.opacity"))
            print(f"DEBUG: スタイルシート '{qss_full_path}' を読み込みました。")
        except FileNotFoundError:
            print(f"ERROR: スタイルシートファイル '{qss_full_path}' が見つかりませんでした。")
        except Exception as e:
            print(f"ERROR: スタイルシートの読み込み中にエラーが発生しました: {e}")

    def update_content(self, translation, explanation):
        self.translation_label.setText(f"翻訳結果: \n{translation}")
        self.explanation_label.setText(f"解説: \n{explanation}")
        self.show()
        self.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("DEBUG: Escキーが押されました。結果ウィンドウを閉じます。")
            self.hide()

    # --- デバッグ用ログ追加 ---
    def show(self):
        print("DEBUG: ResultWindow: show() が呼び出されました。")
        super().show()

    def hide(self):
        print("DEBUG: ResultWindow: hide() が呼び出されました。")
        super().hide()

    def closeEvent(self, event):
        print("DEBUG: ResultWindow: closeEvent() が呼び出されました。")
        super().closeEvent(event)
    
    def __del__(self):
        print("DEBUG: ResultWindow: __del__() が呼び出されました。ResultWindowが破棄されています。")
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


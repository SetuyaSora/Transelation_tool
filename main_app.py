import sys
import mss
import mss.tools
import time
import os
import yaml
import os.path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMessageBox, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QSizePolicy, QDialog, QSpacerItem, QStyle
)
from PyQt5.QtCore import Qt, QRect, QTimer, QBuffer, QIODevice, QPoint, QEvent, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QCursor, QMovie 

# Gemini API のインポート
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# --- Windows API関連のインポート（エラーハンドリングを追加） ---
try:
    import win32api
    import win32con
    WIN32_AVAILABLE = True
    print("DEBUG: win32api モジュールが正常にインポートされました。")
except ImportError:
    WIN32_AVAILABLE = False
    print("ERROR: win32api モジュールが見つかりませんでした。Pywin32がインストールされているか確認してください。")
    print("コマンドプロンプトで 'pip install pywin32' を実行してください。")
    # win32apiが利用できない場合のデフォルトホットキーコードを設定
    # この場合、ホットキー機能は動作しません。
    # 代替手段として、例えばGUIボタンからの起動などを検討する必要があります。
    HOTKEY_VK_CODE_FALLBACK = None # ホットキー無効
except Exception as e:
    WIN32_AVAILABLE = False
    print(f"ERROR: win32api モジュールのインポート中に予期せぬエラーが発生しました: {e}")
    HOTKEY_VK_CODE_FALLBACK = None


# --- 設定ファイルパスと初期設定 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "setting.yaml")

# デフォルト設定 (ファイルが存在しない場合やエラーの場合に使う)
DEFAULT_SETTINGS = {
    "result_window": {
        "opacity": 0.85,
        "background_color": "rgba(40, 40, 40, 200)",
        "border_radius": 15,
        "border_color": "rgba(100, 100, 100, 150)",
        "border_width": 1,
        "min_width": 200,
        "min_height": 100,
        "translation_label": {
            "font_size": 14,
            "font_weight": "bold",
            "color": "#ADD8E6"
        },
        "explanation_label": {
            "font_size": 10,
            "font_weight": "normal",
            "color": "#C0C0C0"
        },
        "close_button": {
            "background-color": "rgba(255, 0, 0, 180)",
            "hover_color": "rgba(255, 50, 50, 220)",
            "border_radius": 10,
            "font_size": 12,
            "font_weight": "bold",
            "color": "white",
            "size": 20
        }
    },
    "hotkey": {
        "key_code": 0xA5 # 右Altキー
    },
    "gemini_settings": {
        "model_name": "gemini-1.5-flash-latest",
        "translation_prompt": """この画像は英語で表示されたゲーム画面です。含まれる全ての英語テキストを日本語に翻訳してください。ただし、ゲーム内の固有名詞（船、アイテム、勢力、地名、キャラクター名など）は翻訳せずに、元の英語をカタカナ表記にしてください。一般的な英単語でも、文脈からゲーム用語である可能性が高い場合は、無理に翻訳せずカタカナ表記にすることを優先してください。翻訳する際は、不自然な直訳にならないよう、文脈を考慮した自然な日本語への意訳を許可します。特に、ゲームのUIやメッセージとして表示されるテキストが、より自然で理解しやすい日本語になるように調整してください。

例：
- Original: Imperial Courier is best ship.
- Translation: インペリアルクーリエは最高の船だ。
- Original: THREAT LEVEL
- Translation: スレッドレベル

翻訳結果のみを最初に提供し、その後に元の英語テキストの単語や表現に関する簡単な解説を箇条書きで提供してください。
例：
翻訳結果: [翻訳]
解説:
- [元の英語]: [解説]
"""
    },
    "behavior": { # 新しい行動設定セクション
        "show_api_confirmation": True # API送信確認ダイアログの表示/非表示 (デフォルト: True)
    }
}

# --- 設定読み込み関数 ---
def load_settings():
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)
            merged_settings = DEFAULT_SETTINGS.copy()
            _deep_merge_dicts(merged_settings, settings)
            print(f"DEBUG: 設定ファイル '{SETTINGS_FILE}' を読み込みました。")
            return merged_settings
    except FileNotFoundError:
        print(f"WARNING: 設定ファイル '{SETTINGS_FILE}' が見つかりませんでした。デフォルト設定を使用します。")
        return DEFAULT_SETTINGS
    except yaml.YAMLError as e:
        print(f"ERROR: 設定ファイル '{SETTINGS_FILE}' の読み込み中にエラーが発生しました: {e}")
        return DEFAULT_SETTINGS

# 辞書を再帰的にマージするヘルパー関数
def _deep_merge_dicts(default_dict, override_dict):
    for key, value in override_dict.items():
        if key in default_dict and isinstance(default_dict[key], dict) and isinstance(value, dict):
            _deep_merge_dicts(default_dict[key], value)
        else:
            default_dict[key] = value
    return default_dict


# 初期設定の読み込み
current_settings = load_settings()
# win32apiが利用できない場合はフォールバックのキーコードを使用
HOTKEY_VK_CODE = current_settings["hotkey"]["key_code"] if WIN32_AVAILABLE else HOTKEY_VK_CODE_FALLBACK


# スクリーンショット保存フォルダの設定
OUTPUT_FOLDER = "screenshots"

# Gemini APIキーの設定 (環境変数から読み込む)
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: 環境変数 'GEMINI_API_KEY' が設定されていません。")
    print("APIキーを設定してから再度実行してください。")
    sys.exit(1)
genai.configure(api_key=API_KEY)
print("DEBUG: Gemini APIが設定されました。")

# Gemini API呼び出し用のWorkerスレッド
class GeminiWorker(QThread):
    # API処理完了時に結果を送信するシグナル
    # Arguments: translation (str), explanation (str)
    finished = pyqtSignal(str, str)
    # エラー発生時にエラーメッセージを送信するシグナル
    # Arguments: error_message (str)
    error = pyqtSignal(str)

    def __init__(self, image_data):
        super().__init__()
        self.image_data = image_data

    def run(self):
        print("DEBUG: GeminiWorker: API処理を開始します。")
        try:
            model_name = current_settings["gemini_settings"]["model_name"]
            model = genai.GenerativeModel(model_name)
            
            image_part = {
                'mime_type': 'image/png',
                'data': self.image_data
            }

            translation_prompt = current_settings["gemini_settings"]["translation_prompt"]
            prompt_parts = [
                image_part,
                translation_prompt,
            ]

            print("DEBUG: GeminiWorker: Gemini APIへリクエスト送信中...")
            response = model.generate_content(prompt_parts)
            print("DEBUG: GeminiWorker: Gemini APIからの応答を受信しました。")
            
            text_content = response.text
            
            translation = "翻訳結果が見つかりませんでした。"
            explanation = "解説が見つかりませんでした。"

            if "翻訳結果:" in text_content:
                parts = text_content.split("翻訳結果:", 1)
                translation_part = parts[1]
                if "解説:" in translation_part:
                    trans_exp_parts = translation_part.split("解説:", 1)
                    translation = trans_exp_parts[0].strip()
                    explanation = trans_exp_parts[1].strip()
                else:
                    translation = translation_part.strip()
            elif "解説:" in text_content:
                explanation = text_content.split("解説:", 1)[1].strip()
            else:
                translation = text_content.strip()

            print(f"DEBUG: GeminiWorker: 翻訳結果: {translation[:50]}...")
            print(f"DEBUG: GeminiWorker: 解説: {explanation[:50]}...")
            # Send results via signal
            self.finished.emit(translation, explanation)

        except Exception as e:
            print(f"ERROR: GeminiWorker: Gemini API処理中にエラーが発生しました: {e}")
            # Send error message via signal
            self.error.emit(f"翻訳処理中にエラーが発生しました。\n{e}")

# Window to display translation results and explanation
class ResultWindow(QWidget):
    def __init__(self):
        super().__init__()
        print("DEBUG: ResultWindow: __init__ が呼び出されました。")
        self.setWindowTitle("翻訳結果と解説")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.FramelessWindowHint
        )
        
        self.setMinimumSize(
            current_settings["result_window"]["min_width"],
            current_settings["result_window"]["min_height"]
        )
        self.setGeometry(100, 100, self.minimumSize().width(), self.minimumSize().height())

        self.apply_settings(current_settings)

        close_button = QPushButton("X", self)
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.hide)
        close_button_size = current_settings["result_window"]["close_button"]["size"]
        close_button.setFixedSize(close_button_size, close_button_size)

        header_layout = QHBoxLayout()
        header_layout.addStretch()
        header_layout.addWidget(close_button)
        header_layout.setContentsMargins(5, 5, 5, 5)

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

        self._resizing = False
        self._resize_start_pos = None
        self._resize_start_geometry = None
        self._resize_edge = []

        self.setMouseTracking(True)
        self.translation_label.setMouseTracking(True)
        self.explanation_label.setMouseTracking(True)

        self.installEventFilter(self)
        self.translation_label.installEventFilter(self)
        self.explanation_label.installEventFilter(self)

    def apply_settings(self, settings):
        self.setWindowOpacity(settings["result_window"]["opacity"])
        
        qss = f"""
            QWidget {{
                background-color: {settings["result_window"]["background_color"]};
                border-radius: {settings["result_window"]["border_radius"]}px;
                border: {settings["result_window"]["border_width"]}px solid {settings["result_window"]["border_color"]};
                color: white;
                font-family: Yu Gothic UI, Meiryo, sans-serif;
            }}
            QLabel {{
                padding: 5px;
            }}
            #translation_label {{
                font-size: {settings["result_window"]["translation_label"]["font_size"]}pt;
                font-weight: {settings["result_window"]["translation_label"]["font_weight"]};
                color: {settings["result_window"]["translation_label"]["color"]};
            }}
            #explanation_label {{
                font-size: {settings["result_window"]["explanation_label"]["font_size"]}pt;
                font-weight: {settings["result_window"]["explanation_label"]["font_weight"]};
                color: {settings["result_window"]["explanation_label"]["color"]};
            }}
            #closeButton {{
                background-color: {settings["result_window"]["close_button"]["background_color"]};
                border-radius: {settings["result_window"]["close_button"]["border_radius"]}px;
                font-size: {settings["result_window"]["close_button"]["font_size"]}pt;
                font-weight: {settings["result_window"]["close_button"]["font_weight"]};
                color: {settings["result_window"]["close_button"]["color"]};
                min-width: {settings["result_window"]["close_button"]["size"]}px;
                min-height: {settings["result_window"]["close_button"]["size"]}px;
                max-width: {settings["result_window"]["close_button"]["size"]}px;
                max-height: {settings["result_window"]["close_button"]["size"]}px;
                padding: 0px;
            }}
            #closeButton:hover {{
                background-color: {settings["result_window"]["close_button"]["hover_color"]};
            }}
        """
        self.setStyleSheet(qss)
        
        self.setMinimumSize(
            settings["result_window"]["min_width"],
            settings["result_window"]["min_height"]
        )

    def eventFilter(self, obj, event):
        if obj == self or obj == self.translation_label or obj == self.explanation_label:
            if event.type() == QEvent.MouseMove:
                if event.buttons() == Qt.LeftButton:
                    if self._resizing:
                        self._handle_resize(event.globalPos())
                    else:
                        current_cursor = self._get_cursor_shape(self.mapFromGlobal(event.globalPos()))
                        self.setCursor(current_cursor)
                        delta = QPoint(event.globalPos() - self.old_pos)
                        self.move(self.x() + delta.x(), self.y() + delta.y())
                        self.old_pos = event.globalPos()
                else:
                    local_pos = self.mapFromGlobal(event.globalPos())
                    current_cursor = self._get_cursor_shape(local_pos)
                    self.setCursor(current_cursor)
                return True
            
            elif event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    local_pos = self.mapFromGlobal(event.globalPos())
                    if self._is_at_border(local_pos):
                        self._resizing = True
                        self._resize_start_pos = event.globalPos()
                        self._resize_start_geometry = self.geometry()
                        self._resize_edge = self._get_resize_edge(local_pos)
                        self.setCursor(self._get_cursor_shape(local_pos))
                    else:
                        self._resizing = False
                        self.old_pos = event.globalPos()
                return True

            elif event.type() == QEvent.MouseButtonRelease:
                self.old_pos = None
                self._resizing = False
                self.setCursor(Qt.ArrowCursor)
                return True
            
        return QWidget.eventFilter(self, obj, event)

    def update_content(self, translation, explanation):
        self.translation_label.setText(f"翻訳結果: \n{translation}")
        self.explanation_label.setText(f"解説: \n{explanation}")
        self.show()
        self.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("DEBUG: Escキーが押されました。結果ウィンドウを閉じます。")
            self.hide()

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

# New custom message box class
class CustomMessageBox(QDialog):
    def __init__(self, parent=None, title="メッセージ", message="メッセージ", icon_type=QMessageBox.Information, buttons=QMessageBox.Ok):
        super().__init__(parent)
        print("DEBUG: CustomMessageBox: __init__ が呼び出されました。")
        self.setWindowTitle(title)
        # Set window flags to be frameless, dialog, and always on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True) # Make it a modal dialog

        self.result = QMessageBox.NoButton # Default result

        # Layout
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
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 0, 0, 180);
                border-radius: 10px;
                font-size: 10pt;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 50, 50, 220);
            }
        """)
        close_button.clicked.connect(lambda: self.done(QMessageBox.Cancel)) # Close on click
        header_layout.addWidget(close_button)
        main_layout.addLayout(header_layout)

        # Icon and message
        content_layout = QHBoxLayout()
        icon_label = QLabel(self)
        # Import QStyle here if not already imported globally
        from PyQt5.QtWidgets import QStyle 
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
        self.apply_style()

    def apply_style(self):
        # Custom dialog style
        self.setStyleSheet("""
            CustomMessageBox {
                background-color: #333333; /* Dark gray background */
                border: 1px solid #555555; /* Border */
                border-radius: 8px; /* Rounded corners */
            }
            QLabel {
                color: white; /* White text */
                font-family: Yu Gothic UI, Meiryo, sans-serif;
                font-size: 10pt; /* Message font size */
            }
            QPushButton {
                background-color: #5cb85c; /* Green button */
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 70px;
                min-height: 25px;
                font-size: 10pt; /* Button font size */
            }
            QPushButton:hover {
                background-color: #4cae4c; /* Hover color */
            }
            QPushButton:pressed {
                background-color: #449d44; /* Click color */
            }
        """)

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

# New class for loading indicator
class LoadingIndicator(QWidget):
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
        self.message_label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;")
        self.message_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.message_label)
        
        # Simple pulsating animation (can be replaced with GIF if available)
        self.setFixedSize(200, 100) # Fixed size for the loading indicator
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 200); /* Semi-transparent dark background */
                border-radius: 15px; /* Rounded corners */
            }
        """)
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


class SelectionWindow(QWidget):
    def __init__(self):
        super().__init__()
        print("DEBUG: SelectionWindow: __init__ が呼び出されました。")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.X11BypassWindowManagerHint
        )
        self.setCursor(Qt.CrossCursor)
        self.setWindowOpacity(0.2)
        self.setStyleSheet("background-color: black;")

        screen_geometry = QApplication.instance().desktop().screenGeometry()
        self.setGeometry(screen_geometry)
        print(f"DEBUG: SelectionWindow: 画面サイズを {screen_geometry.width()}x{screen_geometry.height()} に設定しました。")

        self.start_point = None
        self.end_point = None
        self.selecting = False
        self.worker_thread = None # Variable to hold GeminiWorker thread
        self.loading_indicator = LoadingIndicator(self) # Initialize loading indicator
        self.loading_indicator.hide() # Hide initially
        print("DEBUG: SelectionWindow: 初期化完了。")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.selecting = True
            self.repaint()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.end_point = event.pos()
            self.repaint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selecting:
            self.end_point = event.pos()
            self.selecting = False
            self.hide()
            print("DEBUG: mouseReleaseEvent: ウィンドウを非表示にしました。")

            if self.start_point and self.end_point:
                x1 = min(self.start_point.x(), self.end_point.x())
                y1 = min(self.start_point.y(), self.end_point.y())
                x2 = max(self.start_point.x(), self.end_point.x())
                y2 = max(self.start_point.y(), self.end_point.y())

                if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                    print("DEBUG: 選択範囲が小さすぎます。処理を中断します。")
                    self.show_custom_messagebox("エラー", "選択範囲が小さすぎます。", QMessageBox.Warning)
                    return

                # Take screenshot and save to file, then get data
                screenshot_data = self.take_selected_screenshot_in_memory(x1, y1, x2 - x1, y2 - y1)
                
                if screenshot_data:
                    # Check if confirmation dialog should be shown
                    if current_settings["behavior"]["show_api_confirmation"]:
                        dialog = CustomMessageBox(
                            self,
                            "API送信確認",
                            "スクリーンショットをGemini APIに送信して翻訳しますか？",
                            QMessageBox.Question,
                            QMessageBox.Yes | QMessageBox.No
                        )
                        reply = dialog.exec_() # Show as modal
                    else:
                        reply = QMessageBox.Yes # If not showing dialog, assume YES to proceed

                    if reply == QMessageBox.Yes:
                        print("DEBUG: API送信が承認されました。")
                        self.loading_indicator.show() # Show loading indicator
                        # Start asynchronous API processing
                        self.worker_thread = GeminiWorker(screenshot_data)
                        self.worker_thread.finished.connect(self.on_gemini_finished)
                        self.worker_thread.error.connect(self.on_gemini_error)
                        self.worker_thread.start()
                    else:
                        print("DEBUG: API送信がキャンセルされました。")
                else:
                    self.show_custom_messagebox("エラー", "スクリーンショットの取得に失敗しました。", QMessageBox.Critical)
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("DEBUG: Escキーが押されました。選択をキャンセルします。")
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.selecting and self.start_point and self.end_point:
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(QColor(255, 255, 255, 50))
            painter.drawRect(rect)

    def take_selected_screenshot_in_memory(self, x, y, width, height):
        print(f"DEBUG: take_selected_screenshot: スクリーンショット範囲 ({x},{y},{width},{height})")
        
        # Create screenshot save folder if it does not exist
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
            print(f"DEBUG: フォルダ '{OUTPUT_FOLDER}' を作成しました。")

        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": width, "height": height}
            sct_img = sct.grab(monitor)

            from PIL import Image
            img_pil = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            
            # Use timestamp for filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(OUTPUT_FOLDER, filename)

            try:
                img_pil.save(filepath, "PNG")
                print(f"DEBUG: スクリーンショットをファイルに保存しました: {filepath}")
            except Exception as e:
                print(f"ERROR: スクリーンショットのファイル保存中にエラーが発生しました: {e}")
                return None # Return None on save failure

            byte_array = QBuffer()
            byte_array.open(QIODevice.WriteOnly)
            img_pil.save(byte_array, "PNG")
            print("DEBUG: スクリーンショットをメモリに取得しました。")
            return byte_array.buffer().data()

    def on_gemini_finished(self, translation, explanation):
        """Slot called when Gemini API processing is complete"""
        self.loading_indicator.hide() # Hide loading indicator
        if result_window:
            result_window.update_content(translation, explanation)
            result_window.show()
            result_window.raise_()
            result_window.activateWindow()
        else:
            # Display information dialog if result_window does not exist
            self.show_custom_messagebox("翻訳結果", f"翻訳結果:\n{translation}\n\n解説:\n{explanation}", QMessageBox.Information)

    def on_gemini_error(self, error_message):
        """Slot called when an error occurs during Gemini API processing"""
        self.loading_indicator.hide() # Hide loading indicator on error
        self.show_custom_messagebox("エラー", error_message, QMessageBox.Critical)

    def show_custom_messagebox(self, title, message, icon_type, buttons=QMessageBox.Ok):
        """
        Function to display a custom message box.
        Uses the CustomMessageBox class.
        """
        dialog = CustomMessageBox(self, title, message, icon_type, buttons)
        return dialog.exec_()


# --- Main application code ---

app = None
selection_window = None
result_window = None
hotkey_timer = None

def check_hotkey():
    # win32apiが利用可能な場合のみホットキーをチェック
    if WIN32_AVAILABLE:
        if win32api.GetAsyncKeyState(HOTKEY_VK_CODE) & 0x8000:
            if not selection_window.isVisible():
                print("DEBUG: ホットキー検出！範囲選択を開始します。")
                selection_window.showFullScreen()
                selection_window.raise_()
                selection_window.activateWindow()
                if QApplication.instance():
                    QApplication.instance().processEvents()
    else:
        # win32apiが利用できない場合はホットキー機能が無効であることをユーザーに通知
        print("WARNING: ホットキー機能は無効です。pywin32ライブラリがインストールされていません。")


if __name__ == "__main__":
    print("DEBUG: メインスクリプト開始。")
    
    if not os.getenv("GEMINI_API_KEY"):
        load_dotenv()
        if not os.getenv("GEMINI_API_KEY"):
            print("ERROR: 環境変数 'GEMINI_API_KEY' が設定されていません。")
            print("APIキーを設定してから再度実行してください。")
            sys.exit(1)

    app = QApplication(sys.argv)
    print("DEBUG: QApplicationインスタンスを作成しました。")
    
    selection_window = SelectionWindow()
    selection_window.hide()
    print("DEBUG: SelectionWindowインスタンスを作成し、非表示にしました。")

    result_window = ResultWindow()
    print("DEBUG: ResultWindowインスタンスを作成し、非表示にしました。")

    hotkey_timer = QTimer()
    hotkey_timer.timeout.connect(check_hotkey)
    hotkey_timer.start(100)

    print("ショートカットキー（右Altキー）を監視中です... (ポーリング方式)")
    print("Ctrl+Cでプログラムを終了できます。")

    # win32apiが利用できない場合は、ホットキー以外の起動方法を案内
    if not WIN32_AVAILABLE:
        print("注意: pywin32ライブラリがインストールされていないため、ホットキーは動作しません。")
        print("手動で 'python main_app.py' を実行し、範囲選択ツールを直接起動してください。")


    sys.exit(app.exec_())
    print("DEBUG: QApplicationのイベントループが終了しました。")

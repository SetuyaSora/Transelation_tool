import sys
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu, QAction # QSystemTrayIcon, QMenu, QAction を追加
from PyQt5.QtCore import QTimer, Qt # Qt を追加
from PyQt5.QtGui import QIcon # QIcon を追加
import logging

# 分割したモジュールをインポート
from src.config.config_manager import ConfigManager
from src.utils.helper_functions import hotkey_signal, set_global_hotkey, get_key_name_from_vk_code
from src.utils.logger_config import configure_logging

from src.windows.selection_window import SelectionWindow
from src.windows.result_window import ResultWindow
from src.windows.history_window import HistoryWindow
from src.windows.settings_window import SettingsWindow

# --- ログ設定の初期化 (アプリケーションの最初に呼び出す) ---
configure_logging(log_dir="logs", log_file_name="app.log", log_level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- 定数の定義 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "setting.yaml")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "translation_history.json")
OUTPUT_FOLDER = "screenshots"
APP_ICON_PATH = os.path.join(SCRIPT_DIR, "app_icon.ico") # アイコンファイルのパス

# --- 環境変数のロード ---
load_dotenv()

# --- ConfigManagerの初期化 ---
config_manager = ConfigManager(SETTINGS_FILE)

# ConfigManagerにOUTPUT_FOLDERをセット (設定ファイルにない場合に追加)
if config_manager.get("OUTPUT_FOLDER") is None:
    config_manager.set("OUTPUT_FOLDER", OUTPUT_FOLDER)
    config_manager.save_settings()

# ホットキーの仮想キーコードをConfigManagerから取得
HOTKEY_VK_CODE = config_manager.get("hotkey.key_code")

# --- Gemini APIキーの設定 ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logger.error("環境変数 'GEMINI_API_KEY' が設定されていません。")
    logger.error("APIキーを設定してから再度実行してください。")
    sys.exit(1)
genai.configure(api_key=API_KEY)
logger.info("Gemini APIが設定されました。")

# --- アプリケーションのメインロジック ---
app = None
selection_window = None
result_window = None
history_window = None
settings_window = None
tray_icon = None # システムトレイアイコンのグローバル参照

def on_hotkey_pressed():
    """グローバルホットキーが押されたときに呼び出されるスロット。"""
    if not selection_window.isVisible():
        logger.debug("ホットキー検出！範囲選択を開始します。")
        selection_window.showFullScreen()
        selection_window.raise_()
        selection_window.activateWindow()

def show_settings_dialog():
    """設定ウィンドウをモーダル表示するヘルパー関数。"""
    global settings_window
    if settings_window:
        logger.debug("show_settings_dialog: 設定ウィンドウをモーダル表示します。")
        settings_window.exec_()
        logger.debug("show_settings_dialog: 設定ウィンドウが閉じられました。")
        if result_window.isVisible():
            logger.debug("show_settings_dialog: result_window は表示されています。最前面に持っていきます。")
            result_window.raise_()
            result_window.activateWindow()
        else:
            logger.debug("show_settings_dialog: result_window は表示されていませんでした。")
    else:
        logger.error("show_settings_dialog: settings_window が初期化されていません。")

def show_result_window_from_tray():
    """システムトレイから翻訳結果ウィンドウを表示する。"""
    if result_window:
        logger.info("システムトレイから翻訳結果ウィンドウを表示します。")
        result_window.show()
        result_window.raise_()
        result_window.activateWindow()
    else:
        logger.warning("result_window が初期化されていないため、表示できません。")

def hide_result_window_to_tray():
    """翻訳結果ウィンドウを非表示にしてシステムトレイに送る。"""
    if result_window:
        logger.info("翻訳結果ウィンドウを非表示にしてシステムトレイに送ります。")
        result_window.hide()
    else:
        logger.warning("result_window が初期化されていないため、非表示にできません。")

def quit_application():
    """アプリケーションを完全に終了する。"""
    logger.info("アプリケーションを終了します。")
    if tray_icon:
        tray_icon.hide() # トレイアイコンを非表示にする
    QApplication.quit() # アプリケーションを終了

if __name__ == "__main__":
    logger.info("メインスクリプト開始。")
    
    app = QApplication(sys.argv)
    # 最後のウィンドウが閉じられてもアプリが終了しないように設定
    # システムトレイアイコンを使用する場合、これをFalseに設定することが重要
    app.setQuitOnLastWindowClosed(False)
    
    # アプリケーションアイコンの設定
    if os.path.exists(APP_ICON_PATH):
        app.setWindowIcon(QIcon(APP_ICON_PATH))
        logger.info(f"アプリケーションアイコンを '{APP_ICON_PATH}' に設定しました。")
    else:
        logger.warning(f"アプリケーションアイコンファイル '{APP_ICON_PATH}' が見つかりませんでした。デフォルトアイコンを使用します。")

    logger.info("QApplicationインスタンスを作成しました。")
    
    result_window = ResultWindow(config_manager=config_manager)
    result_window.hide()
    logger.info("ResultWindowインスタンスを作成し、非表示にしました。")

    history_window = HistoryWindow(history_file_path=HISTORY_FILE)
    history_window.hide()
    logger.info("HistoryWindowインスタンスを作成し、非表示にしました。")

    settings_window = SettingsWindow(parent=None, config_manager=config_manager)
    settings_window.hide()
    logger.info("SettingsWindowインスタンスを作成し、非表示にしました。")

    selection_window = SelectionWindow(
        config_manager=config_manager,
        history_file_path=HISTORY_FILE,
        result_window=result_window
    )
    selection_window.hide()
    logger.info("SelectionWindowインスタンスを作成し、非表示にしました。")

    # --- システムトレイアイコンの設定 ---
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = QSystemTrayIcon(app.windowIcon(), app) # アプリケーションアイコンを使用
        tray_icon.setToolTip("スクリーンショット翻訳ツール")

        # コンテキストメニューの作成
        tray_menu = QMenu()
        show_action = QAction("表示", app)
        show_action.triggered.connect(show_result_window_from_tray)
        tray_menu.addAction(show_action)

        hide_action = QAction("非表示", app)
        hide_action.triggered.connect(hide_result_window_to_tray)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator() # 区切り線

        quit_action = QAction("終了", app)
        quit_action.triggered.connect(quit_application)
        tray_menu.addAction(quit_action)

        tray_icon.setContextMenu(tray_menu)

        # クリックイベントの接続 (左クリックで表示/非表示を切り替える)
        tray_icon.activated.connect(lambda reason: show_result_window_from_tray() if reason == QSystemTrayIcon.Trigger else None)
        
        tray_icon.show()
        logger.info("システムトレイアイコンが作成され、表示されました。")
    else:
        logger.warning("システムトレイが利用できません。システムトレイアイコンは表示されません。")
    # --- システムトレイアイコンの設定ここまで ---


    result_window.show_history_signal.connect(history_window.show)
    result_window.show_settings_signal.connect(show_settings_dialog)
    
    settings_window.settings_saved.connect(lambda: config_manager.reload())
    settings_window.settings_saved.connect(
        lambda: logger.debug(f"設定が保存されました。新しいホットキー: 0x{config_manager.get('hotkey.key_code'):X}")
    )
    settings_window.settings_saved.connect(lambda: set_global_hotkey(config_manager.get("hotkey.key_code")))

    hotkey_signal.hotkey_pressed.connect(on_hotkey_pressed)

    set_global_hotkey(HOTKEY_VK_CODE)

    logger.info(f"ショートカットキー（現在の設定: {get_key_name_from_vk_code(HOTKEY_VK_CODE)}）を監視中です...")
    logger.info("Ctrl+Cでプログラムを終了できます。")
    
    sys.exit(app.exec_())
    logger.info("QApplicationのイベントループが終了しました。")


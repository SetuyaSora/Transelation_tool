import sys
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu, QAction, QStyle # QStyle を追加
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon
import logging
import json

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
# アプリケーションのベースディレクトリを決定
if getattr(sys, 'frozen', False):
    APP_BASE_DIR = os.path.dirname(sys.executable)
else:
    APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(APP_BASE_DIR, "setting.yaml")
HISTORY_FILE = os.path.join(APP_BASE_DIR, "translation_history.json")
OUTPUT_FOLDER = os.path.join(APP_BASE_DIR, "screenshots")

APP_ICON_PATH = os.path.join(APP_BASE_DIR, "app_icon.ico")

# --- 環境変数のロード ---
load_dotenv()

# --- ConfigManagerの初期化 ---
config_manager = ConfigManager(SETTINGS_FILE)

# setting.yaml が存在しない場合、または OUTPUT_FOLDER が設定されていない場合に保存を強制
if not os.path.exists(SETTINGS_FILE) or \
   config_manager.get("OUTPUT_FOLDER") is None or not os.path.isabs(config_manager.get("OUTPUT_FOLDER")):
    logger.info("setting.yaml が存在しないか、初期設定が不完全なため、デフォルト設定を保存します。")
    config_manager.set("OUTPUT_FOLDER", OUTPUT_FOLDER)
    config_manager.save_settings()
    config_manager.reload()

# translation_history.json が存在しない場合、空のファイルとして生成
if not os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        logger.info(f"translation_history.json が存在しないため、空のファイルを生成しました: {HISTORY_FILE}")
    except Exception as e:
        logger.exception(f"translation_history.json の生成中にエラーが発生しました: {HISTORY_FILE}")


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
tray_icon = None

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
        tray_icon.hide()
    QApplication.quit()

if __name__ == "__main__":
    logger.info("メインスクリプト開始。")
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # --- アプリケーションアイコンとシステムトレイアイコンの堅牢な設定 ---
    app_icon = None
    if os.path.exists(APP_ICON_PATH):
        app_icon = QIcon(APP_ICON_PATH)
        app.setWindowIcon(app_icon)
        logger.info(f"アプリケーションアイコンを '{APP_ICON_PATH}' に設定しました。")
    else:
        logger.warning(f"アプリケーションアイコンファイル '{APP_ICON_PATH}' が見つかりませんでした。")
        # フォールバックとしてQtの標準アイコンを使用
        app_icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon) # または SP_DesktopIcon など
        app.setWindowIcon(app_icon)
        logger.info("デフォルトのQt標準アイコンをアプリケーションアイコンとして設定しました。")


    logger.info("QApplicationインスタンスを作成しました。")
    
    result_window = ResultWindow(config_manager=config_manager)
    result_window.hide() # main_app_file_generation_fix の状態に戻すため、このまま
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

    if QSystemTrayIcon.isSystemTrayAvailable():
        # システムトレイアイコンには、app_iconが有効であればそれを使用、そうでなければデフォルトのQtアイコンを使用
        tray_icon_to_use = app_icon if app_icon and not app_icon.isNull() else QApplication.style().standardIcon(QStyle.SP_MessageBoxInformation)
        
        tray_icon = QSystemTrayIcon(tray_icon_to_use, app)
        tray_icon.setToolTip("スクリーンショット翻訳ツール")

        tray_menu = QMenu()
        show_action = QAction("表示", app)
        show_action.triggered.connect(show_result_window_from_tray)
        tray_menu.addAction(show_action)

        hide_action = QAction("非表示", app)
        hide_action.triggered.connect(hide_result_window_to_tray)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("終了", app)
        quit_action.triggered.connect(quit_application)
        tray_menu.addAction(quit_action)

        tray_icon.setContextMenu(tray_menu)
        tray_icon.activated.connect(lambda reason: show_result_window_from_tray() if reason == QSystemTrayIcon.Trigger else None)
        
        tray_icon.show()
        logger.info("システムトレイアイコンが作成され、表示されました。")
    else:
        logger.warning("システムトレイが利用できません。システムトレイアイコンは表示されません。")


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


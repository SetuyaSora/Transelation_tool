import sys
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

# 分割したモジュールをインポート
from src.config.config_manager import ConfigManager
from src.utils.helper_functions import hotkey_signal, set_global_hotkey, get_key_name_from_vk_code

from src.windows.selection_window import SelectionWindow
from src.windows.result_window import ResultWindow
from src.windows.history_window import HistoryWindow
from src.windows.settings_window import SettingsWindow

# --- 定数の定義 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "setting.yaml")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "translation_history.json")
OUTPUT_FOLDER = "screenshots" # スクリーンショット保存フォルダ

# --- 環境変数のロード ---
load_dotenv()

# --- ConfigManagerの初期化 ---
config_manager = ConfigManager(SETTINGS_FILE)

# ConfigManagerにOUTPUT_FOLDERをセット (設定ファイルにない場合に追加)
if config_manager.get("OUTPUT_FOLDER") is None:
    config_manager.set("OUTPUT_FOLDER", OUTPUT_FOLDER)
    config_manager.save_settings() # 新しい設定を保存

# ホットキーの仮想キーコードをConfigManagerから取得
HOTKEY_VK_CODE = config_manager.get("hotkey.key_code")

# --- Gemini APIキーの設定 ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: 環境変数 'GEMINI_API_KEY' が設定されていません。")
    print("APIキーを設定してから再度実行してください。")
    sys.exit(1)
genai.configure(api_key=API_KEY)
print("DEBUG: Gemini APIが設定されました。")

# --- アプリケーションのメインロジック ---
app = None
selection_window = None
result_window = None
history_window = None
settings_window = None

def on_hotkey_pressed():
    """グローバルホットキーが押されたときに呼び出されるスロット。"""
    if not selection_window.isVisible():
        print("DEBUG: ホットキー検出！範囲選択を開始します。")
        selection_window.showFullScreen()
        selection_window.raise_()
        selection_window.activateWindow()


def show_settings_dialog():
    """設定ウィンドウをモーダル表示するヘルパー関数。"""
    global settings_window # グローバル変数として参照
    if settings_window:
        print("DEBUG: show_settings_dialog: 設定ウィンドウをモーダル表示します。")
        settings_window.exec_() # モーダル表示
        print("DEBUG: show_settings_dialog: 設定ウィンドウが閉じられました。")
        # settings_window.exec_() が完了したら、result_window は通常表示されたままのはず
        # 念のため、result_window を最前面に持ってくる
        if result_window.isVisible():
            print("DEBUG: show_settings_dialog: result_window は表示されています。最前面に持っていきます。")
            result_window.raise_()
            result_window.activateWindow()
        else:
            print("DEBUG: show_settings_dialog: result_window は表示されていませんでした。")
    else:
        print("ERROR: show_settings_dialog: settings_window が初期化されていません。")


if __name__ == "__main__":
    print("DEBUG: メインスクリプト開始。")
    
    app = QApplication(sys.argv)
    # 最後のウィンドウが閉じられてもアプリが終了しないように設定
    app.setQuitOnLastWindowClosed(False) # ここを追加！
    print("DEBUG: QApplicationインスタンスを作成しました。")
    
    # 各ウィンドウインスタンスの作成とConfigManager、履歴ファイルパスの引き渡し
    result_window = ResultWindow(config_manager=config_manager)
    result_window.hide()
    print("DEBUG: ResultWindowインスタンスを作成し、非表示にしました。")

    history_window = HistoryWindow(history_file_path=HISTORY_FILE)
    history_window.hide()
    print("DEBUG: HistoryWindowインスタンスを作成し、非表示にしました。")

    # SettingsWindowにはparent=Noneを指定し、独立したトップレベルウィンドウにする
    settings_window = SettingsWindow(parent=None, config_manager=config_manager) # parent=None に変更！
    settings_window.hide()
    print("DEBUG: SettingsWindowインスタンスを作成し、非表示にしました。")

    # SelectionWindowにはresult_windowの参照も渡す
    selection_window = SelectionWindow(
        config_manager=config_manager,
        history_file_path=HISTORY_FILE,
        result_window=result_window # ここでresult_windowを渡す
    )
    selection_window.hide()
    print("DEBUG: SelectionWindowインスタンスを作成し、非表示にしました。")

    # ウィンドウ間のシグナル接続
    result_window.show_history_signal.connect(history_window.show)
    # settings_window.show() の代わりに show_settings_dialog() を接続
    result_window.show_settings_signal.connect(show_settings_dialog)
    
    # settings_window.finished.connect(result_window.show) は不要になるので削除
    # result_window.show_settings_signal.connect(show_settings_dialog) で exec_() がブロックするため、
    # その後の result_window.show() は show_settings_dialog 内で行う

    # 設定が保存されたら、ConfigManagerをリロードして最新の設定を反映させる
    settings_window.settings_saved.connect(lambda: config_manager.reload())
    settings_window.settings_saved.connect(
        lambda: print(f"DEBUG: 設定が保存されました。新しいホットキー: 0x{config_manager.get('hotkey.key_code'):X}")
    )
    # 設定が保存されたらグローバルホットキーを更新
    settings_window.settings_saved.connect(lambda: set_global_hotkey(config_manager.get("hotkey.key_code")))

    # pynputのホットキーシグナルとSelectionWindowの表示を接続
    hotkey_signal.hotkey_pressed.connect(on_hotkey_pressed)

    # アプリケーション起動時にグローバルホットキーリスナーを開始
    set_global_hotkey(HOTKEY_VK_CODE) # 初期ホットキーを設定

    print(f"ショートカットキー（現在の設定: {get_key_name_from_vk_code(HOTKEY_VK_CODE)}）を監視中です...")
    print("Ctrl+Cでプログラムを終了できます。")
    
    sys.exit(app.exec_())
    print("DEBUG: QApplicationのイベントループが終了しました。")


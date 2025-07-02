import os
import json
import datetime
import logging # logging モジュールを追加
from pynput import keyboard
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QMetaObject, Q_ARG, QGenericArgument # QMetaObject, Q_ARG, QGenericArgument を追加

logger = logging.getLogger(__name__) # このモジュール用のロガーを取得

# --- ホットキーの状態を通知するためのシグナルクラス ---
class HotkeySignal(QObject):
    hotkey_pressed = pyqtSignal()
    key_captured = pyqtSignal(int) # 新しいホットキー設定用

hotkey_signal = HotkeySignal()

# --- win32api の利用可能性チェック (pynputは内部でwin32apiを使う場合があるため、念のため) ---
# pynputが提供するキーコード変換に依存するため、このWIN32_AVAILABLEは主に情報提供用
WIN32_AVAILABLE = True # pynputがWindowsで動作する限りTrueとみなす

# --- 翻訳履歴の保存/読み込み関数 ---
def save_translation_history(history_file_path, history_data):
    """翻訳履歴データをファイルに保存する。"""
    try:
        with open(history_file_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)
        logger.debug(f"翻訳履歴を '{history_file_path}' に保存しました。")
    except Exception as e:
        logger.exception(f"翻訳履歴の保存中にエラーが発生しました。")

def load_translation_history(history_file_path):
    """翻訳履歴データをファイルから読み込む。"""
    history = []
    if os.path.exists(history_file_path):
        try:
            with open(history_file_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            logger.debug(f"翻訳履歴を '{history_file_path}' から読み込みました。")
        except json.JSONDecodeError as e:
            logger.error(f"翻訳履歴ファイル '{history_file_path}' の読み込み中にJSONデコードエラーが発生しました: {e}")
        except Exception as e:
            logger.exception(f"翻訳履歴の読み込み中にエラーが発生しました。")
    return history

def add_translation_entry(history_data, original_text, translation, explanation):
    """新しい翻訳エントリを履歴に追加する。"""
    new_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "original_text": original_text,
        "translation": translation,
        "explanation": explanation
    }
    history_data.append(new_entry)
    logger.debug("新しい翻訳エントリを履歴に追加しました。")

# --- pynputのキーオブジェクトからVKコードとキー名を取得するヘルパー関数 ---
def get_vk_code_from_key(key):
    """pynputのKeyオブジェクトから仮想キーコード（Windows）を取得する。"""
    try:
        if isinstance(key, keyboard.KeyCode):
            return key.vk
        elif isinstance(key, keyboard.Key):
            return key.value.vk if hasattr(key.value, 'vk') else None
        else:
            return None
    except Exception as e:
        logger.debug(f"キーコード変換中にエラーが発生しました: {e}")
        return None

def get_key_name_from_vk_code(vk_code):
    """仮想キーコードから人間が読めるキー名を取得する (pynputベース)。"""
    if vk_code is None:
        return "None"

    # pynputのKey enum を逆引きして名前を取得
    for key_name, key_obj in keyboard.Key.__members__.items():
        if hasattr(key_obj.value, 'vk') and key_obj.value.vk == vk_code:
            return key_name.replace('_', ' ').capitalize()

    # その他のよく使うキーの静的マップ
    common_keys = {
        0x20: "Space", # VK_SPACE
        0x0D: "Enter", # VK_RETURN
        0x1B: "Esc",   # VK_ESCAPE
        0x09: "Tab",   # VK_TAB
        0x08: "Backspace", # VK_BACK
        0x2D: "Insert", # VK_INSERT
        0x2E: "Delete", # VK_DELETE
        0x24: "Home",   # VK_HOME
        0x23: "End",    # VK_END
        0x21: "PageUp", # VK_PRIOR
        0x22: "PageDown", # VK_NEXT
        0x25: "Left Arrow", # VK_LEFT
        0x27: "Right Arrow", # VK_RIGHT
        0x26: "Up Arrow", # VK_UP
        0x28: "Down Arrow", # VK_DOWN
        0xA4: "左Alt", # VK_LMENU (Left Alt)
        0xA5: "右Alt", # VK_RMENU (Right Alt)
        0xA0: "左Shift", # VK_LSHIFT
        0xA1: "右Shift", # VK_RSHIFT
        0xA2: "左Ctrl", # VK_LCONTROL
        0xA3: "右Ctrl", # VK_RCONTROL
        0x5B: "左Win", # VK_LWIN
        0x5C: "右Win", # VK_RWIN
    }
    name = common_keys.get(vk_code)
    if name:
        return name

    # 数字キー 0-9
    if vk_code >= 0x30 and vk_code <= 0x39: return str(vk_code - 0x30)
    
    # アルファベット A-Z
    if vk_code >= 0x41 and vk_code <= 0x5A: return chr(vk_code)
    
    # ファンクションキー F1-F24
    if vk_code >= 0x70 and vk_code <= 0x87:
        return f"F{vk_code - 0x70 + 1}"

    return f"不明なキー (0x{vk_code:X})"


# --- グローバルホットキーリスナー ---
_global_listener = None
_hotkey_vk_code = None

def on_press_global(key):
    global _hotkey_vk_code
    try:
        vk_code = get_vk_code_from_key(key)
        if vk_code == _hotkey_vk_code:
            logger.debug(f"グローバルホットキー ({get_key_name_from_vk_code(vk_code)}) が押されました。")
            QMetaObject.invokeMethod(hotkey_signal, 'hotkey_pressed', Qt.QueuedConnection)
            
    except AttributeError:
        logger.debug(f"on_press_global: 属性エラー (おそらく特殊キー): {key}")
    except Exception as e:
        logger.exception(f"on_press_global中に予期せぬエラーが発生しました。")

def set_global_hotkey(vk_code):
    """グローバルホットキーを設定し、リスナーを再起動する。"""
    global _global_listener, _hotkey_vk_code
    _hotkey_vk_code = vk_code
    
    if _global_listener:
        _global_listener.stop()
        _global_listener.join()
        logger.debug("既存のグローバルホットキーリスナーを停止しました。")

    if _hotkey_vk_code is not None:
        _global_listener = keyboard.Listener(on_press=on_press_global)
        _global_listener.start()
        logger.info(f"グローバルホットキーリスナーを開始しました。ホットキー: {get_key_name_from_vk_code(_hotkey_vk_code)}")
    else:
        logger.info("ホットキーが設定されていないため、グローバルホットキーリスナーは開始されません。")


# --- ホットキーキャプチャリスナー (設定ウィンドウ用) ---
class HotkeyCaptureListener:
    def __init__(self):
        self.listener = None
        self.captured_key_vk = None
        self.callback = None
        self._running = False

    def start_capture(self, callback):
        """キーキャプチャを開始する。キャプチャしたキーはcallbackで通知される。"""
        if self._running:
            logger.warning("HotkeyCaptureListener: 既にキャプチャ中です。")
            return

        self.callback = callback
        self.captured_key_vk = None
        self._running = True
        
        self.listener = keyboard.Listener(
            on_press=self._on_press_capture,
            suppress=True # キャプチャ中はキー入力を抑制
        )
        self.listener.start()
        logger.debug("HotkeyCaptureListener: キーキャプチャを開始しました。")

    def _on_press_capture(self, key):
        """キーキャプチャ中のキー押下イベントハンドラ。"""
        if not self._running:
            return

        vk_code = get_vk_code_from_key(key)
        
        # 修飾キー単独でのホットキー設定を避ける
        modifier_vks = [
            getattr(keyboard.Key, 'shift', None),
            getattr(keyboard.Key, 'ctrl', None),
            getattr(keyboard.Key, 'alt', None),
            getattr(keyboard.Key, 'cmd', None) # Windowsキー
        ]
        modifier_vk_codes = [get_vk_code_from_key(mod) for mod in modifier_vks if mod is not None]
        
        if vk_code in modifier_vk_codes:
            logger.debug(f"HotkeyCaptureListener: 修飾キー {get_key_name_from_vk_code(vk_code)} が単独で押されました。無視します。")
            return
        
        if vk_code is not None:
            self.captured_key_vk = vk_code
            self.stop_capture()
            QMetaObject.invokeMethod(hotkey_signal, 'key_captured', Qt.QueuedConnection,
                                     Q_ARG(int, self.captured_key_vk))


    def stop_capture(self):
        """キーキャプチャを停止する。"""
        if self._running:
            if self.listener:
                self.listener.stop()
                self.listener.join()
                self.listener = None
            self._running = False
            logger.debug("HotkeyCaptureListener: キーキャプチャを停止しました。")
        self.callback = None


import os
import yaml
import logging # logging モジュールを追加

logger = logging.getLogger(__name__) # このモジュール用のロガーを取得

class ConfigManager:
    """
    アプリケーションの設定を管理するクラス。
    setting.yaml ファイルの読み込み、保存、デフォルト設定の提供を行う。
    """
    
    # デフォルト設定
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
            "key_code": 0xA5 # 右Altキーの仮想キーコード (pynputでも共通)
        },
        "gemini_settings": {
            "mode": "translation", # 新しいモード設定: "translation" または "explanation"
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
""",
            "explanation_prompt": """この画像はゲーム画面です。写っている英語テキストを元に、ゲーム内のアイテム、スキル、キャラクター、場所、イベントなどについて詳しく日本語で解説してください。特に以下の点を重視してください。
- 名称の確認とカタカナ表記（公式名称があれば優先）
- 用途や効果、機能（具体的な数値や条件があればそれも）
- 入手方法、出現場所、関連イベント
- 関連する他の要素（組み合わせると強いアイテム、関連キャラクターなど）

解説は、まるで攻略サイトの記事のように分かりやすく、かつ正確であることを目指してください。不正確な情報や憶測は避け、客観的な情報を提供してください。もし情報が不足している場合は、その旨を明記してください。

解説:
- [対象の名称]: [詳細な解説]
"""
        },
        "behavior": {
            "show_api_confirmation": True
        },
        "ocr_settings": {
            "tesseract_path": None,
            "lang": "eng+jpn",
            "config": "--psm 3"
        }
    }

    def __init__(self, settings_file_path):
        self.settings_file_path = settings_file_path
        self._settings_data = self._load_settings()
        logger.debug(f"ConfigManager: 設定ファイル '{self.settings_file_path}' から設定をロードしました。")

    def _load_settings(self):
        """設定ファイルを読み込み、デフォルト設定とマージする。"""
        try:
            with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                user_settings = yaml.safe_load(f)
            merged_settings = self.DEFAULT_SETTINGS.copy()
            self._deep_merge_dicts(merged_settings, user_settings)
            return merged_settings
        except FileNotFoundError:
            logger.warning(f"設定ファイル '{self.settings_file_path}' が見つかりませんでした。デフォルト設定を使用します。")
            return self.DEFAULT_SETTINGS.copy()
        except yaml.YAMLError as e:
            logger.exception(f"設定ファイル '{self.settings_file_path}' の読み込み中にエラーが発生しました。")
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """現在の設定データをファイルに保存する。"""
        try:
            with open(self.settings_file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self._settings_data, f, allow_unicode=True, indent=4)
            logger.debug(f"ConfigManager: 設定を '{self.settings_file_path}' に保存しました。")
        except Exception as e:
            logger.exception(f"ConfigManager: 設定の保存中にエラーが発生しました。")

    def get(self, key_path, default=None):
        """
        設定値を取得する。ネストされたキーに対応。
        例: config_manager.get("result_window.opacity")
        """
        keys = key_path.split('.')
        current_value = self._settings_data
        try:
            for key in keys:
                current_value = current_value[key]
            return current_value
        except (KeyError, TypeError):
            logger.warning(f"ConfigManager: 設定キーパス '{key_path}' が見つかりませんでした。デフォルト値 '{default}' を使用します。")
            return default

    def set(self, key_path, value):
        """
        設定値を設定する。ネストされたキーに対応。
        例: config_manager.set("hotkey.key_code", 0x20)
        """
        keys = key_path.split('.')
        current_dict = self._settings_data
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                current_dict[key] = value
            else:
                if key not in current_dict or not isinstance(current_dict[key], dict):
                    current_dict[key] = {}
                current_dict = current_dict[key]
        logger.debug(f"ConfigManager: 設定 '{key_path}' を '{value}' に更新しました。")

    def _deep_merge_dicts(self, default_dict, override_dict):
        """辞書を再帰的にマージするヘルパー関数。"""
        for key, value in override_dict.items():
            if key in default_dict and isinstance(default_dict[key], dict) and isinstance(value, dict):
                self._deep_merge_dicts(default_dict[key], value)
            else:
                default_dict[key] = value
        return default_dict

    def reload(self):
        """設定をファイルから再ロードする。"""
        self._settings_data = self._load_settings()
        logger.debug("ConfigManager: 設定を再ロードしました。")


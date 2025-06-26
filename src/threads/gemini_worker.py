from PyQt5.QtCore import QThread, pyqtSignal
import google.generativeai as genai

# src/config/config_managerから設定マネージャーをインポート
# main_app.pyでConfigManagerのインスタンスが作成され、それが渡されることを想定
# ここではimport文のみ記述し、ConfigManagerのインスタンスは外部から注入される
from src.config.config_manager import ConfigManager # インポートを追加
from src.utils.helper_functions import add_translation_entry, save_translation_history # 履歴関連関数をインポート

class GeminiWorker(QThread):
    """
    Gemini APIを非同期で呼び出し、翻訳処理を行うWorkerスレッド。
    """
    # API処理完了時に結果を送信するシグナル
    # Arguments: original_text (str), translation (str), explanation (str)
    finished = pyqtSignal(str, str, str)
    # エラー発生時にエラーメッセージを送信するシグナル
    # Arguments: error_message (str)
    error = pyqtSignal(str)

    def __init__(self, image_data, config_manager: ConfigManager, history_file_path: str): # config_managerとhistory_file_pathを引数に追加
        super().__init__()
        self.image_data = image_data
        self.config_manager = config_manager # ConfigManagerのインスタンスを保持
        self.history_file_path = history_file_path
        self._current_translation_history = [] # 履歴を保持する内部リスト。後でload_translation_historyで初期化

    def run(self):
        print("DEBUG: GeminiWorker: API処理を開始します。")
        original_text = "N/A" # デフォルト値

        # 履歴をロード（スレッド内で直接ロードしない）
        # self._current_translation_history = load_translation_history(self.history_file_path)

        try:
            model_name = self.config_manager.get("gemini_settings.model_name") # ConfigManagerから設定を取得
            # APIキーはmain_app.pyでgenai.configureされているため、ここでは不要

            model = genai.GenerativeModel(model_name)
            
            image_part = {
                'mime_type': 'image/png',
                'data': self.image_data
            }

            translation_prompt = self.config_manager.get("gemini_settings.translation_prompt") # ConfigManagerから設定を取得
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
                original_text = "画像から抽出されたテキスト (OCR未実装)" # 暫定的な値

                translation_part = parts[1]
                if "解説:" in translation_part:
                    trans_exp_parts = translation_part.split("解説:", 1)
                    translation = trans_exp_parts[0].strip()
                    explanation = trans_exp_parts[1].strip()
                else:
                    translation = translation_part.strip()
            elif "解説:" in text_content:
                explanation = text_content.split("解説:", 1)[1].strip()
                original_text = "画像から抽出されたテキスト (OCR未実装)" # 暫定的な値
            else:
                translation = text_content.strip()
                original_text = "画像から抽出されたテキスト (OCR未実装)" # 暫定的な値

            print(f"DEBUG: GeminiWorker: 翻訳結果: {translation[:50]}...")
            print(f"DEBUG: GeminiWorker: 解説: {explanation[:50]}...")
            
            # 処理結果をシグナルで送信
            self.finished.emit(original_text, translation, explanation)

        except Exception as e:
            print(f"ERROR: GeminiWorker: Gemini API処理中にエラーが発生しました: {e}")
            # エラーメッセージをシグナルで送信
            self.error.emit(f"翻訳処理中にエラーが発生しました。\n{e}")


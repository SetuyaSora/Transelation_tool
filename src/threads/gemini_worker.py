from PyQt5.QtCore import QThread, pyqtSignal
import google.generativeai as genai

# src/config/config_managerから設定マネージャーをインポート
from src.config.config_manager import ConfigManager
# 履歴関連関数はGeminiWorkerからは直接操作しない (SelectionWindowで操作する)
# from src.utils.helper_functions import add_translation_entry, save_translation_history # ここでは不要

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

    def __init__(self, image_data, original_text, config_manager: ConfigManager, history_file_path: str):
        super().__init__()
        self.image_data = image_data
        self.original_text = original_text # OCRで抽出された原文テキスト (または空文字列)
        self.config_manager = config_manager
        self.history_file_path = history_file_path # 履歴ファイルパスは履歴保存用として保持

    def run(self):
        print("DEBUG: GeminiWorker: API処理を開始します。")
        
        try:
            model_name = self.config_manager.get("gemini_settings.model_name")
            model = genai.GenerativeModel(model_name)
            
            image_part = {
                'mime_type': 'image/png',
                'data': self.image_data
            }

            # 設定からプロンプトを取得
            translation_prompt = self.config_manager.get("gemini_settings.translation_prompt")
            
            # OCRでテキストが抽出された場合のみ、プロンプトに原文を含める
            if self.original_text and self.original_text.strip() != "" and \
                not self.original_text.startswith("OCRエラー:"): # エラーメッセージはプロンプトに含めない
                translation_prompt += f"\n\n--- 画像からOCRで抽出されたテキスト ---\n{self.original_text.strip()}\n\n"
                translation_prompt += "上記OCRテキストを考慮し、もし画像テキストが読み取れない場合はOCRテキストを優先して翻訳・解説してください。"
            else:
                print("DEBUG: GeminiWorker: OCRテキストが空か、エラーメッセージのため、プロンプトには含めません。")
            
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
            
            self.finished.emit(self.original_text, translation, explanation)

        except Exception as e:
            print(f"ERROR: GeminiWorker: Gemini API処理中にエラーが発生しました: {e}")
            # エラー発生時はoriginal_textをそのまま渡す (エラーメッセージならそのまま、OCR結果ならそのまま)
            self.error.emit(f"翻訳処理中にエラーが発生しました。\n{e}")


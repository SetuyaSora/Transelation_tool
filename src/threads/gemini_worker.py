from PyQt5.QtCore import QThread, pyqtSignal
import google.generativeai as genai
import logging # logging モジュールを追加

# src/config/config_managerから設定マネージャーをインポート
from src.config.config_manager import ConfigManager

logger = logging.getLogger(__name__) # このモジュール用のロガーを取得

class GeminiWorker(QThread):
    """
    Gemini APIを非同期で呼び出し、翻訳処理を行うWorkerスレッド。
    """
    finished = pyqtSignal(str, str, str) # original_text (str), translation (str), explanation (str)
    error = pyqtSignal(str) # error_message (str)

    def __init__(self, image_data, original_text, config_manager: ConfigManager, history_file_path: str):
        super().__init__()
        self.image_data = image_data
        self.original_text = original_text # OCRで抽出された原文テキスト (または空文字列)
        self.config_manager = config_manager
        self.history_file_path = history_file_path # 履歴ファイルパスは履歴保存用として保持

    def run(self):
        logger.debug("GeminiWorker: API処理を開始します。")
        
        try:
            model_name = self.config_manager.get("gemini_settings.model_name")
            model = genai.GenerativeModel(model_name)
            
            image_part = {
                'mime_type': 'image/png',
                'data': self.image_data
            }

            # 現在のモードに応じてプロンプトを選択
            current_mode = self.config_manager.get("gemini_settings.mode", "translation")
            if current_mode == "translation":
                translation_prompt = self.config_manager.get("gemini_settings.translation_prompt")
                logger.debug("GeminiWorker: 翻訳モードでプロンプトを構築します。")
            elif current_mode == "explanation":
                translation_prompt = self.config_manager.get("gemini_settings.explanation_prompt")
                logger.debug("GeminiWorker: 解説モードでプロンプトを構築します。")
            else:
                # 未定義のモードの場合、デフォルトで翻訳モードを使用
                translation_prompt = self.config_manager.get("gemini_settings.translation_prompt")
                logger.warning(f"GeminiWorker: 未定義のモード '{current_mode}' が設定されています。デフォルトの翻訳モードを使用します。")
            
            # OCRでテキストが抽出された場合のみ、プロンプトに原文を含める
            if self.original_text and self.original_text.strip() != "" and \
               not self.original_text.startswith("OCRエラー:"):
                translation_prompt += f"\n\n--- 画像からOCRで抽出されたテキスト ---\n{self.original_text.strip()}\n\n"
                if current_mode == "explanation":
                    translation_prompt += "上記OCRテキストを参考に、ゲーム内の要素について詳しく解説してください。もし画像内の文字が不鮮明な場合、OCRテキストを優先して情報を取得し、正確な解説を生成してください。"
                else:
                    translation_prompt += "上記OCRテキストを考慮し、もし画像テキストが読み取れない場合はOCRテキストを優先して翻訳・解説してください。"
            else:
                logger.debug("GeminiWorker: OCRテキストが空か、エラーメッセージのため、プロンプトには含めません。")
            
            prompt_parts = [
                image_part,
                translation_prompt,
            ]

            logger.debug("GeminiWorker: Gemini APIへリクエスト送信中...")
            response = model.generate_content(prompt_parts)
            logger.debug("GeminiWorker: Gemini APIからの応答を受信しました。")
            
            text_content = response.text
            
            translation = ""
            explanation = "解説が見つかりませんでした。"

            if current_mode == "translation":
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
            elif current_mode == "explanation":
                if "解説:" in text_content:
                    explanation = text_content.split("解説:", 1)[1].strip()
                    translation = text_content.split("解説:", 1)[0].strip() # 解説より前の部分を要約として表示
                else:
                    explanation = text_content.strip()
                    translation = ""
            
            logger.debug(f"GeminiWorker: 最終プロンプトの一部: {translation_prompt[:200]}...")
            logger.debug(f"GeminiWorker: 翻訳結果 (mode={current_mode}): {translation[:50]}...")
            logger.debug(f"GeminiWorker: 解説 (mode={current_mode}): {explanation[:50]}...")
            
            self.finished.emit(self.original_text, translation, explanation)

        except Exception as e:
            logger.exception(f"GeminiWorker: Gemini API処理中にエラーが発生しました。")
            self.error.emit(f"翻訳処理中にエラーが発生しました。\n{e}")


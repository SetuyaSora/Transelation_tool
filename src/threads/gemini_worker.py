from PyQt5.QtCore import QThread, pyqtSignal
import google.generativeai as genai

# src/config/config_managerから設定マネージャーをインポート
from src.config.config_manager import ConfigManager

class GeminiWorker(QThread):
    """
    Gemini APIを非同期で呼び出し、翻訳処理を行うWorkerスレッド。
    """
    finished = pyqtSignal(str, str, str) # original_text (str), translation (str), explanation (str)
    error = pyqtSignal(str) # error_message (str)

    def __init__(self, image_data, original_text, config_manager: ConfigManager, history_file_path: str):
        super().__init__()
        self.image_data = image_data
        self.original_text = original_text
        self.config_manager = config_manager
        self.history_file_path = history_file_path

    def run(self):
        print("DEBUG: GeminiWorker: API処理を開始します。")
        
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
                print("DEBUG: GeminiWorker: 翻訳モードでプロンプトを構築します。")
            elif current_mode == "explanation":
                translation_prompt = self.config_manager.get("gemini_settings.explanation_prompt")
                print("DEBUG: GeminiWorker: 解説モードでプロンプトを構築します。")
            else:
                # 未定義のモードの場合、デフォルトで翻訳モードを使用
                translation_prompt = self.config_manager.get("gemini_settings.translation_prompt")
                print(f"WARNING: GeminiWorker: 未定義のモード '{current_mode}' が設定されています。デフォルトの翻訳モードを使用します。")
            
            # OCRでテキストが抽出された場合のみ、プロンプトに原文を含める
            if self.original_text and self.original_text.strip() != "" and \
               not self.original_text.startswith("OCRエラー:"):
                # OCRテキストが長い場合、切り詰めるなどの処理を検討しても良い
                translation_prompt += f"\n\n--- 画像からOCRで抽出されたテキスト ---\n{self.original_text.strip()}\n\n"
                # 解説モードでは、OCRテキストを元に解説を補強する指示を追加
                if current_mode == "explanation":
                    translation_prompt += "上記OCRテキストを参考に、ゲーム内の要素について詳しく解説してください。もし画像内の文字が不鮮明な場合、OCRテキストを優先して情報を取得し、正確な解説を生成してください。"
                else: # 翻訳モード
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
            
            translation = "" # 解説モードでは翻訳結果は空にするか、最初の要約とする
            explanation = "解説が見つかりませんでした。"

            # レスポンスの解析ロジックをモードに合わせて調整
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
                    translation = text_content.strip() # フォーマットがない場合、全て翻訳結果として扱う
            elif current_mode == "explanation":
                # 解説モードでは、レスポンス全体を解説として扱う
                # もし「解説:」というプレフィックスを強制するなら、ここも調整
                if "解説:" in text_content:
                    explanation = text_content.split("解説:", 1)[1].strip()
                    translation = text_content.split("解説:", 1)[0].strip() # 解説より前の部分を要約として表示
                else:
                    explanation = text_content.strip() # フォーマットがない場合、全て解説として扱う
                    translation = "" # 翻訳はなし
            
            print(f"DEBUG: GeminiWorker: 最終プロンプトの一部: {translation_prompt[:200]}...") # 最終プロンプトを確認
            print(f"DEBUG: GeminiWorker: 翻訳結果 (mode={current_mode}): {translation[:50]}...")
            print(f"DEBUG: GeminiWorker: 解説 (mode={current_mode}): {explanation[:50]}...")
            
            self.finished.emit(self.original_text, translation, explanation)

        except Exception as e:
            print(f"ERROR: GeminiWorker: Gemini API処理中にエラーが発生しました: {e}")
            self.error.emit(f"翻訳処理中にエラーが発生しました。\n{e}")


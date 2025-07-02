import logging
import os
from logging.handlers import RotatingFileHandler

def configure_logging(log_dir="logs", log_file_name="app.log", log_level=logging.DEBUG, max_bytes=10*1024*1024, backup_count=5):
    """
    アプリケーションのログ設定を行う。

    Args:
        log_dir (str): ログファイルを保存するディレクトリ名。
        log_file_name (str): ログファイル名。
        log_level (int): ログの最低レベル (logging.DEBUG, logging.INFOなど)。
        max_bytes (int): 各ログファイルの最大サイズ (バイト単位)。
        backup_count (int): 保持するバックアップログファイルの数。
    """
    # ログディレクトリが存在しない場合は作成
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, log_file_name)

    # ルートロガーを取得
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 既存のハンドラーをクリア (再呼び出し時に重複しないように)
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # ログフォーマットの定義
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # ファイルハンドラー (ローテーション対応)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # コンソールハンドラー (開発中にコンソールにも出力したい場合)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    root_logger.info(f"ログ出力が設定されました。ログファイル: {log_file_path}")
    root_logger.info(f"ログレベル: {logging.getLevelName(log_level)}")


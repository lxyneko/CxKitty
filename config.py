import warnings
from pathlib import Path

import yaml

try:
    with open("config.yml", "r", encoding="utf8") as fp:
        conf: dict = yaml.load(fp, yaml.FullLoader)
except FileNotFoundError:
    conf = {}
    warnings.warn("Config file not found", RuntimeWarning)

# 路径配置
SESSIONS_PATH = Path(conf.get("session_path", "session"))
LOGS_PATH = Path(conf.get("log_path", "logs"))
EXPORT_PATH = Path(conf.get("export_path"))
FACE_PATH = Path(conf.get("face_image_path"))

# 创建导出目录
if not EXPORT_PATH.exists():
    EXPORT_PATH.mkdir(parents=True)

# 基本配置
MULTI_SESS: bool = conf.get("multi_session", True)
TUI_MAX_HEIGHT: int = conf.get("tui_max_height", 25)
MASKACC: bool = conf.get("mask_acc", True)
FETCH_UPLOADED_FACE: bool = conf.get("fetch_uploaded_face", True)

# 任务配置
WORK: dict = conf.get("work", {})
VIDEO: dict = conf.get("video", {})
DOCUMENT: dict = conf.get("document", {})
EXAM: dict = conf.get("exam", {})

# 任务使能配置
WORK_EN: bool = WORK.get("enable", True)
VIDEO_EN: bool = VIDEO.get("enable", True)
DOCUMENT_EN: bool = DOCUMENT.get("enable", True)

# 任务延时配置
WORK_WAIT: int = WORK.get("wait", 15)
VIDEO_WAIT: int = VIDEO.get("wait", 15)
DOCUMENT_WAIT: int = DOCUMENT.get("wait", 15)

# 搜索器配置
SEARCHERS: list = conf.get("searchers", [])

# 通知配置
NOTIFICATION: dict = conf.get("notification", {})
NOTIFICATION_ENABLED: bool = NOTIFICATION.get("enabled", False)
NOTIFICATION_PROVIDER: str = NOTIFICATION.get("provider", "")
NOTIFICATION_URL: str = NOTIFICATION.get("url", "")

# 通知服务实例（延迟初始化）
_notification_service = None

def get_notification_service():
    """获取通知服务实例"""
    global _notification_service
    if _notification_service is None:
        from notification import create_notification_service
        # 如果配置文件中有通知配置，使用配置文件的设置
        if NOTIFICATION_ENABLED and NOTIFICATION_PROVIDER:
            config = {
                'provider': NOTIFICATION_PROVIDER,
                'url': NOTIFICATION_URL
            }
            _notification_service = create_notification_service(config)
        else:
            # 否则尝试从config.ini文件加载
            _notification_service = create_notification_service()
    return _notification_service

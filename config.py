import warnings
import os
import sys
from pathlib import Path

import yaml


class Config:
    def __init__(self, config_file="config.yml"):
        self.config_path = self._get_config_path(config_file)
        self.conf = self._load_config()

        self._setup_paths()
        self._setup_basic_config()
        self._setup_task_config()
        self._setup_webapp_config()

    def _get_resource_path(self, relative_path):
        """获取资源的绝对路径"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _get_config_path(self, config_file):
        external_config = Path(config_file)
        if external_config.exists():
            return external_config
        return self._get_resource_path(config_file)

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf8") as fp:
                return yaml.load(fp, yaml.FullLoader)
        except FileNotFoundError:
            warnings.warn(f"Config file not found at {self.config_path}", RuntimeWarning)
            return {}

    def _setup_paths(self):
        self.SESSIONS_PATH = Path(self.conf.get("session_path", "session"))
        self.LOGS_PATH = Path(self.conf.get("log_path", "logs"))
        self.EXPORT_PATH = Path(self.conf.get("export_path", "export"))
        self.FACE_PATH = Path(self.conf.get("face_image_path", "imgs"))

        if not self.EXPORT_PATH.exists():
            self.EXPORT_PATH.mkdir(parents=True)

    def _setup_basic_config(self):
        self.MULTI_SESS: bool = self.conf.get("multi_session", True)
        self.TUI_MAX_HEIGHT: int = self.conf.get("tui_max_height", 25)
        self.MASKACC: bool = self.conf.get("mask_acc", True)
        self.FETCH_UPLOADED_FACE: bool = self.conf.get("fetch_uploaded_face", True)

    def _setup_task_config(self):
        self.WORK: dict = self.conf.get("work", {})
        self.VIDEO: dict = self.conf.get("video", {})
        self.DOCUMENT: dict = self.conf.get("document", {})
        self.EXAM: dict = self.conf.get("exam", {})

        self.WORK_EN: bool = self.WORK.get("enable", True)
        self.VIDEO_EN: bool = self.VIDEO.get("enable", True)
        self.DOCUMENT_EN: bool = self.DOCUMENT.get("enable", True)

        self.WORK_WAIT: int = self.WORK.get("wait", 15)
        self.VIDEO_WAIT: int = self.VIDEO.get("wait", 15)
        self.DOCUMENT_WAIT: int = self.DOCUMENT.get("wait", 15)

        self.SEARCHERS: list = self.conf.get("searchers", [])

    def _setup_webapp_config(self):
        webapp_conf = self.conf.get("webapp", {})
        self.WEBAPP_ENABLE: bool = webapp_conf.get("enable", False)
        self.WEBAPP_USERNAME: str = webapp_conf.get("username", "admin")
        self.WEBAPP_PASSWORD: str = webapp_conf.get("password", "admin123")
        self.WEBAPP_SECRET_KEY: str = webapp_conf.get("secret_key", "a_very_secret_key")

# 全局配置实例
config = Config()

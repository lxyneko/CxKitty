#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用通知推送模块
支持 ServerChan、Qmsg、Bark 等多种推送服务
"""

import configparser
import requests
from abc import ABC, abstractmethod
from typing import Dict, Optional
from pathlib import Path

# 使用项目的日志系统
from logger import Logger


class NotificationService(ABC):
    """通知服务基类"""
    
    CONFIG_PATH = "config.ini"
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.url = ""
        self._conf = None
        self.disabled = False
        self.logger = Logger(f"Notification.{self.name}")
        
    def config_set(self, config: Dict[str, str]) -> None:
        """设置配置"""
        self._conf = config
        
    def _load_config_from_file(self) -> Optional[Dict[str, str]]:
        """从配置文件加载配置"""
        try:
            config_path = Path(self.CONFIG_PATH)
            if not config_path.exists():
                self.logger.info("未找到config.ini配置文件，已忽略推送功能")
                self.disabled = True
                return None
                
            config = configparser.ConfigParser()
            config.read(config_path, encoding="utf8")
            
            if 'notification' not in config:
                self.logger.info("未找到notification配置节，已忽略推送功能")
                self.disabled = True
                return None
                
            return dict(config['notification'])
        except Exception as e:
            self.logger.error(f"读取配置文件失败: {e}")
            self.disabled = True
            return None
    
    def init_notification(self) -> None:
        """初始化通知服务"""
        if not self._conf:
            self._conf = self._load_config_from_file()
        
        if not self.disabled and self._conf:
            self._init_service()
    
    @abstractmethod
    def _init_service(self) -> None:
        """初始化具体服务"""
        pass
    
    @abstractmethod
    def _send(self, message: str) -> None:
        """发送消息"""
        pass
    
    def send(self, message: str) -> None:
        """发送通知的公共接口"""
        if not self.disabled:
            try:
                self._send(message)
            except Exception as e:
                self.logger.error(f"发送通知失败: {e}")


class DefaultNotification(NotificationService):
    """默认通知服务（空实现）"""
    
    def _init_service(self) -> None:
        pass
    
    def _send(self, message: str) -> None:
        self.logger.debug(f"默认通知服务收到消息: {message}")
    
    def get_notification_from_config(self) -> NotificationService:
        """根据配置创建具体的通知服务"""
        if not self._conf:
            self._conf = self._load_config_from_file()
            
        if self.disabled or not self._conf:
            return self
            
        try:
            provider_name = self._conf.get('provider', '').strip()
            if not provider_name:
                self.logger.info("未指定通知服务提供商，使用默认服务")
                return self
                
            # 获取对应的通知服务类
            provider_class = globals().get(provider_name)
            if not provider_class:
                self.logger.error(f"未找到名为 {provider_name} 的通知服务提供商")
                self.disabled = True
                return self
                
            # 创建通知服务实例
            service = provider_class()
            service.config_set(self._conf)
            return service
            
        except Exception as e:
            self.logger.error(f"创建通知服务失败: {e}")
            self.disabled = True
            return self


class ServerChan(NotificationService):
    """Server酱推送服务"""
    
    def _init_service(self) -> None:
        if not self._conf or not self._conf.get('url'):
            self.disabled = True
            self.logger.info("未找到Server酱url配置")
            return
            
        self.url = self._conf['url'].strip()
        self.logger.info("已初始化Server酱推送服务")
    
    def _send(self, message: str) -> None:
        params = {
            'text': 'CxKitty通知',
            'desp': message,
        }
        headers = {
            'Content-Type': 'application/json;charset=utf-8'
        }
        
        try:
            response = requests.post(self.url, json=params, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 0:
                self.logger.info("Server酱推送成功")
            else:
                self.logger.error(f"Server酱推送失败: {result.get('message', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Server酱推送网络错误: {e}")
        except Exception as e:
            self.logger.error(f"Server酱推送失败: {e}")


class Qmsg(NotificationService):
    """Qmsg酱推送服务"""
    
    def _init_service(self) -> None:
        if not self._conf or not self._conf.get('url'):
            self.disabled = True
            self.logger.info("未找到Qmsg酱url配置")
            return
            
        self.url = self._conf['url'].strip()
        self.logger.info("已初始化Qmsg酱推送服务")
    
    def _send(self, message: str) -> None:
        params = {'msg': message}
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        
        try:
            response = requests.post(self.url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                self.logger.info("Qmsg酱推送成功")
            else:
                self.logger.error(f"Qmsg酱推送失败: {result.get('reason', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Qmsg酱推送网络错误: {e}")
        except Exception as e:
            self.logger.error(f"Qmsg酱推送失败: {e}")


class Bark(NotificationService):
    """Bark推送服务"""
    
    def _init_service(self) -> None:
        if not self._conf or not self._conf.get('url'):
            self.disabled = True
            self.logger.info("未找到Bark url配置")
            return
            
        self.url = self._conf['url'].strip()
        if not self.url.endswith('/'):
            self.url += '/'
        self.logger.info("已初始化Bark推送服务")
    
    def _send(self, message: str) -> None:
        # Bark支持URL路径方式发送
        url = f"{self.url}CxKitty通知/{message}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 200:
                self.logger.info("Bark推送成功")
            else:
                self.logger.error(f"Bark推送失败: {result.get('message', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Bark推送网络错误: {e}")
        except Exception as e:
            self.logger.error(f"Bark推送失败: {e}")


# 工厂函数
def create_notification_service(config: Optional[Dict[str, str]] = None) -> NotificationService:
    """创建通知服务实例"""
    service = DefaultNotification()
    
    if config:
        service.config_set(config)
    
    service = service.get_notification_from_config()
    service.init_notification()
    
    return service


# 全局通知服务实例
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """获取全局通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = create_notification_service()
    return _notification_service


def send_notification(message: str) -> None:
    """发送通知的便捷函数"""
    service = get_notification_service()
    service.send(message)


# 为了向后兼容
Notification = DefaultNotification
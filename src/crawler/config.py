from typing import List, Dict
from src.config import config

# 使用全局配置实例
class Config:
    @classmethod
    def get_gitlab_configs(cls) -> List[Dict]:
        """获取GitLab配置列表"""
        return config.get_gitlab_configs()

    @classmethod
    def get_td_configs(cls) -> List[Dict]:
        """获取TD配置列表"""
        return config.get_td_configs()

    @property
    def GITLAB_SINCE_DATE(self):
        return config.get('GITLAB_SINCE_DATE')

    @property
    def GITLAB_UNTIL_DATE(self):
        return config.get('GITLAB_UNTIL_DATE')
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict

load_dotenv()  # 加载 .env 文件


class Config:
    # GitLab 配置
    GITLAB_URLS = os.getenv("GITLAB_URLS", "http://cs.devops.sangfor.org").split(',')
    GITLAB_TOKENS = os.getenv("GITLAB_TOKENS", "").split(',')
    GITLAB_PROJECT_IDS = [ids.split(',') for ids in os.getenv("GITLAB_PROJECT_IDS", "").split('|')]

    # 默认获取最近30天的提交
    DEFAULT_DAYS = int(os.getenv("DEFAULT_DAYS", "30"))
    GITLAB_SINCE_DATE = os.getenv("GITLAB_SINCE_DATE",
                                  (datetime.now() - timedelta(days=DEFAULT_DAYS)).strftime("%Y-%m-%d"))
    GITLAB_UNTIL_DATE = os.getenv("GITLAB_UNTIL_DATE",
                                  datetime.now().strftime("%Y-%m-%d"))

    # TD系统配置
    TD_URLS = os.getenv("TD_URLS", "https://td.sangfor.com").split(',')
    TD_COOKIES = os.getenv("TD_COOKIES", "").split(',')
    PRODUCT_IDS = os.getenv("PRODUCT_IDS", "").split(',')
    TD_AREA = os.getenv("TD_AREA", "null")

    @classmethod
    def get_gitlab_configs(cls) -> List[Dict]:
        """获取GitLab配置列表，每个配置包含URL、Token和对应的项目ID列表"""
        configs = []
        for url, token, project_ids in zip(cls.GITLAB_URLS, cls.GITLAB_TOKENS, cls.GITLAB_PROJECT_IDS):
            configs.append({
                "url": url.strip(),
                "token": token.strip(),
                "project_ids": [pid.strip() for pid in project_ids]
            })
        return configs

    @classmethod
    def get_td_configs(cls) -> List[Dict]:
        """获取TD配置列表，每个配置包含URL、Cookie和对应的产品ID列表"""
        configs = []
        for url, cookie in zip(cls.TD_URLS, cls.TD_COOKIES):
            configs.append({
                "url": url.strip(),
                "headers": {
                    "PRODUCT-ID": cls.PRODUCT_IDS[0].strip(),  # 默认使用第一个产品ID
                    "TD-AREA": cls.TD_AREA,
                    "Cookie": cookie.strip(),
                }
            })
        return configs

    # 数据库配置
    DATABASE_PATH = "bugs.db"
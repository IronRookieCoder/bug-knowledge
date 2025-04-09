from typing import List, Dict, Optional, Any
from src.config import config
from src.utils.log import get_logger

logger = get_logger(__name__)

# 使用全局配置实例
class Config:
    @classmethod
    def get_gitlab_configs(cls) -> List[Dict]:
        """获取GitLab配置列表"""
        try:
            configs = config.get_gitlab_configs()
            if not configs:
                logger.warning("未找到GitLab配置")
                return []
                
            # 验证配置
            valid_configs = []
            for cfg in configs:
                if not isinstance(cfg, dict):
                    logger.warning(f"无效的GitLab配置类型: {type(cfg)}")
                    continue
                    
                # 检查所需字段
                if not all(key in cfg for key in ["url", "token", "project_ids"]):
                    logger.warning(f"GitLab配置缺少必要字段: {cfg}")
                    continue
                    
                # 验证project_ids
                if not isinstance(cfg["project_ids"], list):
                    logger.warning(f"GitLab配置中project_ids不是列表类型: {cfg}")
                    continue
                    
                valid_configs.append(cfg)
                
            if len(valid_configs) < len(configs):
                logger.warning(f"发现 {len(configs) - len(valid_configs)} 个无效的GitLab配置")
                
            return valid_configs
        except Exception as e:
            logger.error(f"获取GitLab配置时发生错误: {str(e)}")
            return []

    @classmethod
    def get_td_configs(cls) -> List[Dict]:
        """获取TD配置列表"""
        try:
            configs = config.get_td_configs()
            if not configs:
                logger.warning("未找到TD配置")
                return []
                
            # 验证配置
            valid_configs = []
            for cfg in configs:
                if not isinstance(cfg, dict):
                    logger.warning(f"无效的TD配置类型: {type(cfg)}")
                    continue
                    
                # 检查所需字段
                if not all(key in cfg for key in ["url", "headers"]):
                    logger.warning(f"TD配置缺少必要字段: {cfg}")
                    continue
                    
                # 验证headers是字典
                if not isinstance(cfg["headers"], dict):
                    logger.warning(f"TD配置中headers不是字典类型: {cfg}")
                    continue
                    
                valid_configs.append(cfg)
                
            if len(valid_configs) < len(configs):
                logger.warning(f"发现 {len(configs) - len(valid_configs)} 个无效的TD配置")
                
            return valid_configs
        except Exception as e:
            logger.error(f"获取TD配置时发生错误: {str(e)}")
            return []

    @property
    def GITLAB_SINCE_DATE(self) -> Optional[str]:
        try:
            date = config.get('GITLAB_SINCE_DATE')
            return str(date) if date else None
        except Exception as e:
            logger.error(f"获取GITLAB_SINCE_DATE时发生错误: {str(e)}")
            return None

    @property
    def GITLAB_UNTIL_DATE(self) -> Optional[str]:
        try:
            date = config.get('GITLAB_UNTIL_DATE')
            return str(date) if date else None
        except Exception as e:
            logger.error(f"获取GITLAB_UNTIL_DATE时发生错误: {str(e)}")
            return None
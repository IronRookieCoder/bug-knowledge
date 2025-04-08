import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


@dataclass
class ConfigValidationError:
    key: str
    message: str


@dataclass
class GitLabConfig:
    url: str
    token: str
    project_ids: List[str]


@dataclass
class TDConfig:
    url: str
    headers: Dict[str, str]


class Config:
    """配置管理类"""

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self.load_config()
        self._validate_config()

    def load_config(self) -> None:
        """加载配置"""
        # 确定环境
        env = os.getenv("PYTHON_ENV", "development")

        # 项目根路径
        root_path = Path(__file__).parent.parent

        # 基础配置
        base_env_path = root_path / ".env"
        if base_env_path.exists():
            load_dotenv(base_env_path)

        # 环境特定配置
        env_file = root_path / f".env.{env}"
        if env_file.exists():
            load_dotenv(env_file, override=True)

        # 本地开发配置
        local_env = root_path / ".env.local"
        if local_env.exists():
            load_dotenv(local_env, override=True)

        # 加载配置到内存
        self._load_app_config()
        self._load_database_config()
        self._load_crawler_config()
        self._load_vector_store_config()
        self._load_web_config()
        self._load_log_config()
        self._load_model_config()
        self._load_gitlab_configs()
        self._load_td_configs()

    def _load_app_config(self) -> None:
        """加载应用配置"""
        self._config["DEBUG"] = os.getenv("DEBUG", "False").lower() == "true"
        self._config["APP_NAME"] = os.getenv("APP_NAME", "bug-knowledge")
        self._config["APP_PORT"] = int(os.getenv("APP_PORT", "5000"))

    def _load_database_config(self) -> None:
        """加载数据库配置"""
        self._config["DATABASE_PATH"] = os.getenv("DATABASE_PATH", "data/bugs.db")

    def _load_crawler_config(self) -> None:
        """加载爬虫配置"""
        # GitLab配置
        self._config["GITLAB_URLS"] = os.getenv("GITLAB_URLS", "").split("|")
        self._config["GITLAB_TOKENS"] = os.getenv("GITLAB_TOKENS", "").split("|")
        self._config["GITLAB_PROJECT_IDS"] = [
            ids.split(",") for ids in os.getenv("GITLAB_PROJECT_IDS", "").split("|")
        ]

        # 时间范围配置
        self._config["DEFAULT_DAYS"] = int(os.getenv("DEFAULT_DAYS", "30"))
        since_date = (
            datetime.now() - timedelta(days=self._config["DEFAULT_DAYS"])
        ).strftime("%Y-%m-%d")
        self._config["GITLAB_SINCE_DATE"] = os.getenv("GITLAB_SINCE_DATE", since_date)
        self._config["GITLAB_UNTIL_DATE"] = os.getenv(
            "GITLAB_UNTIL_DATE", datetime.now().strftime("%Y-%m-%d")
        )

        # TD系统配置
        self._config["TD_URLS"] = os.getenv("TD_URLS", "").split("|")
        self._config["TD_COOKIES"] = os.getenv("TD_COOKIES", "").split("|")
        self._config["PRODUCT_IDS"] = [
            ids.split(",") for ids in os.getenv("PRODUCT_IDS", "").split("|")
        ]
        self._config["TD_AREAS"] = os.getenv("TD_AREA", "").split("|")

    def _load_vector_store_config(self) -> None:
        """加载向量存储配置"""
        self._config["VECTOR_STORE"] = {
            "data_dir": os.getenv("VECTOR_STORE_DIR", "data/annoy"),
            "vector_dim": int(os.getenv("VECTOR_DIM", "384")),
            "index_type": os.getenv("INDEX_TYPE", "angular"),
            "n_trees": int(os.getenv("N_TREES", "100")),  # 增加树的数量以提高准确性
            "similarity_threshold": float(
                os.getenv("SIMILARITY_THRESHOLD", "1.2")
            ),  # 调整阈值
        }

    def _load_web_config(self) -> None:
        """加载Web服务配置"""
        self._config["WEB"] = {
            "templates_dir": os.getenv("TEMPLATES_DIR", "src/ui/templates"),
            "static_dir": os.getenv("STATIC_DIR", "src/ui/static"),
            "host": os.getenv("WEB_HOST", "127.0.0.1"),
            "port": int(os.getenv("WEB_PORT", "8010")),
        }

    def _load_log_config(self) -> None:
        """加载日志配置"""
        self._config["LOG"] = {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "file": os.getenv("LOG_FILE", "logs/bug_knowledge.log"),
            "max_size": int(os.getenv("LOG_MAX_SIZE", 10 * 1024 * 1024)),  # 默认10MB
            "backup_count": int(os.getenv("LOG_BACKUP_COUNT", 5)),
            "format": os.getenv(
                "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
        }

        # 确保日志目录存在
        log_dir = Path(self._config["LOG"]["file"]).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    def _load_model_config(self) -> None:
        """加载模型配置"""
        self._config["MODEL"] = {
            "name": os.getenv("MODEL_NAME", "all-MiniLM-L6-v2"),
            "cache_dir": os.getenv("MODEL_CACHE_DIR", "lm-models"),
            "offline": os.getenv("MODEL_OFFLINE", "True").lower() == "true",
        }

    def _load_gitlab_configs(self) -> None:
        """加载GitLab配置"""
        gitlab_config_str = os.getenv("GITLAB_CONFIGS", "[]")
        try:
            gitlab_configs = json.loads(gitlab_config_str)
            self._config["GITLAB"] = [
                GitLabConfig(
                    url=config["url"],
                    token=config["token"],
                    project_ids=config["project_ids"],
                )
                for config in gitlab_configs
            ]
        except json.JSONDecodeError:
            self._config["GITLAB"] = []

    def _load_td_configs(self) -> None:
        """加载TD配置"""
        td_config_str = os.getenv("TD_CONFIGS", "[]")
        try:
            td_configs = json.loads(td_config_str)
            self._config["TD"] = [
                TDConfig(url=config["url"], headers=config["headers"])
                for config in td_configs
            ]
        except json.JSONDecodeError:
            self._config["TD"] = []

    def _validate_config(self) -> None:
        """验证配置有效性"""
        errors: List[ConfigValidationError] = []

        # 验证必需的配置项
        required_configs = [
            ("DATABASE_PATH", "数据库路径不能为空"),
            ("APP_PORT", "应用端口必须设置"),
        ]

        for key, message in required_configs:
            if not self._config.get(key):
                errors.append(ConfigValidationError(key, message))

        # 验证端口范围
        try:
            port = int(self._config.get("APP_PORT", 0))
            if not (1024 <= port <= 65535):
                errors.append(
                    ConfigValidationError("APP_PORT", "端口必须在1024-65535之间")
                )
        except ValueError:
            errors.append(ConfigValidationError("APP_PORT", "端口必须是有效的数字"))

        # 验证路径存在性
        database_dir = Path(self._config.get("DATABASE_PATH", "")).parent
        if not database_dir.exists():
            database_dir.mkdir(parents=True, exist_ok=True)

        # 验证向量存储配置
        vector_store = self._config.get("VECTOR_STORE", {})
        if not vector_store.get("data_dir"):
            errors.append(
                ConfigValidationError("VECTOR_STORE.data_dir", "向量存储目录不能为空")
            )
        if not vector_store.get("vector_dim"):
            errors.append(
                ConfigValidationError("VECTOR_STORE.vector_dim", "向量维度必须设置")
            )

        # 验证Web配置
        web_config = self._config.get("WEB", {})
        if not web_config.get("templates_dir"):
            errors.append(
                ConfigValidationError("WEB.templates_dir", "模板目录不能为空")
            )
        if not web_config.get("static_dir"):
            errors.append(
                ConfigValidationError("WEB.static_dir", "静态文件目录不能为空")
            )

        # 如果有错误，抛出异常
        if errors:
            error_messages = "\n".join(f"{e.key}: {e.message}" for e in errors)
            raise ValueError(f"配置验证失败:\n{error_messages}")

    def update_config(self, key: str, value: Any, validate: bool = True) -> None:
        """
        更新配置项
        
        Args:
            key: 配置项键名
            value: 配置项的新值
            validate: 是否在更新后进行配置验证，默认为True
            
        Raises:
            ValueError: 当validate=True且更新后的配置验证失败时抛出
        """
        if '.' in key:
            # 处理嵌套配置，如 "WEB.host"
            parts = key.split('.')
            config = self._config
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
            config[parts[-1]] = value
        else:
            self._config[key] = value

        if validate:
            self._validate_config()

    def get_required(self, key: str) -> Any:
        """获取必需的配置项，如果不存在则抛出异常"""
        value = self._config.get(key)
        if value is None:
            raise KeyError(f"必需的配置项 {key} 未设置")
        return value

    def get_list(self, key: str, separator: str = ",") -> List[str]:
        """获取列表类型的配置"""
        value = self._config.get(key, "")
        return [x.strip() for x in value.split(separator) if x.strip()]

    def get_int(self, key: str, default: Optional[int] = None) -> int:
        """获取整数类型的配置"""
        try:
            return int(self._config.get(key, default))
        except (TypeError, ValueError):
            return default if default is not None else 0

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔类型的配置"""
        value = self._config.get(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)

    def get_gitlab_configs(self) -> List[GitLabConfig]:
        """获取GitLab配置列表"""
        return self._config.get("GITLAB", [])

    def get_td_configs(self) -> List[TDConfig]:
        """获取TD配置列表"""
        return self._config.get("TD", [])

    @property
    def debug(self) -> bool:
        return self._config["DEBUG"]

    @property
    def database_path(self) -> str:
        return self._config["DATABASE_PATH"]


# 全局配置实例
config = Config()

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AppConfig:
    """应用配置类"""
    vector_store: Dict[str, Any]
    web: Dict[str, Any]
    searcher: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "AppConfig":
        """从字典创建配置实例"""
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            "vector_store": self.vector_store,
            "web": self.web,
            "searcher": self.searcher
        } 
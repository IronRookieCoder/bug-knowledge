from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field
from datetime import datetime

class CodeContext(BaseModel):
    code: str = Field(..., description="问题代码")
    file_path: str = Field(..., description="文件路径")
    line_range: Tuple[int, int] = Field(..., description="行号范围")
    language: str = Field(..., description="编程语言")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="项目依赖")
    diff: Optional[str] = Field(None, description="diff格式的变更")

class EnvironmentInfo(BaseModel):
    runtime_env: str = Field(..., description="运行时环境")
    os_info: str = Field(..., description="操作系统信息")
    network_env: Optional[str] = Field(None, description="网络环境")
    additional_info: Dict[str, str] = Field(default_factory=dict, description="其他环境信息")

class BugReport(BaseModel):
    id: str = Field(..., description="BUG唯一标识符")
    title: str = Field(..., description="BUG标题")
    description: str = Field(..., description="问题描述")
    reproducible: bool = Field(..., description="是否可复现")
    steps_to_reproduce: List[str] = Field(..., description="重现步骤")
    expected_behavior: str = Field(..., description="期望行为")
    actual_behavior: str = Field(..., description="实际行为")
    code_context: CodeContext = Field(..., description="代码及其上下文")
    error_logs: str = Field(..., description="错误日志")
    environment: EnvironmentInfo = Field(..., description="环境信息")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "BUG-2024-001",
                "title": "内存泄漏问题",
                "description": "在长时间运行后观察到内存使用量持续增长",
                "reproducible": True,
                "steps_to_reproduce": [
                    "1. 启动应用",
                    "2. 持续运行24小时",
                    "3. 监控内存使用情况"
                ],
                "expected_behavior": "内存使用量应该保持稳定",
                "actual_behavior": "内存使用量持续增长",
                "code_context": {
                    "code": "def process_data(data):\n    cache = []\n    cache.extend(data)\n    return cache",
                    "file_path": "src/processor.py",
                    "line_range": [10, 15],
                    "language": "python",
                    "dependencies": {"numpy": "1.21.0"}
                },
                "error_logs": "MemoryError: Unable to allocate array",
                "environment": {
                    "runtime_env": "Python 3.9",
                    "os_info": "Ubuntu 20.04",
                    "network_env": "Local"
                }
            }
        } 
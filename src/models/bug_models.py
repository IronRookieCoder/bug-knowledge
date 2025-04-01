from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field

class BugReport(BaseModel):
    id: Optional[int] = Field(None, description="数据库主键")
    bug_id: str = Field(..., description="缺陷的唯一标识符")
    summary: str = Field(..., description="缺陷的简要描述")
    description: str = Field(..., description="缺陷的详细描述")
    file_paths: List[str] = Field(..., description="受影响的文件路径列表")
    code_diffs: List[str] = Field(..., description="代码差异列表")
    aggregated_added_code: str = Field(..., description="所有新增代码的聚合")
    aggregated_removed_code: str = Field(..., description="所有删除代码的聚合")
    test_steps: str = Field(..., description="重现缺陷的测试步骤")
    expected_result: str = Field(..., description="预期结果")
    actual_result: str = Field(..., description="实际结果")
    log_info: str = Field(..., description="相关日志信息")
    severity: str = Field(..., description="缺陷的严重程度")
    is_reappear: str = Field(..., description="缺陷是否可重现")
    environment: str = Field(..., description="缺陷发生的环境信息")
    root_cause: Optional[str] = Field(None, description="缺陷的根本原因")
    fix_solution: Optional[str] = Field(None, description="修复方案")
    related_issues: List[str] = Field(default_factory=list, description="相关问题的列表")
    fix_person: Optional[str] = Field(None, description="负责修复的人员")
    create_at: str = Field(..., description="缺陷创建时间")
    fix_date: str = Field(..., description="缺陷修复时间")
    reopen_count: int = Field(default=0, description="缺陷重新打开的次数")
    handlers: List[str] = Field(..., description="处理该缺陷的人员列表")
    project_id: str = Field(..., description="关联gitlab仓库id")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "bug_id": "BUG-2024-001",
                "summary": "在长时间运行后观察到内存使用量持续增长",
                "description": "在处理大量数据时，内存使用量持续增长，最终导致内存错误。",
                "file_paths": ["src/processor.py"],
                "code_diffs": [
                    "diff --git a/src/processor.py b/src/processor.py",
                    "index 1234567..89abcde 100644",
                    "--- a/src/processor.py",
                    "+++ b/src/processor.py",
                    "@@ -10,7 +10,9 @@ class DataProcessor:",
                    "-    def process_data(data):",
                    "-        cache = []",
                    "-        cache.extend(data)",
                    "-        return cache",
                    "+    def process_data(data):",
                    "+        cache = []",
                    "+        cache.extend(data)",
                    "+        result = self._process_cache(cache)",
                    "+        cache.clear()",
                    "+        return result"
                ],
                "aggregated_added_code": "def process_data(data):\n    cache = []\n    cache.extend(data)\n    return cache",
                "aggregated_removed_code": "",
                "test_steps": "1. 启动应用\n2. 持续运行24小时\n3. 监控内存使用情况",
                "expected_result": "内存使用量应该保持稳定",
                "actual_result": "内存使用量持续增长",
                "log_info": "MemoryError: Unable to allocate array",
                "severity": "P0",
                "is_reappear": "是",
                "environment": "Python 3.9, Ubuntu 20.04",
                "root_cause": "缓存列表未及时清理",
                "fix_solution": "添加定期清理缓存的机制",
                "related_issues": ["BUG-2024-002"],
                "fix_person": "张三",
                "create_at": "2024-03-01T10:00:00",
                "fix_date": "2024-03-02T15:30:00",
                "reopen_count": 0,
                "handlers": ["张三", "李四"],
                "project_id": "PROJ-001"
            }
        }
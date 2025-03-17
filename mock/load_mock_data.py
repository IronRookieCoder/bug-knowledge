import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import json
from datetime import datetime
from src.models.bug_models import BugReport, CodeContext, EnvironmentInfo
from src.retrieval.searcher import BugSearcher

def load_mock_data(data_file: str = "mock/data/bug_reports.json", searcher: BugSearcher = None):
    """加载测试数据到搜索器"""
    # 初始化搜索器
    if searcher is None:
        searcher = BugSearcher()
    
    # 读取测试数据
    with open(data_file, "r", encoding="utf-8") as f:
        mock_data = json.load(f)
    
    # 加载数据到系统
    for data in mock_data:
        # 转换时间字符串为datetime对象
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])
        
        # 创建BugReport对象
        bug_report = BugReport(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            reproducible=data["reproducible"],
            steps_to_reproduce=data["steps_to_reproduce"],
            expected_behavior=data["expected_behavior"],
            actual_behavior=data["actual_behavior"],
            code_context=CodeContext(
                code=data["code_context"]["code"],
                file_path=data["code_context"]["file_path"],
                line_range=tuple(data["code_context"]["line_range"]),
                language=data["code_context"]["language"]
            ),
            error_logs=data["error_logs"],
            environment=EnvironmentInfo(
                runtime_env=data["environment"]["runtime_env"],
                os_info=data["environment"]["os_info"],
                network_env=data["environment"]["network_env"]
            ),
            created_at=created_at,
            updated_at=updated_at
        )
        
        # 添加到知识库
        searcher.add_bug_report(bug_report)
        print(f"已添加Bug报告: {bug_report.id}")
    
    return searcher

if __name__ == "__main__":
    load_mock_data() 
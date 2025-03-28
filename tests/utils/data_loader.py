import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from src.models.bug_models import BugReport
from src.retrieval.searcher import BugSearcher

class TestDataLoader:
    """测试数据加载器"""
    
    def __init__(self, data_file: str = "tests/data/bug_reports.json"):
        self.data_file = Path(data_file)
    
    def load_json_data(self) -> List[Dict]:
        """从JSON文件加载原始数据"""
        if not self.data_file.exists():
            raise FileNotFoundError(f"测试数据文件不存在: {self.data_file}")
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def convert_to_bug_report(self, data: Dict) -> BugReport:
        """将JSON数据转换为BugReport对象"""
        return BugReport(
            id=data["id"],
            description=data["description"],
            is_reappear=data["is_reappear"],
            test_steps=data["test_steps"],
            expected_behavior=data["expected_behavior"],
            actual_behavior=data["actual_behavior"],
            error_logs=data["error_logs"],
            create_at=datetime.fromisoformat(data["create_at"]),
            fix_date=datetime.fromisoformat(data["fix_date"])
        )
    
    def load_bug_reports(self) -> List[BugReport]:
        """加载并转换所有bug报告"""
        json_data = self.load_json_data()
        return [self.convert_to_bug_report(data) for data in json_data]
    
    def load_into_searcher(self, searcher: BugSearcher = None) -> BugSearcher:
        """将测试数据加载到搜索器中"""
        if searcher is None:
            searcher = BugSearcher()
        
        bug_reports = self.load_bug_reports()
        for bug_report in bug_reports:
            searcher.add_bug_report(bug_report)
            print(f"已加载Bug报告: {bug_report.id}")
        
        return searcher

def load_test_data(data_file: str = "tests/data/bug_reports.json", searcher: BugSearcher = None) -> BugSearcher:
    """加载测试数据的便捷函数"""
    loader = TestDataLoader(data_file)
    return loader.load_into_searcher(searcher)

if __name__ == "__main__":
    load_test_data() 
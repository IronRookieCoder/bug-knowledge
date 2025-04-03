import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import json
from datetime import datetime
from src.models.bug_models import BugReport
from src.retrieval.searcher import BugSearcher
from rich.console import Console

console = Console()

def load_mock_data(searcher: BugSearcher = None):
    """从数据库加载测试数据到搜索器"""
    # 初始化搜索器
    if searcher is None:
        # 创建带有写入模式的向量存储
        from src.storage.vector_store import VectorStore
        vector_store = VectorStore(data_dir="data/annoy")
        searcher = BugSearcher(vector_store=vector_store)
    
    try:
        # 从数据库获取所有bug报告
        bug_reports = searcher.vector_store.db.get_all_bug_reports()
        
        # 加载数据到系统
        total = len(bug_reports)
        success = 0
        
        with console.status("[bold green]正在加载测试数据...") as status:
            for bug_report in bug_reports:
                try:
                    # 创建BugReport对象
                    bug_report_obj = BugReport(
                        bug_id=bug_report["bug_id"],
                        summary=bug_report["summary"],
                        description=bug_report["description"],
                        file_paths=bug_report["file_paths"],
                        code_diffs=bug_report["code_diffs"],
                        aggregated_added_code=bug_report["aggregated_added_code"],
                        aggregated_removed_code=bug_report["aggregated_removed_code"],
                        test_steps=bug_report["test_steps"],
                        expected_result=bug_report["expected_result"],
                        actual_result=bug_report["actual_result"],
                        log_info=bug_report["log_info"],
                        severity=bug_report["severity"],
                        is_reappear=bug_report["is_reappear"],
                        environment=bug_report["environment"],
                        root_cause=bug_report.get("root_cause"),
                        fix_solution=bug_report.get("fix_solution"),
                        related_issues=bug_report["related_issues"],
                        fix_person=bug_report.get("fix_person"),
                        create_at=bug_report["create_at"],
                        fix_date=bug_report["fix_date"],
                        reopen_count=bug_report["reopen_count"],
                        handlers=bug_report["handlers"],
                        project_id=bug_report["project_id"]
                    )
                    
                    # 添加到知识库
                    searcher.add_bug_report(bug_report_obj)
                    success += 1
                except Exception as e:
                    console.print(f"[red]添加bug report失败: {str(e)}[/red]")
                    continue
        
        if success == total:
            console.print(f"[green]成功加载全部 {total} 条测试数据[/green]")
        else:
            console.print(f"[yellow]加载完成：成功 {success}/{total} 条[/yellow]")
        
        return searcher
        
    except Exception as e:
        console.print(f"[red]错误：加载测试数据失败: {str(e)}[/red]")
        return None

if __name__ == "__main__":
    load_mock_data() 
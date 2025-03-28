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

def load_mock_data(data_file: str = "mock/data/bug_reports.json", searcher: BugSearcher = None):
    """加载测试数据到搜索器"""
    # 初始化搜索器
    if searcher is None:
        # 创建带有写入模式的向量存储
        from src.storage.vector_store import VectorStore
        vector_store = VectorStore(read_only=False, data_dir="mock/data/annoy")
        searcher = BugSearcher(vector_store=vector_store)
    
    # 读取测试数据
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            mock_data = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]错误：找不到测试数据文件 {data_file}[/red]")
        return None
    except json.JSONDecodeError:
        console.print(f"[red]错误：测试数据文件 {data_file} 格式不正确[/red]")
        return None
    
    # 加载数据到系统
    total = len(mock_data)
    success = 0
    
    with console.status("[bold green]正在加载测试数据...") as status:
        for i, data in enumerate(mock_data, 1):
            try:
                # 创建BugReport对象
                bug_report = BugReport(
                    bug_id=data["bug_id"],
                    summary=data["summary"],
                    file_paths=data["file_paths"],
                    code_diffs=data["code_diffs"],
                    aggregated_added_code=data["aggregated_added_code"],
                    aggregated_removed_code=data["aggregated_removed_code"],
                    test_steps=data["test_steps"],
                    expected_result=data["expected_result"],
                    actual_result=data["actual_result"],
                    log_info=data["log_info"],
                    severity=data["severity"],
                    is_reappear=data["is_reappear"],
                    environment=data["environment"],
                    root_cause=data.get("root_cause"),
                    fix_solution=data.get("fix_solution"),
                    related_issues=data["related_issues"],
                    fix_person=data.get("fix_person"),
                    create_at=data["create_at"],
                    fix_date=data["fix_date"],
                    reopen_count=data["reopen_count"],
                    handlers=data["handlers"],
                    project_id=data["project_id"]
                )
                
                # 添加到知识库
                searcher.add_bug_report(bug_report)
                success += 1
                
                # 更新状态
                status.update(f"[bold green]正在加载测试数据... ({i}/{total})")
            except Exception as e:
                console.print(f"[red]加载Bug报告 {data.get('bug_id', '未知')} 失败: {str(e)}[/red]")
    
    # 显示加载结果
    if success == total:
        console.print(f"[bold green]成功加载全部 {total} 条测试数据[/bold green]")
    else:
        console.print(f"[yellow]加载完成：成功 {success}/{total} 条[/yellow]")
    
    return searcher

if __name__ == "__main__":
    load_mock_data() 
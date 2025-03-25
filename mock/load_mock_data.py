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
from rich.console import Console

console = Console()

def load_mock_data(data_file: str = "mock/data/bug_reports.json", searcher: BugSearcher = None):
    """加载测试数据到搜索器"""
    # 初始化搜索器
    if searcher is None:
        searcher = BugSearcher()
    
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
                        network_env=data["environment"].get("network_env")
                    ),
                    created_at=created_at,
                    updated_at=updated_at
                )
                
                # 添加到知识库
                searcher.add_bug_report(bug_report)
                success += 1
                
                # 更新状态
                status.update(f"[bold green]正在加载测试数据... ({i}/{total})")
            except Exception as e:
                console.print(f"[red]加载Bug报告 {data.get('id', '未知')} 失败: {str(e)}[/red]")
    
    # 显示加载结果
    if success == total:
        console.print(f"[bold green]成功加载全部 {total} 条测试数据[/bold green]")
    else:
        console.print(f"[yellow]加载完成：成功 {success}/{total} 条[/yellow]")
    
    return searcher

if __name__ == "__main__":
    load_mock_data() 
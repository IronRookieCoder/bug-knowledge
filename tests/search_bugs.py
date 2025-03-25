import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.retrieval.searcher import BugSearcher
from tests.utils.data_loader import load_test_data
from rich.console import Console
from rich.panel import Panel

console = Console()

def format_bug_report(bug: dict, index: int = None) -> Panel:
    """格式化bug报告为富文本面板"""
    similarity = f"相似度: {(1 - bug['distance']) * 100:.1f}%"
    
    content = [
        f"[dim]ID: {bug['id']}[/dim]\n",
        
        "[yellow]问题描述：[/yellow]",
        bug['description'] + "\n",
        
        "[yellow]重现步骤：[/yellow]",
        "\n".join(f"{i+1}. {step}" for i, step in enumerate(bug['steps_to_reproduce'])) + "\n",
        
        "[yellow]期望结果：[/yellow]",
        bug['expected_behavior'] + "\n",
        
        "[yellow]实际结果：[/yellow]",
        bug['actual_behavior'] + "\n",
        
        "[yellow]代码上下文：[/yellow]",
        f"文件：{bug['code_context']['file_path']}",
        f"行号：{bug['code_context']['line_range'][0]}-{bug['code_context']['line_range'][1]}",
        bug['code_context']['code'] + "\n",
        
        "[yellow]错误日志：[/yellow]",
        (bug['error_logs'] or "无") + "\n",
        
        "[yellow]环境信息：[/yellow]",
        f"运行时环境：{bug['environment']['runtime_env']}",
        f"操作系统：{bug['environment']['os_info']}",
    ]
    
    if bug['environment'].get('network_env'):
        content.append(f"网络环境：{bug['environment']['network_env']}")
    
    return Panel("\n".join(content), border_style="blue")

def search_bugs(searcher: BugSearcher = None):
    """Bug知识库搜索功能"""
    # 如果没有提供搜索器，加载测试数据
    if searcher is None:
        searcher = load_test_data()
    
    # 搜索界面
    console.print("\n[bold blue]=== Bug 知识库搜索系统 ===[/bold blue]\n")
    
    while True:
        console.print("\n请选择搜索类型：")
        console.print("[cyan]1.[/cyan] 按问题描述搜索")
        console.print("[cyan]2.[/cyan] 按代码内容搜索")
        console.print("[cyan]3.[/cyan] 按错误日志搜索")
        console.print("[cyan]4.[/cyan] 按环境信息搜索")
        console.print("[cyan]5.[/cyan] 混合搜索")
        console.print("[cyan]0.[/cyan] 退出")
        
        choice = input("\n请输入选项（0-5）: ")
        
        if choice == "0":
            break
        
        n_results = int(input("请输入要返回的结果数量（默认5）: ") or "5")
        
        if choice == "1":
            console.print("\n[yellow]问题描述搜索[/yellow]")
            console.print("支持以下格式：")
            console.print("1. 标题")
            console.print("2. 问题描述")
            console.print("3. 重现步骤：")
            console.print("4. 期望结果：")
            console.print("5. 实际结果：")
            console.print("\n请输入问题描述（支持多行，输入空行结束）：")
            
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            query = "\n".join(lines)
            
            results = searcher.search(
                query_text=query,
                n_results=n_results
            )
        elif choice == "2":
            console.print("\n[yellow]代码搜索[/yellow]")
            console.print("请输入代码片段（支持多行，输入空行结束）：")
            
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            query = "\n".join(lines)
            
            results = searcher.search(
                code_snippet=query,
                n_results=n_results
            )
        elif choice == "3":
            console.print("\n[yellow]错误日志搜索[/yellow]")
            console.print("请输入错误日志（支持多行，输入空行结束）：")
            
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            query = "\n".join(lines)
            
            results = searcher.search(
                error_log=query,
                n_results=n_results
            )
        elif choice == "4":
            console.print("\n[yellow]环境信息搜索[/yellow]")
            console.print("请输入环境信息（支持多行，输入空行结束）：")
            
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            query = "\n".join(lines)
            
            results = searcher.search(
                env_info=query,
                n_results=n_results
            )
        elif choice == "5":
            console.print("\n[yellow]=== 混合搜索 ===[/yellow]")
            
            # 问题描述
            console.print("\n[cyan]问题描述[/cyan]（支持多行，输入空行结束）：")
            query_lines = []
            while True:
                line = input()
                if not line:
                    break
                query_lines.append(line)
            query_text = "\n".join(query_lines)
            
            # 代码片段
            console.print("\n[cyan]代码片段[/cyan]（支持多行，输入空行结束）：")
            code_lines = []
            while True:
                line = input()
                if not line:
                    break
                code_lines.append(line)
            code_snippet = "\n".join(code_lines)
            
            # 错误日志
            console.print("\n[cyan]错误日志[/cyan]（支持多行，输入空行结束）：")
            log_lines = []
            while True:
                line = input()
                if not line:
                    break
                log_lines.append(line)
            error_log = "\n".join(log_lines)
            
            # 环境信息
            console.print("\n[cyan]环境信息[/cyan]（支持多行，输入空行结束）：")
            env_lines = []
            while True:
                line = input()
                if not line:
                    break
                env_lines.append(line)
            env_info = "\n".join(env_lines)
            
            results = searcher.search(
                query_text=query_text,
                code_snippet=code_snippet,
                error_log=error_log,
                env_info=env_info,
                n_results=n_results
            )
        else:
            console.print("\n[red]无效的选项！[/red]")
            continue
        
        # 显示搜索结果
        if results:
            console.print("\n[bold blue]=== 搜索结果 ===[/bold blue]")
            for i, result in enumerate(results, 1):
                console.print(format_bug_report(result, i))
                if i < len(results):
                    console.print()  # 添加空行分隔
        else:
            console.print("\n[yellow]未找到相关的bug报告[/yellow]")

if __name__ == "__main__":
    search_bugs() 
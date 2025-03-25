import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.layout import Layout
from typing import Optional
import uuid
from datetime import datetime

from src.models.bug_models import BugReport, CodeContext, EnvironmentInfo
from src.retrieval.searcher import BugSearcher

app = typer.Typer()
console = Console()
bug_searcher = BugSearcher()

def format_bug_report(bug: dict, index: int = None) -> Panel:
    """格式化bug报告为富文本面板"""
    title = f"{'#'+str(index) if index else ''} {bug['title']}"
    similarity = f"相似度: {(1 - bug['distance']) * 100:.1f}%"
    
    content = [
        f"[bold blue]{title}[/bold blue] [green]{similarity}[/green]",
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
    
    content.extend([
        f"\n[dim]创建时间：{datetime.fromisoformat(bug['created_at']).strftime('%Y-%m-%d %H:%M:%S')}",
        f"更新时间：{datetime.fromisoformat(bug['updated_at']).strftime('%Y-%m-%d %H:%M:%S')}[/dim]"
    ])
    
    return Panel("\n".join(content), title=title, border_style="blue")

@app.command()
def add_bug():
    """添加新的bug报告到知识库"""
    console.print("[bold blue]添加新的Bug报告[/bold blue]")
    
    # 收集基本信息
    title = typer.prompt("Bug标题")
    
    console.print("\n[yellow]问题描述[/yellow] (支持多行，输入空行结束)")
    description_lines = []
    while True:
        line = input()
        if not line:
            break
        description_lines.append(line)
    description = "\n".join(description_lines)
    
    reproducible = typer.confirm("是否可复现?")
    
    # 收集重现步骤
    console.print("\n[yellow]重现步骤[/yellow] (每行一个步骤，输入空行结束)")
    steps = []
    while True:
        step = input()
        if not step:
            break
        steps.append(step)
    
    console.print("\n[yellow]期望结果[/yellow] (支持多行，输入空行结束)")
    expected_lines = []
    while True:
        line = input()
        if not line:
            break
        expected_lines.append(line)
    expected_behavior = "\n".join(expected_lines)
    
    console.print("\n[yellow]实际结果[/yellow] (支持多行，输入空行结束)")
    actual_lines = []
    while True:
        line = input()
        if not line:
            break
        actual_lines.append(line)
    actual_behavior = "\n".join(actual_lines)
    
    # 收集代码信息
    console.print("\n[yellow]问题代码[/yellow] (支持多行，输入空行结束)")
    code_lines = []
    while True:
        line = input()
        if not line:
            break
        code_lines.append(line)
    code = "\n".join(code_lines)
    
    file_path = typer.prompt("文件路径")
    line_start = int(typer.prompt("起始行号"))
    line_end = int(typer.prompt("结束行号"))
    language = typer.prompt("编程语言")
    
    # 收集环境信息
    runtime_env = typer.prompt("运行时环境")
    os_info = typer.prompt("操作系统信息")
    network_env = typer.prompt("网络环境 (可选)", default="")
    
    # 收集错误日志
    console.print("\n[yellow]错误日志[/yellow] (支持多行，输入空行结束)")
    log_lines = []
    while True:
        line = input()
        if not line:
            break
        log_lines.append(line)
    error_logs = "\n".join(log_lines)
    
    # 创建BugReport对象
    bug_report = BugReport(
        id=f"BUG-{uuid.uuid4().hex[:8]}",
        title=title,
        description=description,
        reproducible=reproducible,
        steps_to_reproduce=steps,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
        code_context=CodeContext(
            code=code,
            file_path=file_path,
            line_range=(line_start, line_end),
            language=language
        ),
        error_logs=error_logs,
        environment=EnvironmentInfo(
            runtime_env=runtime_env,
            os_info=os_info,
            network_env=network_env if network_env else None
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # 保存到知识库
    bug_searcher.add_bug_report(bug_report)
    console.print(f"[bold green]Bug报告 {bug_report.id} 已添加到知识库[/bold green]")

@app.command()
def search(
    query: str = typer.Option("", help="问题描述"),
    code: str = typer.Option("", help="代码片段"),
    error_log: str = typer.Option("", help="错误日志"),
    env_info: str = typer.Option("", help="环境信息"),
    n_results: int = typer.Option(5, help="返回结果数量")
):
    """搜索相似的bug报告"""
    results = bug_searcher.search(
        query_text=query,
        code_snippet=code,
        error_log=error_log,
        env_info=env_info,
        n_results=n_results
    )
    
    if not results:
        console.print("[yellow]未找到相关的bug报告[/yellow]")
        return
    
    console.print("\n[bold blue]搜索结果：[/bold blue]")
    for i, result in enumerate(results, 1):
        console.print(format_bug_report(result, i))
        if i < len(results):
            console.print()  # 添加空行分隔

if __name__ == "__main__":
    app() 
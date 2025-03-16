import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
import uuid
from datetime import datetime

from src.models.bug_models import BugReport, CodeContext, EnvironmentInfo
from src.retrieval.searcher import BugSearcher

app = typer.Typer()
console = Console()
bug_searcher = BugSearcher()

@app.command()
def add_bug():
    """添加新的bug报告到知识库"""
    console.print("[bold blue]添加新的Bug报告[/bold blue]")
    
    # 收集基本信息
    title = typer.prompt("Bug标题")
    description = typer.prompt("问题描述")
    reproducible = typer.confirm("是否可复现?")
    
    # 收集重现步骤
    steps = []
    while True:
        step = typer.prompt("输入重现步骤 (直接回车结束)")
        if not step:
            break
        steps.append(step)
    
    expected_behavior = typer.prompt("期望行为")
    actual_behavior = typer.prompt("实际行为")
    
    # 收集代码信息
    code = typer.prompt("问题代码")
    file_path = typer.prompt("文件路径")
    line_start = int(typer.prompt("起始行号"))
    line_end = int(typer.prompt("结束行号"))
    language = typer.prompt("编程语言")
    
    # 收集环境信息
    runtime_env = typer.prompt("运行时环境")
    os_info = typer.prompt("操作系统信息")
    network_env = typer.prompt("网络环境 (可选)", default="")
    
    # 收集错误日志
    error_logs = typer.prompt("错误日志")
    
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
    
    # 创建结果表格
    table = Table(title="搜索结果")
    table.add_column("ID", style="cyan")
    table.add_column("标题", style="magenta")
    table.add_column("相似度", style="green")
    table.add_column("描述", style="blue")
    
    for result in results:
        similarity = 1 - result["distance"]  # 将距离转换为相似度
        table.add_row(
            result["id"],
            result["title"],
            f"{similarity:.2%}",
            result["description"][:100] + "..."
        )
    
    console.print(table)

def main():
    app() 
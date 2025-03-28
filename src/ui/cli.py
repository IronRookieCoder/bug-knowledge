import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.layout import Layout
from typing import Optional
import uuid
from datetime import datetime

from src.models.bug_models import BugReport
from src.retrieval.searcher import BugSearcher

app = typer.Typer()
console = Console()
bug_searcher = BugSearcher()

def format_bug_report(bug: dict, index: int = None) -> Panel:
    """格式化bug报告为富文本面板"""
    similarity = f"相似度: {(1 - bug['distance']) * 100:.1f}%" if 'distance' in bug else ""
    
    content = [
        f"[bold blue]BUG #{index if index else ''}[/bold blue] [green]{similarity}[/green]",
        f"[dim]ID: {bug['bug_id']}[/dim]\n",
        
        "[yellow]摘要：[/yellow]",
        bug['summary'] + "\n",
        
        "[yellow]重现步骤：[/yellow]",
        bug['test_steps'] + "\n",
        
        "[yellow]期望结果：[/yellow]",
        bug['expected_result'] + "\n",
        
        "[yellow]实际结果：[/yellow]",
        bug['actual_result'] + "\n",
        
        "[yellow]代码变更：[/yellow]",
        f"新增代码：\n{bug['aggregated_added_code']}\n",
        f"删除代码：\n{bug['aggregated_removed_code']}\n",
        
        "[yellow]错误日志：[/yellow]",
        (bug['log_info'] or "无") + "\n",
        
        "[yellow]环境信息：[/yellow]",
        bug['environment'] + "\n",
        
        "[yellow]严重程度：[/yellow]",
        bug['severity'] + "\n",
        
        "[yellow]是否可重现：[/yellow]",
        bug['is_reappear'] + "\n",
        
        "[yellow]根本原因：[/yellow]",
        (bug['root_cause'] or "未确定") + "\n",
        
        "[yellow]修复方案：[/yellow]",
        (bug['fix_solution'] or "未修复") + "\n",
        
        "[yellow]修复人员：[/yellow]",
        (bug['fix_person'] or "未分配") + "\n",
        
        "[yellow]处理人员：[/yellow]",
        ", ".join(bug['handlers']) + "\n",
        
        "[yellow]相关问题：[/yellow]",
        ", ".join(bug['related_issues']) + "\n",
        
        f"\n[dim]创建时间：{bug['create_at']}",
        f"修复时间：{bug['fix_date']}",
        f"重新打开次数：{bug['reopen_count']}[/dim]"
    ]
    
    return Panel("\n".join(content), title=f"BUG #{index if index else ''}", border_style="blue")

@app.command()
def add_bug():
    """添加新的bug报告到知识库"""
    console.print("[bold blue]添加新的Bug报告[/bold blue]")
    
    # 收集基本信息
    bug_id = typer.prompt("BUG ID")
    summary = typer.prompt("BUG摘要")
    
    console.print("\n[yellow]问题描述[/yellow] (支持多行，输入空行结束)")
    description_lines = []
    while True:
        line = input()
        if not line:
            break
        description_lines.append(line)
    description = "\n".join(description_lines)
    
    # 收集文件路径
    console.print("\n[yellow]受影响的文件路径[/yellow] (每行一个，输入空行结束)")
    file_paths = []
    while True:
        path = input()
        if not path:
            break
        file_paths.append(path)
    
    # 收集代码差异
    console.print("\n[yellow]代码差异[/yellow] (每行一个，输入空行结束)")
    code_diffs = []
    while True:
        diff = input()
        if not diff:
            break
        code_diffs.append(diff)
    
    # 收集聚合代码
    console.print("\n[yellow]新增代码[/yellow] (支持多行，输入空行结束)")
    added_code_lines = []
    while True:
        line = input()
        if not line:
            break
        added_code_lines.append(line)
    aggregated_added_code = "\n".join(added_code_lines)
    
    console.print("\n[yellow]删除代码[/yellow] (支持多行，输入空行结束)")
    removed_code_lines = []
    while True:
        line = input()
        if not line:
            break
        removed_code_lines.append(line)
    aggregated_removed_code = "\n".join(removed_code_lines)
    
    # 收集测试信息
    console.print("\n[yellow]重现步骤[/yellow] (支持多行，输入空行结束)")
    test_steps_lines = []
    while True:
        line = input()
        if not line:
            break
        test_steps_lines.append(line)
    test_steps = "\n".join(test_steps_lines)
    
    console.print("\n[yellow]期望结果[/yellow] (支持多行，输入空行结束)")
    expected_lines = []
    while True:
        line = input()
        if not line:
            break
        expected_lines.append(line)
    expected_result = "\n".join(expected_lines)
    
    console.print("\n[yellow]实际结果[/yellow] (支持多行，输入空行结束)")
    actual_lines = []
    while True:
        line = input()
        if not line:
            break
        actual_lines.append(line)
    actual_result = "\n".join(actual_lines)
    
    # 收集日志信息
    console.print("\n[yellow]错误日志[/yellow] (支持多行，输入空行结束)")
    log_lines = []
    while True:
        line = input()
        if not line:
            break
        log_lines.append(line)
    log_info = "\n".join(log_lines)
    
    # 收集其他信息
    severity = typer.prompt("严重程度")
    is_reappear = typer.prompt("是否可重现")
    environment = typer.prompt("环境信息")
    root_cause = typer.prompt("根本原因 (可选)", default="")
    fix_solution = typer.prompt("修复方案 (可选)", default="")
    
    # 收集相关人员信息
    console.print("\n[yellow]相关问题的ID[/yellow] (用逗号分隔)")
    related_issues = [x.strip() for x in typer.prompt("").split(",") if x.strip()]
    
    fix_person = typer.prompt("修复人员 (可选)", default="")
    create_at = datetime.now().isoformat()
    fix_date = typer.prompt("修复时间 (可选)", default="")
    
    console.print("\n[yellow]处理人员[/yellow] (用逗号分隔)")
    handlers = [x.strip() for x in typer.prompt("").split(",") if x.strip()]
    
    project_id = typer.prompt("项目ID")
    
    # 创建BugReport对象
    bug_report = BugReport(
        bug_id=bug_id,
        summary=summary,
        file_paths=file_paths,
        code_diffs=code_diffs,
        aggregated_added_code=aggregated_added_code,
        aggregated_removed_code=aggregated_removed_code,
        description=description,
        test_steps=test_steps,
        expected_result=expected_result,
        actual_result=actual_result,
        log_info=log_info,
        severity=severity,
        is_reappear=is_reappear,
        environment=environment,
        root_cause=root_cause if root_cause else None,
        fix_solution=fix_solution if fix_solution else None,
        related_issues=related_issues,
        fix_person=fix_person if fix_person else None,
        create_at=create_at,
        fix_date=fix_date if fix_date else None,
        reopen_count=0,
        handlers=handlers,
        project_id=project_id
    )
    
    # 保存到知识库
    bug_searcher.add_bug_report(bug_report)
    console.print(f"[bold green]Bug报告 {bug_report.bug_id} 已添加到知识库[/bold green]")

@app.command()
def search(
    summary: str = typer.Option("", help="缺陷的简要描述"),
    code: str = typer.Option("", help="代码片段"),
    test_steps: str = typer.Option("", help="重现缺陷的测试步骤"),
    expected_result: str = typer.Option("", help="预期结果"),
    actual_result: str = typer.Option("", help="实际结果"),
    log_info: str = typer.Option("", help="相关日志信息"),
    env: str = typer.Option("", help="缺陷发生的环境信息"),
    n_results: int = typer.Option(5, help="返回结果数量")
):
    """搜索相似的bug报告"""
    # 检查是否有任何搜索条件
    has_content = {
        "summary": bool(summary and summary.strip()),
        "code": bool(code and code.strip()),
        "test": bool((test_steps and test_steps.strip()) or 
                    (expected_result and expected_result.strip()) or 
                    (actual_result and actual_result.strip())),
        "log": bool(log_info and log_info.strip()),
        "env": bool(env and env.strip())
    }
    
    if not any(has_content.values()):
        console.print("[yellow]请至少输入一个搜索条件[/yellow]")
        return
    
    results = bug_searcher.search(
        summary=summary,
        code=code,
        test_steps=test_steps,
        expected_result=expected_result,
        actual_result=actual_result,
        log_info=log_info,
        env=env,
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
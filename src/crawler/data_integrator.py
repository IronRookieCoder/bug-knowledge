from dataclasses import dataclass
from typing import List, Optional
from src.crawler.td_crawler import IssueDetails
from src.utils.diff_preprocessor import preprocess_bug_diffs


@dataclass
class BugReport:
    bug_id: str  # 缺陷的唯一标识符
    summary: str  # 缺陷的简要描述
    file_paths: List[str]  # 受影响的文件路径列表
    code_diffs: List[str]  # 代码差异列表
    aggregated_added_code: str  # 所有新增代码的聚合
    aggregated_removed_code: str  # 所有删除代码的聚合
    description: str  # 缺陷的详细描述
    test_steps: str  # 重现缺陷的测试步骤
    expected_result: str  # 预期结果
    actual_result: str  # 实际结果
    log_info: str  # 相关日志信息
    severity: str  # 缺陷的严重程度
    is_reappear: str  # 缺陷是否可重现
    environment: str  # 缺陷发生的环境信息
    root_cause: Optional[str]  # 缺陷的根本原因
    fix_solution: Optional[str]  # 修复方案
    related_issues: List[str]  # 相关问题的列表
    fix_person: Optional[str]  # 负责修复的人员
    create_at: str  # 缺陷创建时间
    fix_date: str  # 缺陷修复时间
    reopen_count: int  # 缺陷重新打开的次数
    handlers: List[str]  # 处理该缺陷的人员列表
    project_id: str  # 关联gitlab仓库id


class DataIntegrator:
    @staticmethod
    def integrate(code_snippets: list, issue_details: IssueDetails) -> BugReport:
        # 预处理所有代码差异，获取聚合的新增和删除代码
        all_diffs = "\n".join([s.code_diff for s in code_snippets])
        preprocessed = preprocess_bug_diffs(all_diffs)
        project_id = code_snippets[0].project_id if code_snippets else ""

        return BugReport(
            bug_id=issue_details.bug_id,
            summary=issue_details.summary,
            file_paths=[s.file_path for s in code_snippets],
            code_diffs=[s.code_diff for s in code_snippets],
            aggregated_added_code=preprocessed['aggregated_added_code'] if preprocessed else "",
            aggregated_removed_code=preprocessed['aggregated_removed_code'] if preprocessed else "",
            description=issue_details.description,
            test_steps=issue_details.test_steps,
            expected_result=issue_details.expected_result,
            actual_result=issue_details.actual_result,
            log_info=issue_details.log_info,
            severity=issue_details.severity,
            is_reappear=issue_details.is_reappear,
            environment=issue_details.environment,
            root_cause=issue_details.root_cause,
            fix_solution=issue_details.fix_solution,
            related_issues=issue_details.related_issues,
            fix_person=issue_details.fix_person,
            create_at=issue_details.create_at,
            fix_date=issue_details.fix_date,
            reopen_count=issue_details.reopen_count,
            handlers=issue_details.handlers,
            project_id=project_id,
        )
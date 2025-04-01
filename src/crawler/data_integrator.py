from dataclasses import dataclass
from typing import List, Optional
from src.crawler.td_crawler import IssueDetails
from src.utils.diff_preprocessor import preprocess_bug_diffs
from src.models.bug_models import BugReport


class DataIntegrator:
    @staticmethod
    def integrate(code_snippets: list, issue_details: IssueDetails) -> BugReport:
        # 预处理所有代码差异，获取聚合的新增和删除代码
        all_diffs = "\n".join([s.code_diff for s in code_snippets])
        preprocessed = preprocess_bug_diffs(all_diffs)
        project_id = code_snippets[0].project_id if code_snippets else ""

        return BugReport(
            bug_id=issue_details.bug_id,
            summary=issue_details.summary or "",
            description=issue_details.description or "",
            file_paths=[s.file_path for s in code_snippets],
            code_diffs=[s.code_diff for s in code_snippets],
            aggregated_added_code=preprocessed['aggregated_added_code'] if preprocessed else "",
            aggregated_removed_code=preprocessed['aggregated_removed_code'] if preprocessed else "",
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
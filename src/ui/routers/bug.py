from fastapi import APIRouter, Form, HTTPException
from typing import List, Optional
from datetime import datetime
import json
import traceback
from src.utils.log import get_logger
from src.models.bug_models import BugReport
from src.retrieval.searcher_manager import get_bug_searcher

logger = get_logger(__name__)
router = APIRouter(prefix="/api/bugs", tags=["bugs"])

@router.post("")
async def create_bug(
    bug_id: str = Form(...),
    summary: str = Form(...),
    file_paths: Optional[str] = Form("[]"),
    code_diffs: Optional[str] = Form("[]"),
    aggregated_added_code: Optional[str] = Form(""),
    aggregated_removed_code: Optional[str] = Form(""),
    test_steps: Optional[str] = Form(""),
    expected_result: Optional[str] = Form(""),
    actual_result: Optional[str] = Form(""),
    log_info: Optional[str] = Form(""),
    severity: Optional[str] = Form(""),
    is_reappear: Optional[str] = Form(""),
    environment: Optional[str] = Form(""),
    root_cause: Optional[str] = Form(None),
    fix_solution: Optional[str] = Form(None),
    related_issues: Optional[str] = Form("[]"),
    fix_person: Optional[str] = Form(None),
    handlers: Optional[str] = Form("[]"),
    project_id: Optional[str] = Form(""),
):
    try:
        # 解析JSON字符串字段
        try:
            file_paths_list = json.loads(file_paths)
            code_diffs_list = json.loads(code_diffs)
            related_issues_list = json.loads(related_issues)
            handlers_list = json.loads(handlers)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=422,
                detail=f"JSON解析错误: {str(e)}"
            )

        bug_report = BugReport(
            bug_id=bug_id,
            summary=summary,
            file_paths=file_paths_list,
            code_diffs=code_diffs_list,
            aggregated_added_code=aggregated_added_code,
            aggregated_removed_code=aggregated_removed_code,
            test_steps=test_steps,
            expected_result=expected_result,
            actual_result=actual_result,
            log_info=log_info,
            severity=severity or "P3",  # 设置默认值
            is_reappear=is_reappear or "未知",  # 设置默认值
            environment=environment or "未知",  # 设置默认值
            root_cause=root_cause,
            fix_solution=fix_solution,
            related_issues=related_issues_list,
            fix_person=fix_person,
            create_at=datetime.now().isoformat(),
            fix_date=datetime.now().isoformat(),
            reopen_count=0,
            handlers=handlers_list,
            project_id=project_id or "default",  # 设置默认值
        )

        searcher = get_bug_searcher()
        searcher.add_bug_report(bug_report)
        return {"status": "success", "bug_id": bug_report.bug_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加Bug报告失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"添加Bug报告失败: {str(e)}")

@router.get("")
async def list_bugs(
    page: int = 1,
    page_size: int = 10,
    project_id: Optional[str] = None,
    severity: Optional[str] = None,
):
    try:
        searcher = get_bug_searcher()
        total, bugs = searcher.list_bugs(
            page=page,
            page_size=page_size,
            project_id=project_id,
            severity=severity
        )
        return {
            "status": "success",
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": bugs
        }
    except Exception as e:
        logger.error(f"获取Bug列表失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取Bug列表失败: {str(e)}")

@router.get("/{bug_id}")
async def get_bug(bug_id: str):
    try:
        searcher = get_bug_searcher()
        bug = searcher.get_bug_by_id(bug_id)
        if not bug:
            raise HTTPException(status_code=404, detail=f"Bug {bug_id} 不存在")
        return {"status": "success", "data": bug}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Bug详情失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取Bug详情失败: {str(e)}")

@router.put("/{bug_id}")
async def update_bug(
    bug_id: str,
    summary: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file_paths: Optional[str] = Form(None),
    code_diffs: Optional[str] = Form(None),
    aggregated_added_code: Optional[str] = Form(None),
    aggregated_removed_code: Optional[str] = Form(None),
    test_steps: Optional[str] = Form(None),
    expected_result: Optional[str] = Form(None),
    actual_result: Optional[str] = Form(None),
    log_info: Optional[str] = Form(None),
    severity: Optional[str] = Form(None),
    is_reappear: Optional[str] = Form(None),
    environment: Optional[str] = Form(None),
    root_cause: Optional[str] = Form(None),
    fix_solution: Optional[str] = Form(None),
    related_issues: Optional[str] = Form(None),
    fix_person: Optional[str] = Form(None),
    handlers: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
):
    try:
        searcher = get_bug_searcher()
        bug = searcher.get_bug_by_id(bug_id)
        if not bug:
            raise HTTPException(status_code=404, detail=f"Bug {bug_id} 不存在")
            
        update_data = {
            "summary": summary,
            "description": description,
            "aggregated_added_code": aggregated_added_code,
            "aggregated_removed_code": aggregated_removed_code,
            "test_steps": test_steps,
            "expected_result": expected_result,
            "actual_result": actual_result,
            "log_info": log_info,
            "severity": severity,
            "is_reappear": is_reappear,
            "environment": environment,
            "root_cause": root_cause,
            "fix_solution": fix_solution,
            "fix_person": fix_person,
            "project_id": project_id,
            "update_at": datetime.now().isoformat()
        }

        # 处理JSON字符串字段
        if file_paths is not None:
            try:
                update_data["file_paths"] = json.loads(file_paths)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=422, detail=f"file_paths JSON解析错误: {str(e)}")

        if code_diffs is not None:
            try:
                update_data["code_diffs"] = json.loads(code_diffs)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=422, detail=f"code_diffs JSON解析错误: {str(e)}")

        if related_issues is not None:
            try:
                update_data["related_issues"] = json.loads(related_issues)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=422, detail=f"related_issues JSON解析错误: {str(e)}")

        if handlers is not None:
            try:
                update_data["handlers"] = json.loads(handlers)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=422, detail=f"handlers JSON解析错误: {str(e)}")
        
        # 移除None值
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        searcher.update_bug(bug_id, update_data)
        return {"status": "success", "bug_id": bug_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Bug失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"更新Bug失败: {str(e)}")

@router.delete("/{bug_id}")
async def delete_bug(bug_id: str):
    try:
        searcher = get_bug_searcher()
        bug = searcher.get_bug_by_id(bug_id)
        if not bug:
            raise HTTPException(status_code=404, detail=f"Bug {bug_id} 不存在")
            
        searcher.delete_bug(bug_id)
        return {"status": "success", "bug_id": bug_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除Bug失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"删除Bug失败: {str(e)}")

@router.post("/search")
async def search_bugs(
    summary: str = Form(""),
    test_steps: str = Form(""),
    expected_result: str = Form(""),
    actual_result: str = Form(""),
    code: str = Form(""),
    error_logs: str = Form(""),
    n_results: int = Form(5),
):
    try:
        logger.info("收到搜索请求:")
        logger.info(f"  - 摘要: {summary[:50]}..." if len(summary) > 50 else f"  - 摘要: {summary}")
        logger.info(f"  - 代码长度: {len(code)}")
        logger.info(f"  - 测试步骤长度: {len(test_steps)}")
        logger.info(f"  - 预期结果长度: {len(expected_result)}")
        logger.info(f"  - 实际结果长度: {len(actual_result)}")
        logger.info(f"  - 日志长度: {len(error_logs)}")
        logger.info(f"  - 请求结果数量: {n_results}")

        has_content = {
            "summary": bool(summary and summary.strip()),
            "code": bool(code and code.strip()),
            "test": bool(
                (test_steps and test_steps.strip())
                or (expected_result and expected_result.strip())
                or (actual_result and actual_result.strip())
            ),
            "log": bool(error_logs and error_logs.strip()),
        }

        if not any(has_content.values()):
            logger.warning("没有提供任何搜索条件")
            return {"status": "error", "message": "请至少输入一个搜索条件"}

        searcher = get_bug_searcher()
        results = searcher.search(
            summary=summary,
            test_steps=test_steps,
            expected_result=expected_result,
            actual_result=actual_result,
            code=code,
            log_info=error_logs,
            n_results=n_results,
        )

        if results:
            logger.info(f"搜索完成, 获得 {len(results)} 个结果")
            return {"status": "success", "results": results[:n_results]}
        else:
            logger.info("未找到匹配的结果")
            return {"status": "success", "results": []}

    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return {"status": "error", "message": f"搜索失败: {str(e)}"}
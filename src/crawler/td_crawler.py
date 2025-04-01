import requests
import re
from dataclasses import dataclass
from typing import List, Optional, Dict
import time


@dataclass
class IssueDetails:
    bug_id: str
    summary: str
    severity: str
    is_reappear: str
    description: str
    test_steps: str
    expected_result: str
    actual_result: str
    log_info: str
    environment: str
    root_cause: Optional[str]
    fix_solution: Optional[str]
    related_issues: List[str]
    fix_person: Optional[str]
    create_at: str
    fix_date: str
    reopen_count: int
    handlers: List[str]


class TDCrawler:
    def __init__(self, base_urls: List[str], headers_list: List[dict]):
        self.base_urls = base_urls
        self.headers_list = headers_list

    def get_bug_details(self, bug_id: str, product_id: str) -> IssueDetails:
        for base_url, headers in zip(self.base_urls, self.headers_list):
            url = f"{base_url}/api/v1/defect/by_key/{bug_id}?_t={self._get_timestamp()}"
            headers["PRODUCT-ID"] = product_id
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            data_data = data.get("data", {})
            fields = data_data.get("fields", {})

            # 确保desc和comment字段为字符串类型
            desc_content = str(fields.get("desc", ""))  # 强制转换为字符串
            comment_content = str(fields.get("comment", ""))  # 强制转换为字符串

            return IssueDetails(
                bug_id=str(data_data.get("key")),
                summary=fields.get("summary", ""),
                severity=fields.get("severity", {}).get("name", "P4"),
                is_reappear=fields.get("is_reappear", {}).get("value", "1"),
                description=self._build_structured_description(desc_content),
                test_steps=self._parse_desc_section(desc_content, "测试步骤"),
                expected_result=self._parse_desc_section(desc_content, "期望结果"),
                actual_result=self._parse_desc_section(desc_content, "实际结果"),
                log_info=self._parse_desc_section(desc_content, "日志信息"),
                environment=self._parse_desc_section(desc_content, "测试环境"),
                root_cause=self._parse_comment_section(comment_content, r"问题根因.*?|问题原因.*?"),
                fix_solution=self._parse_comment_section(comment_content, "如何修改"),
                related_issues=self._parse_related_issues(comment_content),
                fix_person=fields.get("fix_person", {}).get("display_name"),
                create_at=fields.get("create_at", ""),
                fix_date=fields.get("fix_date", ""),
                reopen_count=fields.get("reopen_count", 0),
                handlers=fields.get("handlers", [])
            )

    def _build_structured_description(self, desc: str) -> str:
        """构建结构化的问题描述"""
        elements = {
            "测试步骤": self._parse_desc_section(desc, "测试步骤"),
            "期望结果": self._parse_desc_section(desc, "期望结果"),
            "实际结果": self._parse_desc_section(desc, "实际结果"),
            "日志信息": self._parse_desc_section(desc, "日志信息")
        }
        return "\n".join([f"{k}：{v}" for k, v in elements.items() if v])

    def _parse_desc_section(self, desc: str, section: str) -> str:
        """解析desc字段中的指定部分"""
        if not isinstance(desc, str):
            return ""
        try:
            match = re.search(
                rf"【{section}】</p><p>(.*?)(?=【|</p>)", desc, re.DOTALL)
            return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else ""
        except (AttributeError, TypeError):
            return ""

    def _parse_comment_section(self, comment: str, section: str) -> str:
        """解析comment字段中的指定部分"""
        if not isinstance(comment, str):
            return ""
        try:
            match = re.search(
                rf"【{section}】</p><p>(.*?)(?=<br/>|</p>|$)", comment, re.DOTALL)
            if match:
                return re.sub(r"<[^>]+>", "", match.group(1)).strip()
            return ""
        except (AttributeError, TypeError):
            return ""

    def _parse_related_issues(self, comment: str) -> List[str]:
        """解析关联问题ID（支持多种格式：BUG202303150001 / BUG:202303150001）"""
        return re.findall(r"BUG[\s_:：]*(\d+)", comment)

    def _get_timestamp(self) -> str:
        return str(int(time.time() * 1000))
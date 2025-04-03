import re
from src.utils.log import logger
from dataclasses import dataclass
from typing import List, Optional, Dict
from src.config import config
from src.utils.http_client import http_client

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
        logger.info(f"初始化TD爬虫，配置了 {len(base_urls)} 个TD系统")

    def get_bug_details_batch(self, bug_ids: List[str]) -> List[Optional[IssueDetails]]:
        """批量获取bug详情"""
        logger.info(f"开始批量获取 {len(bug_ids)} 个bug详情")
        results = http_client.chunk_concurrent_map(
            self._fetch_bug_details_batch,
            bug_ids
        )
        logger.info(f"批量获取完成，成功获取 {len(results)} 个bug详情")
        return results

    def _fetch_bug_details_batch(self, bug_ids: List[str]) -> List[IssueDetails]:
        """批量获取一组bug详情"""
        logger.debug(f"处理一批 {len(bug_ids)} 个bug ID")
        results = []
        for bug_id in bug_ids:
            try:
                result = self.get_bug_details(bug_id)
                if result:
                    results.append(result)
                    logger.debug(f"成功获取bug {bug_id} 的详情")
                else:
                    logger.warning(f"未找到bug {bug_id} 的详情")
            except Exception as e:
                logger.error(f"获取bug {bug_id} 详情时发生错误: {str(e)}")
        logger.debug(f"本批次完成，成功获取 {len(results)}/{len(bug_ids)} 个bug详情")
        return results

    def get_bug_details(self, bug_id: str) -> Optional[IssueDetails]:
        """获取bug详情，遍历所有配置直到找到匹配的bug"""
        logger.debug(f"尝试获取bug {bug_id} 的详情")
        for idx, (base_url, headers) in enumerate(zip(self.base_urls, self.headers_list)):
            try:
                logger.debug(f"尝试从TD系统 {idx + 1} 获取bug {bug_id} 的详情")
                result = self._fetch_bug_details(bug_id, base_url, headers)
                if result:
                    logger.debug(f"在TD系统 {idx + 1} 中找到bug {bug_id} 的详情")
                    return result
            except Exception as e:
                logger.warning(f"从TD系统 {idx + 1} 获取bug {bug_id} 详情失败: {str(e)}")
                continue
        logger.warning(f"在所有TD系统中都未找到bug {bug_id} 的详情")
        return None

    def _fetch_bug_details(self, bug_id: str, base_url: str, headers: dict) -> Optional[IssueDetails]:
        """从指定的TD系统获取bug详情"""
        url = f"{base_url}/api/v1/defect/by_key/{bug_id}?_t={self._get_timestamp()}"
        
        response = http_client.get(url, headers=headers)
        data = response.json()
        data_data = data.get("data", {})
        if not data_data:
            logger.debug(f"TD系统返回的数据中没有找到bug {bug_id} 的详情")
            return None
            
        fields = data_data.get("fields", {})
        logger.debug(f"成功获取bug {bug_id} 的原始数据，开始解析")

        # 确保desc和comment字段为字符串类型
        desc_content = str(fields.get("desc", ""))
        comment_content = str(fields.get("comment", ""))

        # 创建IssueDetails对象
        try:
            issue = IssueDetails(
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
            logger.debug(f"成功解析bug {bug_id} 的详情数据")
            return issue
        except Exception as e:
            logger.error(f"解析bug {bug_id} 的详情数据时发生错误: {str(e)}")
            raise

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
        except (AttributeError, TypeError) as e:
            logger.warning(f"解析{section}部分时发生错误: {str(e)}")
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
        except (AttributeError, TypeError) as e:
            logger.warning(f"解析评论{section}部分时发生错误: {str(e)}")
            return ""

    def _parse_related_issues(self, comment: str) -> List[str]:
        """解析关联问题ID"""
        try:
            related = re.findall(r"BUG[\s_:：]*(\d+)", comment)
            if related:
                logger.debug(f"找到 {len(related)} 个关联的bug ID")
            return related
        except Exception as e:
            logger.warning(f"解析关联问题时发生错误: {str(e)}")
            return []

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        import time
        return str(int(time.time() * 1000))
from src.utils.log import get_logger
from typing import List, Optional, Dict, Any
import re
from src.config import config
from src.utils.http_client import http_client
from src.models.bug_models import BugReport

logger = get_logger(__name__)


class TDCrawler:
    def __init__(self, base_urls: List[str], headers_list: List[dict]):
        # 参数验证
        if not isinstance(base_urls, list) or not isinstance(headers_list, list):
            logger.error(f"初始化TD爬虫失败: base_urls或headers_list不是列表类型")
            self.base_urls = []
            self.headers_list = []
            return
            
        if len(base_urls) != len(headers_list):
            logger.error(f"初始化TD爬虫失败: base_urls和headers_list长度不匹配")
            self.base_urls = []
            self.headers_list = []
            return
            
        self.base_urls = base_urls
        self.headers_list = headers_list
        logger.info(f"初始化TD爬虫，配置了 {len(base_urls)} 个TD系统")

    def get_bug_details_batch(self, bug_ids: List[str]) -> List[Optional[BugReport]]:
        """批量获取bug详情"""
        # 验证bug_ids参数
        if not isinstance(bug_ids, list):
            logger.error(f"批量获取bug详情失败: bug_ids不是列表类型, 而是 {type(bug_ids)}")
            return []
            
        # 过滤空的或非字符串的bug_id
        valid_bug_ids = [bid for bid in bug_ids if isinstance(bid, str) and bid]
        if len(valid_bug_ids) != len(bug_ids):
            logger.warning(f"过滤了 {len(bug_ids) - len(valid_bug_ids)} 个无效的bug ID")
            
        if not valid_bug_ids:
            logger.warning("没有有效的bug ID，跳过批量获取")
            return []
        
        logger.info(f"开始批量获取 {len(valid_bug_ids)} 个bug详情")
        return http_client.chunk_concurrent_map(
            self._fetch_bug_details_batch,
            valid_bug_ids,
        )

    def _fetch_bug_details_batch(self, bug_ids: List[str]) -> List[Optional[BugReport]]:
        """批量获取一组bug详情"""
        # 参数验证
        if not isinstance(bug_ids, list) or not bug_ids:
            logger.warning("接收到空的或无效的bug_ids列表")
            return []
            
        logger.debug(f"处理一批 {len(bug_ids)} 个bug ID")
        results = []
        for bug_id in bug_ids:
            # 验证每个bug_id
            if not isinstance(bug_id, str) or not bug_id:
                logger.warning(f"跳过无效的bug ID: {bug_id}")
                continue
                
            try:
                result = self.get_bug_details(bug_id)
                if result:
                    results.append(result)
                    logger.debug(f"成功获取bug {bug_id} 的详情")
            except Exception as e:
                logger.error(f"获取bug {bug_id} 详情时发生错误: {str(e)}")
                continue
        logger.debug(f"本批次完成，成功获取 {len(results)}/{len(bug_ids)} 个bug详情")
        return results

    def get_bug_details(self, bug_id: str) -> Optional[BugReport]:
        """获取bug详情，遍历所有配置直到找到匹配的bug"""
        # 参数验证
        if not isinstance(bug_id, str) or not bug_id:
            logger.error(f"获取bug详情失败: 无效的bug_id - {bug_id}")
            return None
            
        # 验证爬虫状态
        if not self.base_urls or not self.headers_list:
            logger.error("获取bug详情失败: TD爬虫未正确初始化")
            return None
            
        logger.debug(f"尝试获取bug {bug_id} 的详情")
        for idx, (base_url, headers) in enumerate(
            zip(self.base_urls, self.headers_list)
        ):
            try:
                # 验证每个系统的参数
                if not isinstance(base_url, str) or not base_url:
                    logger.warning(f"TD系统 {idx + 1} 的base_url无效，跳过")
                    continue
                    
                if not isinstance(headers, dict):
                    logger.warning(f"TD系统 {idx + 1} 的headers无效，跳过")
                    continue
                    
                logger.debug(f"尝试从TD系统 {idx + 1} 获取bug {bug_id} 的详情")
                result = self._fetch_bug_details(bug_id, base_url, headers)
                if result:
                    logger.debug(f"在TD系统 {idx + 1} 中找到bug {bug_id} 的详情")
                    return result
            except Exception as e:
                logger.warning(
                    f"从TD系统 {idx + 1} 获取bug {bug_id} 详情失败: {str(e)}"
                )
                continue
        logger.warning(f"在所有TD系统中都未找到bug {bug_id} 的详情")
        return None

    def _fetch_bug_details(
        self, bug_id: str, base_url: str, headers: dict
    ) -> Optional[BugReport]:
        """从指定的TD系统获取bug详情"""
        try:
            # 安全检查参数
            if not isinstance(bug_id, str) or not bug_id:
                logger.error("无效的bug_id")
                return None
                
            if not isinstance(base_url, str) or not base_url:
                logger.error("无效的base_url")
                return None
                
            if not isinstance(headers, dict):
                logger.error("无效的headers")
                return None
                
            url = f"{base_url}/api/v1/defect/by_key/{bug_id}?_t={self._get_timestamp()}"

            response = http_client.get(url, headers=headers)
            data = response.json()
            
            # 验证响应数据
            if not isinstance(data, dict):
                logger.warning(f"TD系统返回的数据格式错误: {type(data)}")
                return None
                
            data_data = data.get("data", {})
            if not data_data or not isinstance(data_data, dict):
                logger.debug(f"TD系统返回的数据中没有找到bug {bug_id} 的详情")
                return None

            fields = data_data.get("fields", {})
            if not isinstance(fields, dict):
                logger.warning(f"Bug {bug_id} 的fields字段不是字典类型")
                return None

            logger.debug(f"成功获取bug {bug_id} 的原始数据，开始解析")

            # 确保所有字段都是正确的类型
            desc_content = self._safe_str(fields.get("desc", ""))
            comment_content = self._safe_str(fields.get("comment", ""))
            
            # 安全处理嵌套对象
            severity_data = fields.get("severity", {})
            severity = self._safe_str(severity_data.get("name", "P4") if isinstance(severity_data, dict) else "P4")
            
            is_reappear_data = fields.get("is_reappear", {})
            is_reappear = self._safe_str(is_reappear_data.get("value", "1") if isinstance(is_reappear_data, dict) else "1")
            
            fix_person_data = fields.get("fix_person", {})
            fix_person = self._safe_str(fix_person_data.get("display_name", "") if isinstance(fix_person_data, dict) else "")

            # 安全处理数组
            handlers_data = fields.get("handlers", [])
            handlers = [self._safe_str(h) for h in handlers_data] if isinstance(handlers_data, list) else []

            # 创建BugReport对象
            bug_report = BugReport(
                bug_id=self._safe_str(data_data.get("key", "")),
                summary=self._safe_str(fields.get("summary", "")),
                severity=severity,
                is_reappear=is_reappear,
                description=self._clean_html_tags(desc_content),
                test_steps=self._parse_desc_section(desc_content, "测试步骤"),
                expected_result=self._parse_desc_section(desc_content, "期望结果"),
                actual_result=self._parse_desc_section(desc_content, "实际结果"),
                log_info=self._parse_desc_section(desc_content, "日志信息"),
                environment=self._parse_desc_section(desc_content, "测试环境"),
                root_cause=self._parse_comment_section(
                    comment_content, r"问题根因.*?|问题原因.*?"
                ),
                fix_solution=self._parse_comment_section(comment_content, "如何修改"),
                related_issues=self._parse_related_issues(comment_content),
                fix_person=fix_person,
                create_at=self._safe_str(fields.get("create_at", "")),
                fix_date=self._safe_str(fields.get("fix_date", "")),
                reopen_count=int(fields.get("reopen_count", 0)),
                handlers=handlers
            )
            logger.debug(f"成功解析bug {bug_id} 的详情数据")
            return bug_report

        except Exception as e:
            logger.error(f"获取或解析bug {bug_id} 详情时发生错误: {str(e)}")
            raise

    def _build_structured_description(self, desc: str) -> str:
        """构建结构化的问题描述"""
        if not isinstance(desc, str):
            return ""
            
        elements = {
            "测试步骤": self._parse_desc_section(desc, "测试步骤"),
            "期望结果": self._parse_desc_section(desc, "期望结果"),
            "实际结果": self._parse_desc_section(desc, "实际结果"),
            "日志信息": self._parse_desc_section(desc, "日志信息"),
        }
        return "\n".join([f"{k}：{v}" for k, v in elements.items() if v])

    def _parse_desc_section(self, desc: str, section: str) -> str:
        """解析desc字段中的指定部分"""
        if not isinstance(desc, str) or not desc:
            return ""
            
        if not isinstance(section, str) or not section:
            return ""
            
        try:
            match = re.search(rf"【{section}】</p><p>(.*?)(?=【|</p>)", desc, re.DOTALL)
            return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else ""
        except (AttributeError, TypeError) as e:
            logger.warning(f"解析{section}部分时发生错误: {str(e)}")
            return ""

    def _parse_comment_section(self, comment: str, section: str) -> str:
        """解析comment字段中的指定部分"""
        if not isinstance(comment, str) or not comment:
            return ""
            
        if not isinstance(section, str) or not section:
            return ""
            
        try:
            match = re.search(
                rf"【{section}】</p><p>(.*?)(?=<br/>|</p>|$)", comment, re.DOTALL
            )
            if match:
                return re.sub(r"<[^>]+>", "", match.group(1)).strip()
            return ""
        except (AttributeError, TypeError) as e:
            logger.warning(f"解析评论{section}部分时发生错误: {str(e)}")
            return ""

    def _parse_related_issues(self, comment: str) -> List[str]:
        """解析关联问题ID"""
        if not isinstance(comment, str) or not comment:
            return []
            
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
        
    def _safe_str(self, value: Any) -> str:
        """安全地将任何值转换为字符串"""
        if value is None:
            return ""
        try:
            return str(value)
        except Exception:
            return ""

    def _clean_html_tags(self, text: str) -> str:
        """清理文本中的HTML标签"""
        if not isinstance(text, str):
            return ""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 替换多个换行符为单个换行符
        text = re.sub(r'\n+', '\n', text)
        # 替换多个空格为单个空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

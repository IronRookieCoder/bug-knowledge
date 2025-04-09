from typing import List, Dict, Optional, Any
from src.crawler.gitlab_crawler import CodeSnippet
from src.crawler.td_crawler import TDCrawler
from src.config import config
from src.utils.diff_preprocessor import preprocess_bug_diffs
from src.models.bug_models import BugReport
from src.utils.log import get_logger

logger = get_logger(__name__)

class DataIntegrator:
    def __init__(self):
        self._init_td_crawler()

    def _init_td_crawler(self):
        # 初始化TD爬虫实例
        td_configs = config.get_td_configs()
        
        if not td_configs:
            logger.warning("未找到有效的TD配置")
            self.td_crawler = None
            return
            
        try:
            urls = []
            headers_list = []
            
            for cfg in td_configs:
                urls.append(cfg.url)
                headers_list.append(cfg.headers)
            
            if not urls or not headers_list:
                logger.warning("没有有效的TD系统配置")
                self.td_crawler = None
                return
                
            self.td_crawler = TDCrawler(
                base_urls=urls,
                headers_list=headers_list
            )
            logger.info(f"成功初始化TD爬虫，配置了 {len(urls)} 个系统")
        except Exception as e:
            logger.error(f"初始化TD爬虫失败: {str(e)}")
            self.td_crawler = None

    @staticmethod
    def integrate(code_snippets: List[CodeSnippet], bug_report: BugReport) -> BugReport:
        """整合代码片段和bug详情"""
        try:
            # 验证输入参数
            if not isinstance(code_snippets, list) or not code_snippets:
                logger.warning("无效的code_snippets参数")
                return bug_report
                
            if not isinstance(bug_report, BugReport):
                logger.error(f"无效的bug_report参数，类型: {type(bug_report)}")
                return bug_report
                
            # 预处理所有代码差异，获取聚合的新增和删除代码
            all_diffs = "\n".join([s.code_diff for s in code_snippets if hasattr(s, 'code_diff') and s.code_diff])
            
            try:
                preprocessed = preprocess_bug_diffs(all_diffs)
            except Exception as e:
                logger.error(f"处理代码差异时发生错误: {str(e)}")
                preprocessed = None
                
            # 获取项目ID
            project_id = ""
            if code_snippets and hasattr(code_snippets[0], 'project_id'):
                project_id = str(code_snippets[0].project_id)

            # 使用现有的 BugReport，只更新代码相关字段，确保类型正确
            try:
                bug_report.file_paths = [str(s.file_path) for s in code_snippets if hasattr(s, 'file_path') and s.file_path]
            except Exception as e:
                logger.error(f"设置file_paths时发生错误: {str(e)}")
                bug_report.file_paths = []
                
            try:
                bug_report.code_diffs = [str(s.code_diff) for s in code_snippets if hasattr(s, 'code_diff') and s.code_diff]
            except Exception as e:
                logger.error(f"设置code_diffs时发生错误: {str(e)}")
                bug_report.code_diffs = []
                
            try:
                bug_report.aggregated_added_code = str(preprocessed.get('aggregated_added_code', "")) if preprocessed else ""
                bug_report.aggregated_removed_code = str(preprocessed.get('aggregated_removed_code', "")) if preprocessed else ""
            except Exception as e:
                logger.error(f"设置聚合代码时发生错误: {str(e)}")
                bug_report.aggregated_added_code = ""
                bug_report.aggregated_removed_code = ""
                
            bug_report.project_id = project_id

            # 确保其他关键字段类型正确
            try:
                if not hasattr(bug_report, 'related_issues') or not isinstance(bug_report.related_issues, list):
                    bug_report.related_issues = []
                    
                if not hasattr(bug_report, 'handlers') or not isinstance(bug_report.handlers, list):
                    bug_report.handlers = []
            except Exception as e:
                logger.error(f"验证字段类型时发生错误: {str(e)}")
                
            return bug_report
        except Exception as e:
            logger.error(f"数据整合失败: {str(e)}")
            # 返回原始bug_report，避免完全失败
            return bug_report
from typing import List, Dict, Optional, Any
from src.crawler.gitlab_crawler import GitLabCrawler, CodeSnippet
from src.crawler.td_crawler import TDCrawler
from src.crawler.config import Config
from src.utils.diff_preprocessor import preprocess_bug_diffs
from src.models.bug_models import BugReport
from src.utils.log import get_logger

logger = get_logger(__name__)

class DataIntegrator:
    def __init__(self):
        self.config = Config()
        self._init_crawlers()

    def _init_crawlers(self):
        # 初始化GitLab爬虫实例
        gitlab_configs = self.config.get_gitlab_configs()
        self.gitlab_crawlers = []
        
        if not gitlab_configs:
            logger.warning("未找到有效的GitLab配置")
            return
            
        for config in gitlab_configs:
            # 验证配置
            if not isinstance(config, dict):
                logger.warning(f"跳过无效的GitLab配置: {config}")
                continue
                
            url = config.get("url")
            token = config.get("token")
            project_ids = config.get("project_ids")
            
            if not url or not token or not project_ids:
                logger.warning(f"GitLab配置缺少必要参数, 跳过: {config}")
                continue
                
            try:
                self.gitlab_crawlers.append(
                    GitLabCrawler(
                        base_url=url,
                        private_token=token,
                        project_ids=project_ids,
                        since_date=self.config.GITLAB_SINCE_DATE,
                        until_date=self.config.GITLAB_UNTIL_DATE
                    )
                )
                logger.info(f"成功初始化GitLab爬虫: {url}")
            except Exception as e:
                logger.error(f"初始化GitLab爬虫失败: {url}, 错误: {str(e)}")

        # 初始化TD爬虫实例
        td_configs = self.config.get_td_configs()
        
        if not td_configs:
            logger.warning("未找到有效的TD配置")
            return
            
        try:
            urls = []
            headers_list = []
            
            for cfg in td_configs:
                if not isinstance(cfg, dict):
                    logger.warning(f"跳过无效的TD配置: {cfg}")
                    continue
                    
                url = cfg.get("url")
                headers = cfg.get("headers")
                
                if not url or not headers:
                    logger.warning(f"TD配置缺少必要参数, 跳过: {cfg}")
                    continue
                    
                urls.append(url)
                headers_list.append(headers)
            
            if not urls or not headers_list:
                logger.warning("没有有效的TD系统配置")
                return
                
            self.td_crawler = TDCrawler(
                base_urls=urls,
                headers_list=headers_list
            )
            logger.info(f"成功初始化TD爬虫，配置了 {len(urls)} 个系统")
        except Exception as e:
            logger.error(f"初始化TD爬虫失败: {str(e)}")
            self.td_crawler = None

    def collect_bug_data(self) -> List[Dict]:
        """收集所有系统的bug数据"""
        all_bugs = []
        
        # 验证爬虫是否正确初始化
        if not hasattr(self, 'gitlab_crawlers') or not self.gitlab_crawlers:
            logger.error("GitLab爬虫未正确初始化")
            return all_bugs
            
        if not hasattr(self, 'td_crawler') or not self.td_crawler:
            logger.error("TD爬虫未正确初始化")
            return all_bugs
        
        # 从每个GitLab实例收集数据
        for crawler in self.gitlab_crawlers:
            try:
                commits = crawler.get_commits_for_all_projects()
                if not commits:
                    logger.warning(f"GitLab实例未返回提交数据: {crawler.base_url}")
                    continue
                    
                logger.info(f"开始处理 {crawler.base_url} 的 {len(commits)} 个提交")
                
                for commit in commits:
                    if not isinstance(commit, dict) or not commit.get("project_id"):
                        logger.warning(f"跳过无效的提交: {commit}")
                        continue
                        
                    try:
                        snippets = crawler.parse_commit(commit["project_id"], commit)
                        if not snippets:
                            continue
                            
                        # 获取第一个snippet中的bug_id（因为同一个commit的所有snippet共享同一个bug_id）
                        bug_id = snippets[0].bug_id
                        if not bug_id:
                            logger.debug(f"提交 {commit.get('id', '未知')} 未关联bug ID")
                            continue
                            
                        # 获取bug详情
                        bug_details = self.td_crawler.get_bug_details(bug_id)
                        if bug_details:
                            all_bugs.append({
                                "bug_details": bug_details,
                                "code_snippets": snippets
                            })
                            logger.debug(f"成功收集bug {bug_id} 的完整数据")
                    except Exception as e:
                        logger.error(f"处理提交时发生错误: {str(e)}, commit_id: {commit.get('id', '未知')}")
                        continue
            except Exception as e:
                logger.error(f"从GitLab {crawler.base_url} 收集数据时发生错误: {str(e)}")
                continue

        logger.info(f"共收集到 {len(all_bugs)} 个完整的bug数据")
        return all_bugs

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
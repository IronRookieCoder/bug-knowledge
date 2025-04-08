from typing import List, Dict
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
        for config in gitlab_configs:
            self.gitlab_crawlers.append(
                GitLabCrawler(
                    base_url=config["url"],
                    private_token=config["token"],
                    project_ids=config["project_ids"],
                    since_date=self.config.GITLAB_SINCE_DATE,
                    until_date=self.config.GITLAB_UNTIL_DATE
                )
            )

        # 初始化TD爬虫实例
        td_configs = self.config.get_td_configs()
        urls = [cfg["url"] for cfg in td_configs]
        headers_list = [cfg["headers"] for cfg in td_configs]
        
        self.td_crawler = TDCrawler(
            base_urls=urls,
            headers_list=headers_list
        )

    def collect_bug_data(self) -> List[Dict]:
        """收集所有系统的bug数据"""
        all_bugs = []
        
        # 从每个GitLab实例收集数据
        for crawler in self.gitlab_crawlers:
            commits = crawler.get_commits_for_all_projects()
            for commit in commits:
                snippets = crawler.parse_commit(commit["project_id"], commit)
                if snippets:
                    # 获取第一个snippet中的bug_id（因为同一个commit的所有snippet共享同一个bug_id）
                    bug_id = snippets[0].bug_id
                    # 获取bug详情
                    bug_details = self.td_crawler.get_bug_details(bug_id)
                    if bug_details:
                        all_bugs.append({
                            "bug_details": bug_details,
                            "code_snippets": snippets
                        })

        return all_bugs

    @staticmethod
    def integrate(code_snippets: list, bug_report: BugReport) -> BugReport:
        """整合代码片段和bug详情"""
        # 预处理所有代码差异，获取聚合的新增和删除代码
        all_diffs = "\n".join([s.code_diff for s in code_snippets])
        preprocessed = preprocess_bug_diffs(all_diffs)
        project_id = code_snippets[0].project_id if code_snippets else ""

        # 使用现有的 BugReport，只更新代码相关字段
        bug_report.file_paths = [s.file_path for s in code_snippets]
        bug_report.code_diffs = [s.code_diff for s in code_snippets]
        bug_report.aggregated_added_code = preprocessed['aggregated_added_code'] if preprocessed else ""
        bug_report.aggregated_removed_code = preprocessed['aggregated_removed_code'] if preprocessed else ""
        bug_report.project_id = project_id

        return bug_report
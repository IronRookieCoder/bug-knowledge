from src.crawler.config import Config
from src.crawler.gitlab_crawler import GitLabCrawler, CodeSnippet
from src.crawler.td_crawler import TDCrawler, IssueDetails
from src.crawler.data_integrator import DataIntegrator, BugReport
from src.storage.database import BugDatabase
from src.utils.log import logging
logger = logging.getLogger(__name__)

def main():
    # 初始化组件
    db = BugDatabase(Config.DATABASE_PATH)
    
    # 处理GitLab数据
    code_snippets_map = {}
    
    # 遍历所有GitLab配置
    for gl_config in Config.get_gitlab_configs():
        gl_crawler = GitLabCrawler(
            gl_config["url"],
            gl_config["token"],
            gl_config["project_ids"],
            Config.GITLAB_SINCE_DATE,
            Config.GITLAB_UNTIL_DATE,
        )
        
        commits = gl_crawler.get_commits_for_all_projects()
        for commit in commits:
            project_id = commit.get('project_id')
            snippets = gl_crawler.parse_commit(project_id, commit)
            for snippet in snippets:
                code_snippets_map.setdefault(
                    snippet.bug_id, []).append(snippet)

    # 处理TD系统数据
    td_crawler = TDCrawler(
        [config["url"] for config in Config.get_td_configs()],
        [config["headers"] for config in Config.get_td_configs()]
    )

    for bug_id in code_snippets_map.keys():
        try:
            # 尝试从每个TD配置获取bug详情
            issue_details = None
            for product_id in Config.PRODUCT_IDS:
                try:
                    issue_details = td_crawler.get_bug_details(bug_id, product_id)
                    if issue_details:
                        break
                except Exception as e:
                    logger(f"Error fetching details for bug {bug_id} with product_id {product_id}: {str(e)}")
                    continue

            if not issue_details:
                logger(f"Could not fetch details for bug {bug_id} from any TD configuration")
                continue

        except Exception as e:
            logger(f"Error fetching details for bug {bug_id}: {str(e)}")
            continue

        try:
            report = DataIntegrator.integrate(
                code_snippets_map[bug_id],
                issue_details
            )
        except Exception as e:
            logger(f"Error integrating data for bug {bug_id}: {str(e)}")
            continue

        try:
            # 将BugReport对象转换为字典
            report_dict = report.__dict__
            db.add_bug_report(bug_id, report_dict)
        except Exception as e:
            logger(f"Error saving report for bug {bug_id}: {str(e)}")
            continue


if __name__ == "__main__":
    main()
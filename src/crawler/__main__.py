from src.config import config
from src.crawler.gitlab_crawler import GitLabCrawler, CodeSnippet
from src.crawler.td_crawler import TDCrawler, IssueDetails
from src.crawler.data_integrator import DataIntegrator, BugReport
from src.storage.database import BugDatabase
from src.utils.log import get_logger

logger = get_logger(__name__)


def get_gitlab_snippets(gl_configs):
    """从GitLab获取代码片段"""
    code_snippets_map = {}
    for gl_config in gl_configs:
        try:
            gl_crawler = GitLabCrawler(
                gl_config["url"],
                gl_config["token"],
                gl_config["project_ids"],
                config.get("GITLAB_SINCE_DATE"),
                config.get("GITLAB_UNTIL_DATE"),
            )

            commits = gl_crawler.get_commits_for_all_projects()
            if not commits:
                logger.warning(
                    f"No commits found for GitLab config: {gl_config['url']}"
                )
                continue

            for commit in commits:
                try:
                    project_id = commit.get("project_id")
                    if not project_id:
                        logger.warning(f"Missing project_id in commit: {commit}")
                        continue

                    snippets = gl_crawler.parse_commit(project_id, commit)
                    for snippet in snippets:
                        code_snippets_map.setdefault(snippet.bug_id, []).append(snippet)
                except Exception as e:
                    logger.error(f"Error processing commit {commit}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error with GitLab config {gl_config['url']}: {str(e)}")
            continue

    return code_snippets_map


def get_td_issue_details(td_crawler, td_configs, bug_id):
    """从TD系统获取bug详情"""
    for td_config in td_configs:
        try:
            issue_details = td_crawler.get_bug_details(bug_id)
            if issue_details:
                return issue_details
        except Exception as e:
            logger.error(f"Error with TD config {td_config['url']}: {str(e)}")
            continue
    return None


def main():
    try:
        # 初始化数据库
        db = BugDatabase(config.database_path)

        # 获取GitLab代码片段
        gl_configs = config.get_gitlab_configs()
        if not gl_configs:
            logger.error("No valid GitLab configurations found")
            return

        code_snippets_map = get_gitlab_snippets(gl_configs)
        if not code_snippets_map:
            logger.error("No code snippets found from any GitLab source")
            return

        # 初始化TD爬虫
        td_configs = config.get_td_configs()
        if not td_configs:
            logger.error("No valid TD configurations found")
            return

        td_crawler = TDCrawler(
            [cfg["url"] for cfg in td_configs], [cfg["headers"] for cfg in td_configs]
        )

        # 处理每个bug
        for bug_id in code_snippets_map:
            try:
                # 检查bug是否已存在
                if db.bug_id_exists(bug_id):
                    logger.info(f"Bug {bug_id} already exists in database, skipping...")
                    continue

                # 获取bug详情
                issue_details = get_td_issue_details(td_crawler, td_configs, bug_id)
                if not issue_details:
                    logger.error(
                        f"Could not fetch details for bug {bug_id} from any TD configuration"
                    )
                    continue

                # 整合数据
                try:
                    report = DataIntegrator.integrate(
                        code_snippets_map[bug_id], issue_details
                    )
                    # 保存到数据库
                    db.add_bug_report(bug_id, report.__dict__)
                    logger.info(f"Successfully processed and saved bug {bug_id}")
                except Exception as e:
                    logger.error(f"Error processing bug {bug_id}: {str(e)}")
                    continue

            except Exception as e:
                logger.error(f"Error handling bug {bug_id}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Fatal error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    main()

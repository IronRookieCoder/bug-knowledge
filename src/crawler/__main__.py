from src.config import config
from src.crawler.gitlab_crawler import GitLabCrawler, CodeSnippet
from src.crawler.td_crawler import TDCrawler
from src.crawler.data_integrator import DataIntegrator, BugReport
from src.storage.database import BugDatabase
from src.utils.log import get_logger
from src.utils.http_client import http_client
from typing import List, Dict, Optional
from collections import defaultdict

logger = get_logger(__name__)


def get_gitlab_snippets(gl_configs):
    """从GitLab获取代码片段，使用并发"""
    code_snippets_map = defaultdict(list)
    for gl_config in gl_configs:
        try:
            gl_crawler = GitLabCrawler(
                gl_config.url,
                gl_config.token,
                gl_config.project_ids,
                config.get("GITLAB_SINCE_DATE"),
                config.get("GITLAB_UNTIL_DATE"),
            )

            commits = gl_crawler.get_commits_for_all_projects()
            if not commits:
                logger.warning(
                    f"No commits found for GitLab config: {gl_config.url}"
                )
                continue

            # 并发处理所有提交
            # 确保传入的是完整的commit字典，而不是键
            filtered_commits = []
            for commit in commits:
                if isinstance(commit, dict) and commit.get("project_id"):
                    filtered_commits.append(commit)
                else:
                    logger.warning(f"跳过无效的commit数据: {commit}")
                    
            snippets = http_client.concurrent_map(
                lambda commit: gl_crawler.parse_commit(
                    commit.get("project_id"), commit
                ),
                filtered_commits,
            )

            # 整合代码片段
            for snippet_list in snippets:
                if snippet_list:
                    for snippet in snippet_list:
                        code_snippets_map[snippet.bug_id].append(snippet)

        except Exception as e:
            logger.error(f"Error with GitLab config {gl_config.url}: {str(e)}")
            continue

    return dict(code_snippets_map)


def process_bugs_batch(
    bug_batch: List[str],
    td_crawler: TDCrawler,
    code_snippets_map: Dict[str, List[CodeSnippet]],
    db: BugDatabase,
) -> None:
    """批量处理一组bug"""
    # 批量获取bug详情
    issue_details_list = td_crawler.get_bug_details_batch(bug_batch)
    
    for issue_details in issue_details_list:
        if not issue_details:
            continue
            
        bug_id = issue_details.bug_id
        try:
            # 检查bug是否已存在
            if db.bug_id_exists(bug_id):
                logger.info(f"Bug {bug_id} already exists in database, skipping...")
                continue

            # 整合数据
            report = DataIntegrator.integrate(
                code_snippets_map[bug_id], issue_details
            )
            # 保存到数据库
            db.add_bug_report(bug_id, report.__dict__)
            logger.info(f"Successfully processed and saved bug {bug_id}")
        except Exception as e:
            logger.error(f"Error processing bug {bug_id}: {str(e)}")


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
            [cfg.url for cfg in td_configs],
            [cfg.headers for cfg in td_configs]
        )

        # 获取所有要处理的bug ID列表
        bug_ids = list(code_snippets_map.keys())
        
        # 使用chunk_concurrent_map批量处理bug
        http_client.chunk_concurrent_map(
            lambda batch: process_bugs_batch(batch, td_crawler, code_snippets_map, db),
            bug_ids,
        )

    except Exception as e:
        logger.error(f"Fatal error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    main()

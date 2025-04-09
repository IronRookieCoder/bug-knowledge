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
            logger.info(f"开始从GitLab配置 {gl_config.url} 获取代码片段")
            gl_crawler = GitLabCrawler(
                gl_config.url,
                gl_config.token,
                gl_config.project_ids,
                config.get("GITLAB_SINCE_DATE"),
                config.get("GITLAB_UNTIL_DATE"),
            )

            commits = gl_crawler.get_commits_for_all_projects()
            # 检查commits是否为列表
            if not isinstance(commits, list):
                logger.warning(
                    f"从GitLab {gl_config.url} 获取的commits数据不是列表: {type(commits)}"
                )
                if isinstance(commits, dict):
                    logger.warning("尝试从字典中提取commits数据")
                    # 尝试从字典中提取列表
                    for key in ["commits", "data", "items", "results"]:
                        if key in commits and isinstance(commits[key], list):
                            commits = commits[key]
                            logger.info(f"从字典的 '{key}' 键中提取到 {len(commits)} 个commits")
                            break
                    else:
                        logger.error(f"无法从字典提取commits数据: {list(commits.keys())}")
                        continue
                else:
                    logger.error(f"无法处理的commits数据类型: {type(commits)}")
                    continue
                    
            if not commits:
                logger.warning(
                    f"No commits found for GitLab config: {gl_config.url}"
                )
                continue

            logger.info(f"从GitLab {gl_config.url} 获取到 {len(commits)} 个commits")
                
            # 并发处理所有提交
            # 确保传入的是完整的commit字典，而不是键
            filtered_commits = []
            for commit in commits:
                # 检查是否为字典类型且包含必要的字段
                if not isinstance(commit, dict):
                    logger.warning(f"跳过非字典类型的commit数据: {type(commit)}")
                    continue
                    
                # 检查是否包含project_id字段
                if not commit.get("project_id"):
                    # 尝试修复：如果没有project_id，但有其他标识项目的字段
                    if "project" in commit and isinstance(commit["project"], dict) and "id" in commit["project"]:
                        commit["project_id"] = str(commit["project"]["id"])
                        logger.debug(f"从commit.project.id提取project_id: {commit['project_id']}")
                    else:
                        # 最后手段：使用配置中的第一个项目ID
                        if gl_config.project_ids:
                            commit["project_id"] = gl_config.project_ids[0]
                            logger.warning(f"为commit {commit.get('id', 'unknown')} 分配默认project_id: {commit['project_id']}")
                        else:
                            logger.warning(f"跳过缺少project_id的commit: {commit.get('id', 'unknown')}")
                            continue
                    
                # 检查commit是否包含id字段
                if not commit.get("id"):
                    logger.warning(f"跳过缺少id的commit, project_id: {commit.get('project_id')}")
                    continue
                    
                # 确保message字段存在，避免后续处理错误
                if "message" not in commit or commit["message"] is None:
                    commit["message"] = ""
                    logger.debug(f"为commit {commit['id']} 添加空message字段")
                    
                # 通过检查，添加到过滤后的列表
                filtered_commits.append(commit)
                    
            logger.info(f"过滤后共有 {len(filtered_commits)}/{len(commits)} 个有效commit")
            
            if not filtered_commits:
                logger.warning(f"筛选后没有有效的commits，跳过GitLab配置 {gl_config.url}")
                continue
                
            try:
                logger.info(f"开始从 {len(filtered_commits)} 个commits中提取代码片段")
                snippets = http_client.concurrent_map(
                    lambda commit: gl_crawler.parse_commit(
                        commit.get("project_id"), commit
                    ),
                    filtered_commits,
                )
                
                logger.info(f"成功从GitLab {gl_config.url} 获取代码片段结果 {len(snippets)} 个")
                
                # 整合代码片段
                snippet_count = 0
                for item in snippets:
                    # 跳过空值
                    if not item:
                        continue
                        
                    # 处理单个CodeSnippet对象的情况
                    if isinstance(item, CodeSnippet):
                        logger.debug(f"直接处理单个CodeSnippet对象: {item.file_path}")
                        code_snippets_map[item.bug_id].append(item)
                        snippet_count += 1
                        continue
                        
                    # 处理列表类型
                    if isinstance(item, list):
                        for snippet in item:
                            if isinstance(snippet, CodeSnippet):
                                code_snippets_map[snippet.bug_id].append(snippet)
                                snippet_count += 1
                            else:
                                logger.warning(f"跳过非CodeSnippet类型的数据: {type(snippet)}")
                        continue
                    
                    # 其他类型，记录警告
                    logger.warning(f"无法处理的snippet数据类型: {type(item)}")
                            
                logger.info(f"从GitLab {gl_config.url} 成功提取 {snippet_count} 个代码片段")
                
            except Exception as e:
                logger.error(f"处理GitLab {gl_config.url} 的commits时发生错误: {str(e)}", exc_info=True)
                continue

        except Exception as e:
            logger.error(f"处理GitLab配置 {gl_config.url} 时发生错误: {str(e)}", exc_info=True)
            continue

    result = dict(code_snippets_map)
    logger.info(f"所有GitLab处理完成，共获取 {len(result)} 个bug的代码片段")
    return result


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

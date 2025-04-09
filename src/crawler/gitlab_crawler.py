import re
import time
from src.utils.log import get_logger
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from src.utils.http_client import http_client

logger = get_logger(__name__)


@dataclass
class CodeSnippet:
    bug_id: str
    file_path: str
    commit_sha: str
    programming_language: str
    code_diff: str
    project_id: str


class GitLabCrawler:
    # 支持的代码文件扩展名
    CODE_EXTENSIONS = {
        # 前端相关
        "js",
        "jsx",
        "ts",
        "tsx",
        "vue",
        "html",
        "css",
        "scss",
        "sass",
        "less",
        # 后端相关
        "java",
        "cpp",
        "cs",
        "py",
        "go",
        "rs",
        "php",
        "rb",
        "swift",
        "kt",
        "m",
        "hs",
        "scala",
        "clj",
        "erl",
        "ex",
        "exs",
        "dart",
        "lua",
        "r",
        "pl",
        # 配置文件
        "json",
        "xml",
        "yaml",
        "yml",
        "toml",
        "ini",
        "conf",
        "properties",
        # 脚本文件
        "sh",
        "bash",
        "bat",
        "cmd",
        "ps1",
        "vbs",
        # 数据库相关
        "md",
        "rst",
        "tex",
        "latex",
        "wiki",
        "adoc",
    }

    # 增强的bug_id匹配模式
    BUG_ID_PATTERNS = [
        # 格式1: 纯数字ID（13位）
        re.compile(r"\b(\d{13})\b"),
        # 格式2: 前缀+数字（支持多种前缀）
        re.compile(r"(?i)(fix|bug|issue|hotfix|task)[-_]?(\d{13})"),
    ]

    def __init__(
        self,
        base_url: str,
        private_token: str,
        project_ids: List[str],
        since_date: str = None,
        until_date: str = None,
    ):
        self.base_url = base_url
        self.headers = {"Private-Token": private_token}
        self.project_ids = project_ids
        self.since_date = since_date
        self.until_date = until_date

    def _extract_bug_id(self, message: str) -> Optional[str]:
        """改进的bug_id提取方法，从title和message中提取"""
        for pattern in self.BUG_ID_PATTERNS:
            match = pattern.search(message)
            if match:
                # 优先返回长格式纯数字ID
                if pattern == self.BUG_ID_PATTERNS[0]:
                    return match.group(1)
                # 处理带前缀的情况
                return match.group(2) if len(match.groups()) > 1 else match.group(1)
        return None

    def get_commits(self, project_id: str) -> List[dict]:
        """获取单个项目的commit列表，使用分页"""
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/commits"
        params = {"per_page": 100, "page": 1}  # 每页获取100个commit

        if self.since_date:
            params["since"] = self.since_date
        if self.until_date:
            params["until"] = self.until_date

        logger.info(
            f"开始获取项目 {project_id} 的提交记录，时间范围: {self.since_date} - {self.until_date}"
        )

        all_commits = []
        while True:
            response = http_client.get(url, headers=self.headers, params=params)
            commits = response.json()
            if not commits:
                break
            all_commits.extend(commits)
            logger.debug(
                f"项目 {project_id} 第 {params['page']} 页获取到 {len(commits)} 个提交"
            )
            params["page"] += 1

        logger.info(f"项目 {project_id} 共获取到 {len(all_commits)} 个提交")

        # 为每个commit添加project_id信息
        for commit in all_commits:
            commit["project_id"] = project_id
        return all_commits

    def get_commits_for_all_projects(self) -> List[dict]:
        """并发获取所有项目的commits"""
        logger.info(f"开始获取所有项目的提交记录，共 {len(self.project_ids)} 个项目")
        all_commits = http_client.concurrent_map(self.get_commits, self.project_ids)
        flattened_commits = [commit for sublist in all_commits if sublist for commit in sublist]
        logger.info(f"所有项目提交获取完成，共获取到 {len(flattened_commits)} 个提交")
        return flattened_commits

    def get_commit_diff(self, project_id: str, commit_sha: str) -> List[dict]:
        """获取commit的详细diff"""
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/commits/{commit_sha}/diff"
        logger.debug(f"获取提交 {commit_sha} 的差异信息")
        response = http_client.get(url, headers=self.headers)
        return response.json()

    def parse_commit(self, project_id: str, commit: Dict) -> List[CodeSnippet]:
        """解析提交信息，获取代码片段"""
        try:
            # 提取bug ID，确保是字符串类型
            bug_id = str(self._extract_bug_id(commit.get("message", "")))
            if not bug_id:
                return []

            commit_sha = str(commit.get("id", ""))
            if not commit_sha:
                return []

            # 获取代码差异
            diff_response = self.get_commit_diff(project_id, commit_sha)
            if not diff_response:
                return []

            code_snippets = []
            for diff in diff_response:
                try:
                    file_path = str(diff.get("new_path", "") or diff.get("old_path", ""))
                    if not file_path:
                        continue

                    # 创建CodeSnippet对象，确保所有字段都是正确的类型
                    snippet = CodeSnippet(
                        bug_id=bug_id,
                        file_path=file_path,
                        commit_sha=commit_sha,
                        programming_language=str(self._get_file_language(file_path)),
                        code_diff=str(diff.get("diff", "")),
                        project_id=str(project_id)
                    )
                    code_snippets.append(snippet)
                except Exception as e:
                    logger.error(f"处理diff时发生错误: {str(e)}, diff: {diff}")
                    continue

            return code_snippets
        except Exception as e:
            logger.error(f"解析commit时发生错误: {str(e)}, commit: {commit}")
            return []

    def _process_diff(
        self, diff: Dict[str, Any], bug_id: str, commit_sha: str, project_id: str
    ) -> Optional[CodeSnippet]:
        """处理单个diff"""
        file_path = diff.get("new_path") or diff.get("old_path")
        if not file_path:
            logger.warning(f"提交 {commit_sha} 的差异中发现无效的文件路径")
            return None

        file_ext = file_path.split(".")[-1].lower()
        if file_ext not in self.CODE_EXTENSIONS:
            logger.debug(f"跳过非代码文件: {file_path}")
            return None

        diff_text = diff.get("diff", "")
        if not diff_text:
            logger.debug(f"文件 {file_path} 没有实际的代码差异")
            return None

        return CodeSnippet(
            bug_id=bug_id,
            file_path=file_path,
            commit_sha=commit_sha,
            programming_language=file_ext,
            code_diff=diff_text,
            project_id=project_id,
        )

import re
import requests
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


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
        'js', 'jsx', 'ts', 'tsx', 'vue', 'html', 'css', 'scss', 'sass', 'less',
        # 后端相关
        'java', 'cpp', 'cs', 'py', 'go', 'rs', 'php', 'rb', 'swift', 'kt', 'm',
        'hs', 'scala', 'clj', 'erl', 'ex', 'exs', 'dart', 'lua', 'r', 'pl',
        # 配置文件
        'json', 'xml', 'yaml', 'yml', 'toml', 'ini', 'conf', 'properties',
        # 脚本文件
        'sh', 'bash', 'bat', 'cmd', 'ps1', 'vbs',
        # 数据库相关
        'sql', 'hql', 'pql',
        # 其他
        'md', 'rst', 'tex', 'latex', 'wiki', 'adoc'
    }

    # 增强的bug_id匹配模式
    BUG_ID_PATTERNS = [
        # 格式1: 纯数字ID（13位）
        re.compile(r'\b(\d{13})\b'),
        # 格式2: 前缀+数字（支持多种前缀）
        re.compile(r'(?i)(fix|bug|issue|hotfix|task)[-_]?(\d{13})'),
    ]

    def __init__(self, base_url: str, private_token: str, project_ids: List[str],
                 since_date: str = None, until_date: str = None):
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
        """获取项目commit列表，使用日期范围，支持分页"""
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/commits"
        params = {
            "per_page": 100,  # 每页获取100个commit
            "page": 1
        }

        if self.since_date:
            params["since"] = self.since_date
        if self.until_date:
            params["until"] = self.until_date

        all_commits = []
        while True:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            commits = response.json()
            if not commits:
                break
            all_commits.extend(commits)
            params["page"] += 1

        # 为每个commit添加project_id信息
        for commit in all_commits:
            commit['project_id'] = project_id
        return all_commits

    def get_commits_for_all_projects(self) -> List[dict]:
        all_commits = []
        for project_id in self.project_ids:
            commits = self.get_commits(project_id)
            all_commits.extend(commits)
        return all_commits

    def get_commit_diff(self, project_id: str, commit_sha: str) -> List[dict]:
        """获取commit的详细diff"""
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/commits/{commit_sha}/diff"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def parse_commit(self, project_id: str, commit: dict) -> List[CodeSnippet]:
        """解析commit生成代码片段"""
        # 从title和message中提取bug_id
        bug_id = self._extract_bug_id(
            commit["title"] + " " + commit.get("message", ""))
        if not bug_id:
            return []

        diffs = self.get_commit_diff(project_id, commit["id"])
        snippets = []

        for diff in diffs:
            # 使用new_path和old_path来判断文件是否为代码文件
            file_path = diff.get("new_path") or diff.get("old_path")
            if not file_path:
                continue

            file_ext = file_path.split('.')[-1].lower()
            if file_ext not in self.CODE_EXTENSIONS:
                continue

            diff_text = diff.get("diff", "")

            snippets.append(CodeSnippet(
                bug_id=bug_id,
                file_path=file_path,
                commit_sha=commit["id"],
                programming_language=file_ext,
                 code_diff=diff_text,
                project_id=project_id,
            ))

        return snippets

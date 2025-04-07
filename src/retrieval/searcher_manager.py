from typing import Optional
from src.retrieval.searcher import BugSearcher
from src.utils.log import get_logger

logger = get_logger(__name__)

_bug_searcher: Optional[BugSearcher] = None

def get_bug_searcher() -> BugSearcher:
    """获取全局BugSearcher实例"""
    global _bug_searcher
    if _bug_searcher is None:
        _bug_searcher = BugSearcher()
    return _bug_searcher

def set_bug_searcher(searcher: BugSearcher) -> None:
    """设置全局BugSearcher实例"""
    global _bug_searcher
    _bug_searcher = searcher
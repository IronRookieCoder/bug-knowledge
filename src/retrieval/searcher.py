from typing import List, Dict, Optional
from src.vectorization.vectorizers import HybridVectorizer
from src.storage.vector_store import VectorStore
from src.models.bug_models import BugReport

class BugSearcher:
    def __init__(self):
        self.vectorizer = HybridVectorizer()
        self.vector_store = VectorStore()
    
    def add_bug_report(self, bug_report: BugReport):
        """添加新的bug报告到知识库"""
        vectors = self.vectorizer.vectorize_bug_report(bug_report)
        self.vector_store.add_bug_report(bug_report, vectors)
    
    def search(self, 
              query_text: str = "",
              code_snippet: str = "",
              error_log: str = "",
              env_info: str = "",
              n_results: int = 5,
              weights: Optional[Dict[str, float]] = None) -> List[Dict]:
        """
        搜索相似的bug报告
        
        Args:
            query_text: 问题描述
            code_snippet: 代码片段
            error_log: 错误日志
            env_info: 环境信息
            n_results: 返回结果数量
            weights: 各个向量的权重
        
        Returns:
            List[Dict]: 相似bug报告列表
        """
        # 向量化查询
        query_vectors = {
            "question_vector": self.vectorizer.question_vectorizer.vectorize(query_text),
            "code_vector": self.vectorizer.code_vectorizer.vectorize(code_snippet),
            "log_vector": self.vectorizer.log_vectorizer.vectorize(error_log),
            "env_vector": self.vectorizer.env_vectorizer.vectorize(env_info)
        }
        
        # 搜索
        return self.vector_store.search(
            query_vectors=query_vectors,
            n_results=n_results,
            weights=weights
        ) 
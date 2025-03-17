from typing import List, Dict, Optional
from src.vectorization.vectorizers import HybridVectorizer
from src.storage.vector_store import VectorStore
from src.models.bug_models import BugReport
import logging
import traceback

logger = logging.getLogger(__name__)

class BugSearcher:
    def __init__(self):
        try:
            logger.info("初始化 BugSearcher...")
            self.vectorizer = HybridVectorizer()
            self.vector_store = VectorStore()
            logger.info("BugSearcher 初始化成功")
        except Exception as e:
            logger.error(f"BugSearcher 初始化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"BugSearcher 初始化失败: {str(e)}")
    
    def add_bug_report(self, bug_report: BugReport):
        """添加新的bug报告到知识库"""
        try:
            logger.info(f"开始添加 Bug 报告: {bug_report.id}")
            vectors = self.vectorizer.vectorize_bug_report(bug_report)
            logger.info("向量化完成")
            self.vector_store.add_bug_report(bug_report, vectors)
            logger.info(f"Bug 报告添加成功: {bug_report.id}")
        except Exception as e:
            logger.error(f"添加 Bug 报告失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"添加 Bug 报告失败: {str(e)}")
    
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
        try:
            logger.info("开始搜索...")
            logger.info(f"查询参数: query_text={query_text[:50]}..., code_snippet={code_snippet[:50]}..., error_log={error_log[:50]}..., env_info={env_info[:50]}...")
            
            # 向量化查询
            logger.info("开始向量化查询...")
            query_vectors = {
                "question_vector": self.vectorizer.question_vectorizer.vectorize(query_text),
                "code_vector": self.vectorizer.code_vectorizer.vectorize(code_snippet),
                "log_vector": self.vectorizer.log_vectorizer.vectorize(error_log),
                "env_vector": self.vectorizer.env_vectorizer.vectorize(env_info)
            }
            logger.info("查询向量化完成")
            
            # 搜索
            logger.info("开始向量搜索...")
            results = self.vector_store.search(
                query_vectors=query_vectors,
                n_results=n_results,
                weights=weights
            )
            logger.info(f"搜索完成，找到 {len(results)} 条结果")
            return results
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"搜索失败: {str(e)}") 
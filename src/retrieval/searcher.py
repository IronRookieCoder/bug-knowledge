from typing import List, Dict, Optional
import logging
from src.models.bug_models import BugReport
from src.storage.vector_store import VectorStore
from src.vectorization.vectorizers import HybridVectorizer
import os
import traceback

# 设置日志
logger = logging.getLogger(__name__)

# 禁用在线模型下载
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

class BugSearcher:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()
        self.vectorizer = HybridVectorizer()
        
        # 查询类型权重配置
        self.query_type_weights = {
            "summary_only": {
                "summary": 0.5,           # 摘要权重
                "code": 0.1,              # 代码权重
                "test_steps": 0.1,        # 测试步骤权重
                "expected_result": 0.1,   # 预期结果权重
                "actual_result": 0.1,     # 实际结果权重
                "log_info": 0.1           # 日志权重
            },
            "code_only": {
                "code": 0.4,              # 代码权重
                "summary": 0.2,           # 摘要权重
                "test_steps": 0.1,        # 测试步骤权重
                "expected_result": 0.1,   # 预期结果权重
                "actual_result": 0.1,     # 实际结果权重
                "log_info": 0.1           # 日志权重
            },
            "test_only": {
                "test_steps": 0.4,        # 测试步骤权重
                "expected_result": 0.2,   # 预期结果权重
                "actual_result": 0.2,     # 实际结果权重
                "summary": 0.1,           # 摘要权重
                "code": 0.1               # 代码权重
            },
            "log_only": {
                "log_info": 0.4,          # 日志权重
                "code": 0.2,              # 代码权重
                "summary": 0.1,           # 摘要权重
                "test_steps": 0.1,        # 测试步骤权重
                "expected_result": 0.1,   # 预期结果权重
                "actual_result": 0.1      # 实际结果权重
            },
            "environment_only": {
                "environment": 0.5,       # 环境权重
                "summary": 0.1,           # 摘要权重
                "code": 0.1,              # 代码权重
                "test_steps": 0.1,        # 测试步骤权重
                "expected_result": 0.1,   # 预期结果权重
                "actual_result": 0.1      # 实际结果权重
            },
            "mixed": {
                "summary": 0.2,           # 摘要权重
                "code": 0.2,              # 代码权重
                "test_steps": 0.2,        # 测试步骤权重
                "expected_result": 0.1,   # 预期结果权重
                "actual_result": 0.1,     # 实际结果权重
                "log_info": 0.1,          # 日志权重
                "environment": 0.1        # 环境权重
            }
        }
    
    def add_bug_report(self, bug_report: BugReport):
        """添加BUG报告"""
        try:
            # 生成向量
            vectors = self.vectorizer.vectorize_bug_report(bug_report)
            
            # 保存向量和BUG报告
            self.vector_store.add_bug_report(bug_report, vectors)
            
            return True
            
        except Exception as e:
            logger.error(f"添加BUG报告失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False
    
    def _determine_query_type(self, query_text: Optional[str] = None,
                          code: Optional[str] = None,
                          test_steps: Optional[str] = None,
                          expected_result: Optional[str] = None,
                          actual_result: Optional[str] = None,
                          log_info: Optional[str] = None,
                          environment: Optional[str] = None) -> str:
        """确定查询类型"""
        if code and not (query_text or test_steps or expected_result or actual_result or log_info or environment):
            return "code_only"
        elif (test_steps or expected_result or actual_result) and not (query_text or code or log_info or environment):
            return "test_only"
        elif log_info and not (query_text or code or test_steps or expected_result or actual_result or environment):
            return "log_only"
        elif environment and not (query_text or code or test_steps or expected_result or actual_result or log_info):
            return "environment_only"
        elif query_text and not (code or test_steps or expected_result or actual_result or log_info or environment):
            return "summary_only"
        else:
            return "mixed"

    def search(self, query_text: Optional[str] = None,
             code: Optional[str] = None,
             test_steps: Optional[str] = None,
             expected_result: Optional[str] = None,
             actual_result: Optional[str] = None,
             log_info: Optional[str] = None,
             environment: Optional[str] = None,
             n_results: int = 5) -> List[Dict]:
        """搜索相似BUG报告
        
        Args:
            query_text: 问题描述
            code: 代码片段
            test_steps: 重现缺陷的测试步骤
            expected_result: 预期结果
            actual_result: 实际结果
            log_info: 日志信息
            environment: 缺陷发生的环境信息
            n_results: 返回结果数量
            
        Returns:
            List[Dict]: 相似BUG报告列表
        """
        try:
            # 确定查询类型
            query_type = self._determine_query_type(
                query_text, code, test_steps, expected_result, 
                actual_result, log_info, environment
            )
            
            # 获取权重配置
            weights = self.query_type_weights[query_type]
            
            # 生成查询向量
            query_vectors = {}
            if query_text:
                query_vectors["summary_vector"] = self.vectorizer.summary_vectorizer.vectorize(query_text)
            if code:
                query_vectors["code_vector"] = self.vectorizer.code_vectorizer.vectorize(code)
            if test_steps or expected_result or actual_result:
                test_info = {
                    "test_steps": test_steps or "",
                    "expected_result": expected_result or "",
                    "actual_result": actual_result or ""
                }
                query_vectors["test_steps_vector"] = self.vectorizer.test_vectorizer.vectorize(test_info)
                query_vectors["expected_result_vector"] = self.vectorizer.test_vectorizer.vectorize(test_info)
                query_vectors["actual_result_vector"] = self.vectorizer.test_vectorizer.vectorize(test_info)
            if log_info:
                query_vectors["log_info_vector"] = self.vectorizer.log_vectorizer.vectorize(log_info)
            if environment:
                query_vectors["environment_vector"] = self.vectorizer.environment_vectorizer.vectorize(environment)
            
            # 执行向量检索
            results = self.vector_store.search(query_vectors, n_results=n_results, weights=weights)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return []
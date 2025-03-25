from typing import List, Dict
import traceback
from log import logger

class BugSearcher:
    def search(
            self,
            description: str = "",
            steps_to_reproduce: str = "",
            expected_behavior: str = "",
            actual_behavior: str = "",
            code: str = "",
            error_logs: str = "",
            weights: Dict[str, float] = None,
            n_results: int = 5
        ) -> List[Dict]:
            """搜索相似的BUG报告
            
            Args:
                description: 问题描述
                steps_to_reproduce: 重现步骤
                expected_behavior: 期望结果
                actual_behavior: 实际结果
                code: 相关代码
                error_logs: 错误日志
                weights: 各个字段的权重
                n_results: 返回结果数量
                
            Returns:
                List[Dict]: 搜索结果列表
            """
            try:
                # 生成查询向量
                vectors = {}
                
                if description:
                    vectors["description_vector"] = self.model.encode(description)
                
                if steps_to_reproduce:
                    vectors["steps_vector"] = self.model.encode(steps_to_reproduce)
                
                if expected_behavior:
                    vectors["expected_vector"] = self.model.encode(expected_behavior)
                
                if actual_behavior:
                    vectors["actual_vector"] = self.model.encode(actual_behavior)
                
                if code:
                    vectors["code_vector"] = self.model.encode(code)
                
                if error_logs:
                    vectors["log_vector"] = self.model.encode(error_logs)
                    
                # 如果没有提供任何搜索内容，返回空列表
                if not vectors:
                    return []
                
                # 搜索相似的BUG报告
                results = self.vector_store.search(
                    query_vectors=vectors,
                    weights=weights,
                    n_results=n_results
                )
                
                return results
                
            except Exception as e:
                logger.error(f"搜索失败: {str(e)}")
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                raise RuntimeError(f"搜索失败: {str(e)}") 
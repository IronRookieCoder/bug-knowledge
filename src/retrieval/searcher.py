from typing import List, Dict, Optional
import logging
from src.models.bug_models import BugReport
from src.storage.vector_store import VectorStore
from src.features.code_features import CodeFeatureExtractor
from sentence_transformers import SentenceTransformer
from sentence_transformers.models import Transformer, Pooling
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
        self.code_feature_extractor = CodeFeatureExtractor()
        
        try:
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            original_dir = os.getcwd()
            os.chdir(current_dir)
            
            model_name = "all-MiniLM-L6-v2"
            model_path = os.path.join("lm-models", model_name)
            if not os.path.exists(model_path):
                raise RuntimeError(f"模型目录不存在: {os.path.abspath(model_path)}")
            
            modules_path = os.path.join(model_path, "modules.json")
            if not os.path.exists(modules_path):
                raise RuntimeError(f"模型文件不完整，modules.json 不存在: {os.path.abspath(modules_path)}")
            
            logger.info(f"正在加载本地模型: {os.path.abspath(model_path)}")
            
            try:
                # 创建 Transformer 和 Pooling 模块
                word_embedding_model = Transformer(model_path)
                pooling_model = Pooling(word_embedding_model.get_word_embedding_dimension())
                
                # 创建 SentenceTransformer 实例
                self.text_encoder = SentenceTransformer(modules=[word_embedding_model, pooling_model])
                
                logger.info("本地模型加载成功")
            except Exception as e:
                logger.error(f"模型加载失败: {str(e)}")
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                raise RuntimeError(f"模型加载失败: {str(e)}")
            
        except Exception as e:
            # 确保在发生错误时也恢复原始工作目录
            if 'original_dir' in locals():
                os.chdir(original_dir)
            logger.error(f"初始化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"初始化失败: {str(e)}")
        
        # 恢复原始工作目录
        os.chdir(original_dir)
        
        # 查询类型权重配置
        self.query_type_weights = {
            "text_only": {
                "question": 0.65,  # 降低纯文本权重，为代码相关性留空间
                "code": 0.25,     # 增加代码权重，因为问题描述可能暗示代码问题
                "log": 0.05,
                "env": 0.05
            },
            "code_only": {
                "question": 0.25,  # 增加问题描述权重，因为相似代码可能有相似的问题描述
                "code": 0.65,     # 保持代码主导但略微降低
                "log": 0.05,
                "env": 0.05
            },
            "mixed": {
                "question": 0.4,   # 稍微提高问题描述权重
                "code": 0.35,      # 保持较高的代码权重
                "log": 0.15,
                "env": 0.1
            },
            "log_only": {
                "question": 0.15,  # 增加问题描述权重，因为日志通常与问题描述相关
                "code": 0.15,      # 增加代码权重，因为日志通常指向代码问题
                "log": 0.6,        # 仍然以日志为主
                "env": 0.1
            }
        }
        
        # 相似度阈值配置
        self.similarity_thresholds = {
            "text": {
                "title_boost": 1.2,      # 标题匹配时的提升因子
                "keyword_weight": 0.3,    # 关键词匹配的权重
                "semantic_weight": 0.7    # 语义相似度的权重
            },
            "code": {
                "structure_weight": 0.4,  # 代码结构相似度权重
                "semantic_weight": 0.6    # 代码语义相似度权重
            },
            "log": {
                "exact_match_boost": 1.3, # 精确匹配时的提升因子
                "pattern_weight": 0.5,    # 错误模式匹配的权重
                "context_weight": 0.5     # 上下文相似度的权重
            }
        }
    
    def add_bug_report(self, bug_report: BugReport):
        """添加新的bug报告"""
        try:
            # 生成文本向量
            question_text = f"{bug_report.title} {bug_report.description}"
            question_vector = self.text_encoder.encode(question_text)
            
            # 生成代码向量
            code_vector = self.text_encoder.encode(bug_report.code_context.code)
            
            # 生成日志向量
            log_vector = self.text_encoder.encode(bug_report.error_logs)
            
            # 生成环境信息向量
            env_text = f"{bug_report.environment.runtime_env} {bug_report.environment.os_info} {bug_report.environment.network_env}"
            env_vector = self.text_encoder.encode(env_text)
            
            # 提取代码特征
            code_features = self.code_feature_extractor.extract_features(bug_report.code_context.code)
            
            # 添加bug报告
            self.vector_store.add_bug_report(
                bug_report,
                {
                    "question_vector": question_vector,
                    "code_vector": code_vector,
                    "log_vector": log_vector,
                    "env_vector": env_vector
                }
            )
            
            logger.info(f"成功添加bug报告: {bug_report.id}")
        except Exception as e:
            logger.error(f"添加bug报告失败: {str(e)}")
            raise
    
    def search(self, query_text: str = "", code_snippet: str = "", 
               error_log: str = "", env_info: str = "", n_results: int = 5) -> List[Dict]:
        """搜索相似的bug报告"""
        try:
            # 确定查询类型
            query_type = self._determine_query_type(query_text, code_snippet, error_log, env_info)
            
            # 生成查询向量
            query_vectors = self._generate_query_vectors(
                query_text, code_snippet, error_log, env_info
            )
            
            # 获取查询类型对应的权重
            weights = self.query_type_weights[query_type]
            
            # 根据查询类型调整搜索策略
            if query_type == "text_only":
                # 增加初始结果数，以便后续过滤
                initial_results = self.vector_store.search(
                    query_vectors=query_vectors,
                    n_results=min(n_results * 3, 200),  # 扩大初始搜索范围
                    weights=weights
                )
                # 对结果进行重新排序，考虑标题匹配度
                results = self._rerank_text_results(initial_results, query_text, n_results)
            elif query_type == "code_only":
                # 使用代码特征进行搜索
                results = self.vector_store.search(
                    query_vectors=query_vectors,
                    n_results=n_results,
                    weights=weights
                )
                # 对结果进行重新排序，考虑代码结构相似度
                results = self._rerank_code_results(results, code_snippet)
            elif query_type == "log_only":
                # 使用日志特征进行搜索
                results = self.vector_store.search(
                    query_vectors=query_vectors,
                    n_results=n_results,
                    weights=weights
                )
                # 对结果进行重新排序，考虑错误模式匹配
                results = self._rerank_log_results(results, error_log)
            else:
                # 混合搜索
                results = self.vector_store.search(
                    query_vectors=query_vectors,
                    n_results=n_results,
                    weights=weights
                )
            
            logger.info(f"搜索完成，找到 {len(results)} 条结果")
            return results[:n_results]  # 确保返回指定数量的结果
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise
    
    def _determine_query_type(self, query_text: str, code_snippet: str, 
                            error_log: str, env_info: str) -> str:
        """确定查询类型"""
        has_text = bool(query_text.strip())
        has_code = bool(code_snippet.strip())
        has_log = bool(error_log.strip())
        has_env = bool(env_info.strip())
        
        if has_text and not (has_code or has_log or has_env):
            return "text_only"
        elif has_code and not (has_text or has_log or has_env):
            return "code_only"
        elif has_log and not (has_text or has_code or has_env):
            return "log_only"
        else:
            return "mixed"
    
    def _generate_query_vectors(self, query_text: str, code_snippet: str, 
                              error_log: str, env_info: str) -> Dict[str, List[float]]:
        """生成查询向量"""
        # 生成文本向量
        question_vector = self.text_encoder.encode(query_text) if query_text else self.text_encoder.encode("")
        
        # 生成代码向量
        code_vector = self.text_encoder.encode(code_snippet) if code_snippet else self.text_encoder.encode("")
        
        # 生成日志向量
        log_vector = self.text_encoder.encode(error_log) if error_log else self.text_encoder.encode("")
        
        # 生成环境信息向量
        env_vector = self.text_encoder.encode(env_info) if env_info else self.text_encoder.encode("")
        
        # 返回向量和原始查询文本
        return {
            "question_vector": question_vector,
            "code_vector": code_vector,
            "log_vector": log_vector,
            "env_vector": env_vector,
            "query_text": query_text  # 添加原始查询文本
        }
    
    def _rerank_text_results(self, results: List[Dict], query_text: str, n_results: int) -> List[Dict]:
        """重新排序文本搜索结果"""
        for result in results:
            # 计算标题匹配得分
            title_similarity = self._calculate_text_similarity(
                query_text, 
                result["title"],
                self.similarity_thresholds["text"]["title_boost"]
            )
            # 更新相似度得分
            result["distance"] = result["distance"] * 0.7 + (1 - title_similarity) * 0.3
        
        # 按更新后的得分重新排序
        return sorted(results, key=lambda x: x["distance"])[:n_results]
    
    def _rerank_code_results(self, results: List[Dict], code_snippet: str) -> List[Dict]:
        """重新排序代码搜索结果"""
        for result in results:
            # 计算代码结构相似度
            structure_similarity = self._calculate_code_structure_similarity(
                code_snippet,
                result["code_context"]["code"]
            )
            # 更新相似度得分
            result["distance"] = result["distance"] * 0.6 + (1 - structure_similarity) * 0.4
        
        return sorted(results, key=lambda x: x["distance"])
    
    def _rerank_log_results(self, results: List[Dict], error_log: str) -> List[Dict]:
        """重新排序日志搜索结果"""
        for result in results:
            # 计算错误模式匹配度
            pattern_similarity = self._calculate_log_pattern_similarity(
                error_log,
                result["error_logs"]
            )
            # 更新相似度得分
            result["distance"] = result["distance"] * 0.5 + (1 - pattern_similarity) * 0.5
        
        return sorted(results, key=lambda x: x["distance"])
    
    def _calculate_text_similarity(self, query: str, text: str, boost_factor: float = 1.0) -> float:
        """计算文本相似度"""
        # 1. 关键词匹配
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        keyword_similarity = len(query_words & text_words) / max(len(query_words), 1)
        
        # 2. 语义相似度
        semantic_similarity = 1 - self.text_encoder.encode(query).dot(self.text_encoder.encode(text))
        
        # 3. 组合得分
        similarity = (
            self.similarity_thresholds["text"]["keyword_weight"] * keyword_similarity +
            self.similarity_thresholds["text"]["semantic_weight"] * semantic_similarity
        ) * boost_factor
        
        return min(1.0, similarity)
    
    def _calculate_code_structure_similarity(self, query_code: str, target_code: str) -> float:
        """计算代码结构相似度"""
        try:
            # 提取代码特征
            query_features = self.code_feature_extractor.extract_features(query_code)
            target_features = self.code_feature_extractor.extract_features(target_code)
            
            # 计算结构相似度
            structure_similarity = self.code_feature_extractor.calculate_similarity(
                query_features,
                target_features
            )
            
            return structure_similarity
        except Exception as e:
            logger.warning(f"计算代码结构相似度失败: {str(e)}")
            return 0.0
    
    def _calculate_log_pattern_similarity(self, query_log: str, target_log: str) -> float:
        """计算日志模式相似度"""
        try:
            # 1. 提取错误类型和关键信息
            query_patterns = self._extract_log_patterns(query_log)
            target_patterns = self._extract_log_patterns(target_log)
            
            # 2. 计算模式匹配度
            pattern_matches = len(set(query_patterns) & set(target_patterns))
            total_patterns = max(len(query_patterns), 1)
            
            return pattern_matches / total_patterns
        except Exception as e:
            logger.warning(f"计算日志模式相似度失败: {str(e)}")
            return 0.0
    
    def _extract_log_patterns(self, log: str) -> List[str]:
        """提取日志中的错误模式"""
        patterns = []
        lines = log.split('\n')
        
        for line in lines:
            # 提取错误类型
            if 'error' in line.lower() or 'exception' in line.lower():
                patterns.append(line.strip())
            # 提取关键信息（如行号、文件名等）
            elif ':' in line and ('at' in line.lower() or 'in' in line.lower()):
                patterns.append(line.strip())
        
        return patterns
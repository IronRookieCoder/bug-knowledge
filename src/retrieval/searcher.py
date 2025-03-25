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
        self.vector_store = vector_store or VectorStore(read_only=False)
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
                "title": 0.3,        # 标题权重
                "description": 0.2,   # 问题描述权重
                "steps": 0.15,       # 重现步骤权重
                "expected": 0.1,      # 期望结果权重
                "actual": 0.15,       # 实际结果权重
                "code": 0.1          # 保留少量代码相关性
            },
            "code_only": {
                "code": 0.7,         # 提高代码权重
                "error": 0.2,        # 关联错误信息
                "description": 0.1    # 保留少量问题描述相关性
            },
            "log_only": {
                "error": 0.6,        # 错误日志主导
                "code": 0.25,        # 关联代码上下文
                "description": 0.15   # 关联问题描述
            },
            "mixed": {
                "code": 0.35,        # 代码权重
                "error": 0.25,       # 错误日志权重
                "description": 0.15,  # 问题描述
                "steps": 0.1,        # 重现步骤
                "expected": 0.05,    # 期望结果
                "actual": 0.1        # 实际结果
            }
        }
        
        # 相似度阈值配置
        self.similarity_thresholds = {
            "text": {
                "title_boost": 1.3,      # 提高标题匹配权重
                "keyword_weight": 0.4,    # 提高关键词匹配权重
                "semantic_weight": 0.6    # 降低语义权重
            },
            "code": {
                "structure_weight": 0.5,  # 提高结构相似度权重
                "semantic_weight": 0.5,   # 降低语义权重
                "language_support": {     # 支持的编程语言
                    "javascript": {
                        "extensions": [".js", ".jsx", ".ts", ".tsx"],
                        "weight": 1.0
                    },
                    "typescript": {
                        "extensions": [".ts", ".tsx"],
                        "weight": 1.2     # TypeScript 代码给予更高权重
                    }
                }
            },
            "log": {
                "exact_match_boost": 1.4, # 提高精确匹配权重
                "pattern_weight": 0.6,    # 提高模式匹配权重
                "context_weight": 0.4     # 降低上下文权重
            }
        }
    
    def add_bug_report(self, bug_report: BugReport):
        """添加BUG报告"""
        try:
            # 生成向量
            vectors = {}
            
            # 文本向量
            description_vector = self.text_encoder.encode(bug_report.description)
            vectors["description_vector"] = description_vector
            
            # 重现步骤向量
            steps_vector = self.text_encoder.encode(" ".join(bug_report.steps_to_reproduce))
            vectors["steps_vector"] = steps_vector
            
            # 期望结果向量
            expected_vector = self.text_encoder.encode(bug_report.expected_behavior)
            vectors["expected_vector"] = expected_vector
            
            # 实际结果向量
            actual_vector = self.text_encoder.encode(bug_report.actual_behavior)
            vectors["actual_vector"] = actual_vector
            
            # 代码向量
            if bug_report.code_context and bug_report.code_context.code:
                code = bug_report.code_context.code
                code_vector = self.text_encoder.encode(code)
                vectors["code_vector"] = code_vector
            
            # 错误日志向量
            if bug_report.error_logs:
                log_vector = self.text_encoder.encode(bug_report.error_logs)
                vectors["log_vector"] = log_vector
            
            # 环境信息向量
            env_text = f"{bug_report.environment.os_info} {bug_report.environment.runtime_env}"
            if bug_report.environment.network_env:
                env_text += f" {bug_report.environment.network_env}"
            env_vector = self.text_encoder.encode(env_text)
            vectors["env_vector"] = env_vector
            
            # 保存向量和BUG报告
            self.vector_store.add_bug_report(bug_report, vectors)
            
            return True
            
        except Exception as e:
            logger.error(f"添加BUG报告失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False
    
    def _calculate_dynamic_weights(self, query_text: str, code_snippet: str, 
                                 error_log: str, env_info: str) -> Dict[str, float]:
        """计算动态权重
        
        Args:
            query_text: 查询文本
            code_snippet: 代码片段
            error_log: 错误日志
            env_info: 环境信息
            
        Returns:
            Dict[str, float]: 计算得到的权重字典
        """
        # 检查每个字段是否有内容
        has_content = {
            "description": bool(query_text.strip()),
            "code": bool(code_snippet.strip()),
            "log": bool(error_log.strip()),
            "env": bool(env_info.strip())
        }
        
        # 根据输入内容的类型动态调整权重
        weights = {}
        
        # 如果只有代码
        if has_content["code"] and not any(v for k, v in has_content.items() if k != "code"):
            weights = {
                "description": 0.0,
                "steps": 0.0,
                "expected": 0.0,
                "actual": 0.0,
                "code": 0.8,
                "log": 0.2,
                "env": 0.0
            }
            logger.info("使用代码特化权重")
        
        # 如果只有错误日志
        elif has_content["log"] and not any(v for k, v in has_content.items() if k != "log"):
            weights = {
                "description": 0.1,
                "steps": 0.0,
                "expected": 0.0,
                "actual": 0.0,
                "code": 0.3,
                "log": 0.6,
                "env": 0.0
            }
            logger.info("使用错误日志特化权重")
        
        # 如果只有问题描述相关字段
        elif has_content["description"] and not (has_content["code"] or has_content["log"]):
            weights = {
                "description": 0.4,
                "steps": 0.2,
                "expected": 0.2,
                "actual": 0.2,
                "code": 0.0,
                "log": 0.0,
                "env": 0.0
            }
            logger.info("使用问题描述特化权重")
        
        # 如果同时包含代码和错误日志
        elif has_content["code"] and has_content["log"]:
            weights = {
                "description": 0.1,
                "steps": 0.1,
                "expected": 0.05,
                "actual": 0.05,
                "code": 0.4,
                "log": 0.3,
                "env": 0.0
            }
            logger.info("使用代码+错误日志特化权重")
        
        # 如果包含代码和问题描述
        elif has_content["code"] and has_content["description"]:
            weights = {
                "description": 0.2,
                "steps": 0.15,
                "expected": 0.1,
                "actual": 0.15,
                "code": 0.4,
                "log": 0.0,
                "env": 0.0
            }
            logger.info("使用代码+问题描述特化权重")
        
        # 如果包含错误日志和问题描述
        elif has_content["log"] and has_content["description"]:
            weights = {
                "description": 0.2,
                "steps": 0.15,
                "expected": 0.1,
                "actual": 0.15,
                "code": 0.0,
                "log": 0.4,
                "env": 0.0
            }
            logger.info("使用错误日志+问题描述特化权重")
        
        # 默认权重（混合场景）
        else:
            weights = {
                "description": 0.2,
                "steps": 0.15,
                "expected": 0.1,
                "actual": 0.15,
                "code": 0.2,
                "log": 0.2,
                "env": 0.0
            }
            logger.info("使用默认混合权重")
        
        # 重新归一化权重，确保总和为1
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}
        
        logger.info(f"最终搜索权重: {weights}")
        return weights

    def search(
        self,
        query_text: str = "",
        code_snippet: str = "",
        error_log: str = "",
        env_info: str = "",
        weights: Dict[str, float] = None,
        n_results: int = 5
    ) -> List[Dict]:
        """搜索相似的BUG报告
        
        Args:
            query_text: 查询文本（包含问题描述、重现步骤、期望结果、实际结果）
            code_snippet: 代码片段
            error_log: 错误日志
            env_info: 环境信息
            weights: 各个字段的权重（如果为None，则使用动态权重）
            n_results: 返回结果数量
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            # 如果没有提供权重，使用动态权重计算
            if weights is None:
                weights = self._calculate_dynamic_weights(query_text, code_snippet, error_log, env_info)
            
            # 生成查询向量
            vectors = self._generate_query_vectors(query_text, code_snippet, error_log, env_info)
            
            # 如果没有生成任何向量，返回空列表
            if not vectors:
                logger.warning("没有生成任何查询向量")
                return []
            
            # 搜索相似的BUG报告，请求更多结果
            search_results = self.vector_store.search(
                query_vectors=vectors,
                weights=weights,
                n_results=n_results * 3  # 请求更多结果
            )
            
            logger.info(f"搜索完成: 找到 {len(search_results)} 个结果")
            
            # 记录详细的搜索结果信息
            if search_results:
                result_ids = [r["id"] for r in search_results[:min(10, len(search_results))]]
                logger.info(f"搜索结果ID (前10个): {result_ids}")
                # 记录每个结果的相似度得分
                for i, result in enumerate(search_results[:min(5, len(search_results))], 1):
                    logger.info(f"结果 #{i}: ID={result['id']}, 距离={result['distance']}")
            
            # 返回用户请求的结果数量
            return search_results[:n_results]
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"搜索失败: {str(e)}")
    
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
        vectors = {}
        
        # 生成文本向量
        if query_text:
            # 尝试从查询文本中提取不同部分
            parts = self._split_query_text(query_text)
            vectors.update({
                "description_vector": self.text_encoder.encode(parts.get("description", "")),
                "steps_vector": self.text_encoder.encode(parts.get("steps", "")),
                "expected_vector": self.text_encoder.encode(parts.get("expected", "")),
                "actual_vector": self.text_encoder.encode(parts.get("actual", ""))
            })
        
        # 生成代码向量
        if code_snippet:
            # 检测代码语言
            language = self._detect_language_from_content(code_snippet)
            vectors["code_vector"] = self.text_encoder.encode(code_snippet)
            vectors["language"] = language
        
        # 生成错误日志向量
        if error_log:
            vectors["log_vector"] = self.text_encoder.encode(error_log)
        
        # 生成环境信息向量
        if env_info:
            vectors["env_vector"] = self.text_encoder.encode(env_info)
        
        return vectors
    
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
                result["code_context"]["code"],
                result["language"],
                self._detect_language(result["code_context"]["file_path"])
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
    
    def _calculate_code_structure_similarity(self, query_code: str, target_code: str, 
                                          query_language: str = "unknown", 
                                          target_language: str = "unknown") -> float:
        """计算代码结构相似度"""
        try:
            # 提取代码特征
            query_features = self.code_feature_extractor.extract_features(query_code)
            target_features = self.code_feature_extractor.extract_features(target_code)
            
            # 计算基础结构相似度
            structure_similarity = self.code_feature_extractor.calculate_similarity(
                query_features,
                target_features
            )
            
            # 应用语言特定的权重
            if query_language in self.similarity_thresholds["code"]["language_support"] and \
               query_language == target_language:
                language_weight = self.similarity_thresholds["code"]["language_support"][query_language]["weight"]
                structure_similarity *= language_weight
            
            return min(1.0, structure_similarity)
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
    
    def _detect_language(self, file_path: str) -> str:
        """检测代码语言"""
        if not file_path:
            return "unknown"
            
        ext = os.path.splitext(file_path)[1].lower()
        
        # JavaScript/TypeScript 文件识别
        if ext in [".ts", ".tsx"]:
            return "typescript"
        elif ext in [".js", ".jsx"]:
            return "javascript"
        
        return "unknown"
    
    def _detect_language_from_content(self, code: str) -> str:
        """从代码内容推测语言"""
        # 简单的特征检测
        ts_features = ["interface", "type", "enum", "namespace", ": string", ": number", ": boolean"]
        js_features = ["const", "let", "var", "function", "=>", "async", "await"]
        
        ts_score = sum(1 for feature in ts_features if feature in code.lower())
        js_score = sum(1 for feature in js_features if feature in code.lower())
        
        if ts_score > js_score:
            return "typescript"
        elif js_score > 0:
            return "javascript"
        
        return "unknown"
    
    def _split_query_text(self, query_text: str) -> Dict[str, str]:
        """将查询文本分割为不同部分"""
        parts = {
            "description": "",
            "steps": "",
            "expected": "",
            "actual": ""
        }
        
        # 如果查询文本为空，直接返回空值字典
        if not query_text or not query_text.strip():
            return parts
            
        # 简单的启发式分割
        lines = query_text.split("\n")
        
        current_section = "description"
        for line in lines:
            line_lower = line.strip().lower()
            
            # 根据关键词识别不同部分
            if "步骤" in line_lower or "重现" in line_lower:
                current_section = "steps"
                continue
            elif "期望" in line_lower or "预期" in line_lower:
                current_section = "expected"
                continue
            elif "实际" in line_lower or "结果" in line_lower:
                current_section = "actual"
                continue
                
            # 添加到当前部分
            if line.strip():
                parts[current_section] = parts[current_section] + " " + line.strip()
        
        return {k: v.strip() for k, v in parts.items()}
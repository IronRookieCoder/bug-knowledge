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
                "question": 0.8,
                "code": 0.1,
                "log": 0.05,
                "env": 0.05
            },
            "code_only": {
                "question": 0.1,
                "code": 0.8,
                "log": 0.05,
                "env": 0.05
            },
            "mixed": {
                "question": 0.4,
                "code": 0.4,
                "log": 0.1,
                "env": 0.1
            },
            "log_only": {
                "question": 0.1,
                "code": 0.1,
                "log": 0.7,
                "env": 0.1
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
            
            # 执行搜索
            results = self.vector_store.search(
                query_vectors=query_vectors,
                n_results=n_results,
                weights=weights
            )
            
            logger.info(f"搜索完成，找到 {len(results)} 条结果")
            return results
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
        
        return {
            "question_vector": question_vector,
            "code_vector": code_vector,
            "log_vector": log_vector,
            "env_vector": env_vector
        }
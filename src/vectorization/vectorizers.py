import numpy as np
from typing import Optional, Any, Union, List, Dict
from sentence_transformers import SentenceTransformer
from sentence_transformers.models import Transformer, Pooling
from abc import ABC, abstractmethod
from src.models.bug_models import BugReport
import os
import traceback
from src.utils.log import get_logger

logger = get_logger(__name__)

# 禁用在线模型下载
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

class BaseVectorizer(ABC):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            # 获取项目根目录并切换工作目录
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            original_dir = os.getcwd()
            os.chdir(current_dir)
            
            model_path = os.path.join("lm-models", model_name)
            if not os.path.exists(model_path):
                raise RuntimeError(f"模型目录不存在: {os.path.abspath(model_path)}")
            
            logger.info(f"正在加载本地模型: {os.path.abspath(model_path)}")
            
            try:
                # 创建 Transformer 和 Pooling 模块
                word_embedding_model = Transformer(model_path)
                pooling_model = Pooling(word_embedding_model.get_word_embedding_dimension())
                
                # 创建 SentenceTransformer 实例
                self.model = SentenceTransformer(modules=[word_embedding_model, pooling_model])
                
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
    
    @abstractmethod
    def vectorize(self, data: Union[str, dict]) -> List[float]:
        pass

class SummaryVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, BugReport]) -> List[float]:
        try:
            if isinstance(data, str):
                text = data
            else:
                # 组合多个相关字段以生成更丰富的摘要向量
                text = f"{data.summary} {data.root_cause or ''} {data.fix_solution or ''}"
            return self.model.encode(text).tolist()
        except Exception as e:
            logger.error(f"摘要向量化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"摘要向量化失败: {str(e)}")

class CodeVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, BugReport]) -> List[float]:
        try:
            if isinstance(data, str):
                text = data
            else:
                # 仅使用 code_diffs 字段
                code_parts = data.code_diffs
                text = "\n".join(code_parts)
            return self.model.encode(text).tolist()
        except Exception as e:
            logger.error(f"代码向量化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"代码向量化失败: {str(e)}")

class TestVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, BugReport, Dict]) -> List[float]:
        try:
            if isinstance(data, str):
                text = data
            else:
                parts = []
                # 处理字典输入
                if isinstance(data, dict):
                    if data.get("test_steps"):
                        parts.append(f"测试步骤: {data['test_steps']}")
                    if data.get("expected_result"):
                        parts.append(f"预期结果: {data['expected_result']}")
                    if data.get("actual_result"):
                        parts.append(f"实际结果: {data['actual_result']}")
                else:
                    # 处理BugReport对象
                    if data.test_steps:
                        parts.append(f"测试步骤: {data.test_steps}")
                    if data.expected_result:
                        parts.append(f"预期结果: {data.expected_result}")
                    if data.actual_result:
                        parts.append(f"实际结果: {data.actual_result}")
                    if data.is_reappear:
                        parts.append(f"是否可重现: {data.is_reappear}")
                text = "\n".join(parts)
            return self.model.encode(text).tolist()
        except Exception as e:
            logger.error(f"测试向量化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"测试向量化失败: {str(e)}")

class LogVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, BugReport]) -> List[float]:
        try:
            if isinstance(data, str):
                text = data
            else:
                text = data.log_info
            return self.model.encode(text).tolist()
        except Exception as e:
            logger.error(f"日志向量化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"日志向量化失败: {str(e)}")

class SolutionVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, BugReport]) -> List[float]:
        try:
            if isinstance(data, str):
                text = data
            else:
                parts = []
                if data.root_cause:
                    parts.append(f"根本原因: {data.root_cause}")
                if data.fix_solution:
                    parts.append(f"修复方案: {data.fix_solution}")
                text = "\n".join(parts)
            return self.model.encode(text).tolist()
        except Exception as e:
            logger.error(f"解决方案向量化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"解决方案向量化失败: {str(e)}")

class EnvironmentVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, BugReport]) -> List[float]:
        try:
            if isinstance(data, str):
                text = data
            else:
                text = data.environment
            return self.model.encode(text).tolist()
        except Exception as e:
            logger.error(f"环境向量化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"环境向量化失败: {str(e)}")

class HybridVectorizer:
    def __init__(self):
        try:
            self.summary_vectorizer = SummaryVectorizer()
            self.code_vectorizer = CodeVectorizer()
            self.test_vectorizer = TestVectorizer()
            self.log_vectorizer = LogVectorizer()
            self.solution_vectorizer = SolutionVectorizer()
            self.environment_vectorizer = EnvironmentVectorizer()
        except Exception as e:
            logger.error(f"混合向量化器初始化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"混合向量化器初始化失败: {str(e)}")
    
    def vectorize_bug_report(self, bug_report: BugReport) -> Dict[str, List[float]]:
        try:
            return {
                "summary_vector": self.summary_vectorizer.vectorize(bug_report),
                "code_vector": self.code_vectorizer.vectorize(bug_report),
                "test_steps_vector": self.test_vectorizer.vectorize(bug_report),
                "expected_result_vector": self.test_vectorizer.vectorize(bug_report),
                "actual_result_vector": self.test_vectorizer.vectorize(bug_report),
                "log_info_vector": self.log_vectorizer.vectorize(bug_report),
                "environment_vector": self.environment_vectorizer.vectorize(bug_report)
            }
        except Exception as e:
            logger.error(f"Bug报告向量化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"Bug报告向量化失败: {str(e)}")
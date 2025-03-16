from abc import ABC, abstractmethod
from typing import Union, List
from sentence_transformers import SentenceTransformer
from sentence_transformers.models import Transformer, Pooling
from src.models.bug_models import BugReport, CodeContext, EnvironmentInfo
import os
import logging
import torch

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            if not os.path.exists(os.path.join(model_path, "modules.json")):
                raise RuntimeError(f"模型文件不完整，请确保所有必要文件都存在于 {os.path.abspath(model_path)}")
            
            logger.info(f"正在加载本地模型: {os.path.abspath(model_path)}")
            
            # 创建 Transformer 和 Pooling 模块
            word_embedding_model = Transformer(model_path)
            pooling_model = Pooling(word_embedding_model.get_word_embedding_dimension())
            
            # 创建 SentenceTransformer 实例
            self.model = SentenceTransformer(modules=[word_embedding_model, pooling_model])
            
            logger.info("本地模型加载成功")
            
            # 恢复原始工作目录
            os.chdir(original_dir)
            
        except Exception as e:
            # 确保在发生错误时也恢复原始工作目录
            if 'original_dir' in locals():
                os.chdir(original_dir)
            logger.error(f"模型加载失败: {str(e)}")
            raise RuntimeError(f"无法加载模型。错误: {str(e)}")
    
    @abstractmethod
    def vectorize(self, data: Union[str, dict]) -> List[float]:
        pass

class QuestionVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, BugReport]) -> List[float]:
        if isinstance(data, str):
            text = data
        else:
            text = f"{data.title} {data.description} {data.expected_behavior} {data.actual_behavior}"
        return self.model.encode(text).tolist()

class CodeVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, CodeContext]) -> List[float]:
        if isinstance(data, str):
            text = data
        else:
            text = f"{data.code} {data.language} {data.file_path}"
        return self.model.encode(text).tolist()

class LogVectorizer(BaseVectorizer):
    def vectorize(self, data: str) -> List[float]:
        return self.model.encode(data).tolist()

class EnvVectorizer(BaseVectorizer):
    def vectorize(self, data: Union[str, EnvironmentInfo]) -> List[float]:
        if isinstance(data, str):
            text = data
        else:
            text = f"{data.runtime_env} {data.os_info} {data.network_env}"
        return self.model.encode(text).tolist()

class HybridVectorizer:
    def __init__(self):
        self.question_vectorizer = QuestionVectorizer()
        self.code_vectorizer = CodeVectorizer()
        self.log_vectorizer = LogVectorizer()
        self.env_vectorizer = EnvVectorizer()
    
    def vectorize_bug_report(self, bug_report: BugReport) -> dict:
        return {
            "question_vector": self.question_vectorizer.vectorize(bug_report),
            "code_vector": self.code_vectorizer.vectorize(bug_report.code_context),
            "log_vector": self.log_vectorizer.vectorize(bug_report.error_logs),
            "env_vector": self.env_vectorizer.vectorize(bug_report.environment)
        } 
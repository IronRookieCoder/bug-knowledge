from abc import ABC, abstractmethod
from typing import Union, List
from sentence_transformers import SentenceTransformer
from src.models.bug_models import BugReport, CodeContext, EnvironmentInfo

class BaseVectorizer(ABC):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
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
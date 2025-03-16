import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from src.models.bug_models import BugReport
import json

class VectorStore:
    def __init__(self, persist_directory: str = "data/chroma"):
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        self.collection = self.client.get_or_create_collection(
            name="bug_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_bug_report(self, bug_report: BugReport, vectors: Dict[str, List[float]]):
        # 将BugReport转换为JSON字符串
        metadata = bug_report.model_dump()
        
        # 添加到向量数据库
        self.collection.add(
            ids=[bug_report.id],
            embeddings={
                "question": vectors["question_vector"],
                "code": vectors["code_vector"],
                "log": vectors["log_vector"],
                "env": vectors["env_vector"]
            },
            metadatas=[metadata],
            documents=[bug_report.model_dump_json()]
        )
    
    def search(self, 
              query_vectors: Dict[str, List[float]], 
              n_results: int = 5,
              weights: Optional[Dict[str, float]] = None) -> List[Dict]:
        if weights is None:
            weights = {
                "question": 0.4,
                "code": 0.3,
                "log": 0.2,
                "env": 0.1
            }
        
        results = self.collection.query(
            query_embeddings={
                "question": query_vectors["question_vector"],
                "code": query_vectors["code_vector"],
                "log": query_vectors["log_vector"],
                "env": query_vectors["env_vector"]
            },
            n_results=n_results
        )
        
        # 解析结果
        bug_reports = []
        for i in range(len(results["ids"][0])):
            bug_report = json.loads(results["documents"][0][i])
            bug_report["distance"] = results["distances"][0][i]
            bug_reports.append(bug_report)
        
        return bug_reports 
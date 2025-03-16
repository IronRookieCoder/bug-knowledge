from typing import List, Dict, Optional
import json
import os
from annoy import AnnoyIndex
from src.models.bug_models import BugReport

class VectorStore:
    def __init__(self, data_dir: str = "data/annoy"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # 存储BUG报告的元数据
        self.metadata_file = os.path.join(data_dir, "metadata.json")
        self.metadata = self._load_metadata()
        
        # 初始化向量索引
        self.vector_dim = 384  # sentence-transformers默认维度
        self.question_index = self._create_or_load_index("question")
        self.code_index = self._create_or_load_index("code")
        self.log_index = self._create_or_load_index("log")
        self.env_index = self._create_or_load_index("env")
    
    def _load_metadata(self) -> Dict:
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def _create_or_load_index(self, name: str) -> AnnoyIndex:
        index = AnnoyIndex(self.vector_dim, 'angular')
        index_file = os.path.join(self.data_dir, f"{name}.ann")
        if os.path.exists(index_file):
            index.load(index_file)
        return index
    
    def add_bug_report(self, bug_report: BugReport, vectors: Dict[str, List[float]]):
        # 获取当前索引大小作为新ID
        idx = len(self.metadata)
        
        # 添加向量到索引
        self.question_index.add_item(idx, vectors["question_vector"])
        self.code_index.add_item(idx, vectors["code_vector"])
        self.log_index.add_item(idx, vectors["log_vector"])
        self.env_index.add_item(idx, vectors["env_vector"])
        
        # 保存元数据
        self.metadata[str(idx)] = bug_report.model_dump()
        
        # 保存索引和元数据
        self._save_indices()
        self._save_metadata()
    
    def _save_indices(self):
        self.question_index.build(10)  # 10棵树
        self.code_index.build(10)
        self.log_index.build(10)
        self.env_index.build(10)
        
        self.question_index.save(os.path.join(self.data_dir, "question.ann"))
        self.code_index.save(os.path.join(self.data_dir, "code.ann"))
        self.log_index.save(os.path.join(self.data_dir, "log.ann"))
        self.env_index.save(os.path.join(self.data_dir, "env.ann"))
    
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
        
        # 获取每个向量的最近邻
        question_nns = self.question_index.get_nns_by_vector(query_vectors["question_vector"], n_results, include_distances=True)
        code_nns = self.code_index.get_nns_by_vector(query_vectors["code_vector"], n_results, include_distances=True)
        log_nns = self.log_index.get_nns_by_vector(query_vectors["log_vector"], n_results, include_distances=True)
        env_nns = self.env_index.get_nns_by_vector(query_vectors["env_vector"], n_results, include_distances=True)
        
        # 合并结果
        results = {}
        for idx, dist in zip(*question_nns):
            results[idx] = {"distance": dist * weights["question"]}
            
        for idx, dist in zip(*code_nns):
            if idx in results:
                results[idx]["distance"] += dist * weights["code"]
            else:
                results[idx] = {"distance": dist * weights["code"]}
                
        for idx, dist in zip(*log_nns):
            if idx in results:
                results[idx]["distance"] += dist * weights["log"]
            else:
                results[idx] = {"distance": dist * weights["log"]}
                
        for idx, dist in zip(*env_nns):
            if idx in results:
                results[idx]["distance"] += dist * weights["env"]
            else:
                results[idx] = {"distance": dist * weights["env"]}
        
        # 排序并返回结果
        sorted_results = []
        for idx, score in sorted(results.items(), key=lambda x: x[1]["distance"])[:n_results]:
            result = self.metadata[str(idx)].copy()
            result["distance"] = score["distance"]
            sorted_results.append(result)
        
        return sorted_results 
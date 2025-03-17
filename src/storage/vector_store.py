from typing import List, Dict, Optional, Tuple
import json
import os
from annoy import AnnoyIndex
from src.models.bug_models import BugReport
from datetime import datetime
import numpy as np
import logging
from pathlib import Path
import tempfile
import shutil
import traceback

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, data_dir="data/annoy"):
        try:
            # 使用绝对路径并确保使用正斜杠
            self.data_dir = os.path.abspath(data_dir).replace('\\', '/')
            os.makedirs(self.data_dir, exist_ok=True)
            
            self.metadata_file = os.path.join(self.data_dir, "metadata.json").replace('\\', '/')
            self.metadata = self._load_metadata()
            
            # 初始化索引
            self.question_index = None
            self.code_index = None
            self.log_index = None
            self.env_index = None
            
            self._load_existing_indices()
            logger.info(f"向量存储初始化成功: {self.data_dir}")
        except Exception as e:
            logger.error(f"向量存储初始化失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"向量存储初始化失败: {str(e)}")
    
    def _load_metadata(self):
        if not os.path.exists(self.metadata_file):
            logger.warning(f"元数据文件不存在，创建新文件: {self.metadata_file}")
            return {"questions": [], "codes": [], "logs": [], "envs": []}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"元数据文件损坏，创建新文件: {self.metadata_file}")
            return {"questions": [], "codes": [], "logs": [], "envs": []}
    
    def _save_metadata(self):
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存元数据失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"保存元数据失败: {str(e)}")
    
    def _load_existing_indices(self):
        try:
            indices_dir = os.path.join(self.data_dir, "indices").replace('\\', '/')
            if not os.path.exists(indices_dir):
                logger.info("索引目录不存在，跳过加载")
                return
            
            # 加载向量
            question_vectors = np.load(os.path.join(indices_dir, "question.npy"))
            code_vectors = np.load(os.path.join(indices_dir, "code.npy"))
            log_vectors = np.load(os.path.join(indices_dir, "log.npy"))
            env_vectors = np.load(os.path.join(indices_dir, "env.npy"))
            
            # 创建索引
            self.question_index = AnnoyIndex(384, 'angular')
            self.code_index = AnnoyIndex(384, 'angular')
            self.log_index = AnnoyIndex(384, 'angular')
            self.env_index = AnnoyIndex(384, 'angular')
            
            # 添加向量
            for i, vector in enumerate(question_vectors):
                self.question_index.add_item(i, vector)
            for i, vector in enumerate(code_vectors):
                self.code_index.add_item(i, vector)
            for i, vector in enumerate(log_vectors):
                self.log_index.add_item(i, vector)
            for i, vector in enumerate(env_vectors):
                self.env_index.add_item(i, vector)
            
            # 构建索引
            self.question_index.build(10)
            self.code_index.build(10)
            self.log_index.build(10)
            self.env_index.build(10)
            
            logger.info("成功加载现有索引")
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"加载索引失败: {str(e)}")
    
    def add_bug_report(self, bug_report, vectors):
        try:
            # 创建新的索引
            new_question_index = AnnoyIndex(384, 'angular')
            new_code_index = AnnoyIndex(384, 'angular')
            new_log_index = AnnoyIndex(384, 'angular')
            new_env_index = AnnoyIndex(384, 'angular')
            
            # 收集所有向量
            question_vectors = []
            code_vectors = []
            log_vectors = []
            env_vectors = []
            
            # 复制现有项目
            if self.question_index:
                for i in range(len(self.metadata["questions"])):
                    vector = self.question_index.get_item_vector(i)
                    question_vectors.append(vector)
                    new_question_index.add_item(i, vector)
            
            if self.code_index:
                for i in range(len(self.metadata["codes"])):
                    vector = self.code_index.get_item_vector(i)
                    code_vectors.append(vector)
                    new_code_index.add_item(i, vector)
            
            if self.log_index:
                for i in range(len(self.metadata["logs"])):
                    vector = self.log_index.get_item_vector(i)
                    log_vectors.append(vector)
                    new_log_index.add_item(i, vector)
            
            if self.env_index:
                for i in range(len(self.metadata["envs"])):
                    vector = self.env_index.get_item_vector(i)
                    env_vectors.append(vector)
                    new_env_index.add_item(i, vector)
            
            # 添加新项目
            question_vectors.append(vectors["question_vector"])
            code_vectors.append(vectors["code_vector"])
            log_vectors.append(vectors["log_vector"])
            env_vectors.append(vectors["env_vector"])
            
            new_question_index.add_item(len(question_vectors) - 1, vectors["question_vector"])
            new_code_index.add_item(len(code_vectors) - 1, vectors["code_vector"])
            new_log_index.add_item(len(log_vectors) - 1, vectors["log_vector"])
            new_env_index.add_item(len(env_vectors) - 1, vectors["env_vector"])
            
            # 构建索引
            new_question_index.build(10)
            new_code_index.build(10)
            new_log_index.build(10)
            new_env_index.build(10)
            
            # 确保索引目录存在
            indices_dir = os.path.join(self.data_dir, "indices").replace('\\', '/')
            os.makedirs(indices_dir, exist_ok=True)
            
            # 保存向量
            question_index_path = os.path.join(indices_dir, "question.npy").replace('\\', '/')
            code_index_path = os.path.join(indices_dir, "code.npy").replace('\\', '/')
            log_index_path = os.path.join(indices_dir, "log.npy").replace('\\', '/')
            env_index_path = os.path.join(indices_dir, "env.npy").replace('\\', '/')
            
            logger.info(f"保存向量到: {question_index_path}")
            np.save(question_index_path, np.array(question_vectors))
            np.save(code_index_path, np.array(code_vectors))
            np.save(log_index_path, np.array(log_vectors))
            np.save(env_index_path, np.array(env_vectors))
            
            # 更新元数据
            self.metadata["questions"].append({
                "id": bug_report.id,
                "title": bug_report.title,
                "description": bug_report.description
            })
            
            self.metadata["codes"].append({
                "id": bug_report.id,
                "code": bug_report.code_context.code
            })
            
            self.metadata["logs"].append({
                "id": bug_report.id,
                "log": bug_report.error_logs
            })
            
            self.metadata["envs"].append({
                "id": bug_report.id,
                "env": str(bug_report.environment)
            })
            
            self._save_metadata()
            
            # 更新当前索引
            self.question_index = new_question_index
            self.code_index = new_code_index
            self.log_index = new_log_index
            self.env_index = new_env_index
            
            logger.info(f"成功添加Bug报告: {bug_report.id}")
        except Exception as e:
            logger.error(f"添加Bug报告失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"添加Bug报告失败: {str(e)}")
    
    def search(self, query_vectors, n_results=5, weights=None):
        try:
            if weights is None:
                # 调整权重，增加问题描述的权重
                weights = {
                    "question": 2.0,  # 增加问题描述的权重
                    "code": 1.0,
                    "log": 0.5,  # 降低日志的权重
                    "env": 0.3   # 降低环境信息的权重
                }
            
            if not self.question_index:
                logger.warning("索引为空，无法搜索")
                return []
            
            # 获取每个向量的最近邻
            question_neighbors = self.question_index.get_nns_by_vector(
                query_vectors["question_vector"], n_results, include_distances=True)
            code_neighbors = self.code_index.get_nns_by_vector(
                query_vectors["code_vector"], n_results, include_distances=True)
            log_neighbors = self.log_index.get_nns_by_vector(
                query_vectors["log_vector"], n_results, include_distances=True)
            env_neighbors = self.env_index.get_nns_by_vector(
                query_vectors["env_vector"], n_results, include_distances=True)
            
            # 计算每个维度的最大距离用于归一化
            max_distances = {
                "question": max(question_neighbors[1]) if question_neighbors[1] else 1.0,
                "code": max(code_neighbors[1]) if code_neighbors[1] else 1.0,
                "log": max(log_neighbors[1]) if log_neighbors[1] else 1.0,
                "env": max(env_neighbors[1]) if env_neighbors[1] else 1.0
            }
            
            # 合并结果并进行归一化
            results = {}
            
            # 处理问题描述向量
            for i, (idx, dist) in enumerate(zip(question_neighbors[0], question_neighbors[1])):
                normalized_dist = dist / max_distances["question"]
                # 使用余弦相似度转换
                cosine_sim = 1 - (normalized_dist ** 2) / 2
                results[idx] = {"distance": (1 - cosine_sim) * weights["question"]}
            
            # 处理代码向量
            for i, (idx, dist) in enumerate(zip(code_neighbors[0], code_neighbors[1])):
                normalized_dist = dist / max_distances["code"]
                cosine_sim = 1 - (normalized_dist ** 2) / 2
                if idx in results:
                    results[idx]["distance"] += (1 - cosine_sim) * weights["code"]
                else:
                    results[idx] = {"distance": (1 - cosine_sim) * weights["code"]}
            
            # 处理日志向量
            for i, (idx, dist) in enumerate(zip(log_neighbors[0], log_neighbors[1])):
                normalized_dist = dist / max_distances["log"]
                cosine_sim = 1 - (normalized_dist ** 2) / 2
                if idx in results:
                    results[idx]["distance"] += (1 - cosine_sim) * weights["log"]
                else:
                    results[idx] = {"distance": (1 - cosine_sim) * weights["log"]}
            
            # 处理环境向量
            for i, (idx, dist) in enumerate(zip(env_neighbors[0], env_neighbors[1])):
                normalized_dist = dist / max_distances["env"]
                cosine_sim = 1 - (normalized_dist ** 2) / 2
                if idx in results:
                    results[idx]["distance"] += (1 - cosine_sim) * weights["env"]
                else:
                    results[idx] = {"distance": (1 - cosine_sim) * weights["env"]}
            
            # 计算总权重用于归一化最终距离
            total_weight = sum(weights.values())
            
            # 按距离排序并返回结果
            sorted_results = []
            for idx, score in sorted(results.items(), key=lambda x: x[1]["distance"])[:n_results]:
                result = self.metadata["questions"][idx].copy()
                # 归一化最终距离并转换为相似度分数
                normalized_distance = score["distance"] / total_weight
                result["distance"] = normalized_distance
                sorted_results.append(result)
            
            logger.info(f"搜索完成，找到 {len(sorted_results)} 条结果")
            return sorted_results
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"搜索失败: {str(e)}") 
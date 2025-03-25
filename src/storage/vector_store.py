from typing import List, Dict, Optional, Tuple, Any
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
from src.features.code_features import CodeFeatureExtractor, CodeFeatures

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, data_dir: str = "data/annoy", vector_dim: int = 384, index_type: str = "angular"):
        self.data_dir = data_dir
        self.vector_dim = vector_dim
        self.index_type = index_type
        
        # 创建数据目录
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化索引
        self.description_index = None
        self.steps_index = None
        self.expected_index = None
        self.actual_index = None
        self.code_index = None
        self.log_index = None
        self.env_index = None
        
        # 初始化元数据
        self.metadata = {
            "bugs": {},
            "next_id": 0
        }
        
        # 加载或创建索引
        self._load_or_create_indices()
    
    def _load_or_create_indices(self):
        """加载或创建索引"""
        try:
            # 加载元数据
            metadata_path = os.path.join(self.data_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                    # 转换时间字符串为datetime对象
                    for bug_id, bug_data in self.metadata["bugs"].items():
                        bug_data["created_at"] = datetime.fromisoformat(bug_data["created_at"])
                        bug_data["updated_at"] = datetime.fromisoformat(bug_data["updated_at"])
            
            # 创建或加载索引
            self.description_index = self._create_or_load_index("description")
            self.steps_index = self._create_or_load_index("steps")
            self.expected_index = self._create_or_load_index("expected")
            self.actual_index = self._create_or_load_index("actual")
            self.code_index = self._create_or_load_index("code")
            self.log_index = self._create_or_load_index("log")
            self.env_index = self._create_or_load_index("env")
            
        except Exception as e:
            logger.error(f"加载索引失败，将创建新索引: {str(e)}")
            # 创建新的索引
            self._create_new_indices()
    
    def _create_or_load_index(self, name: str) -> Optional[AnnoyIndex]:
        """创建或加载单个索引"""
        try:
            index = AnnoyIndex(self.vector_dim, self.index_type)
            index_path = os.path.join(self.data_dir, f"{name}.ann")
            
            if os.path.exists(index_path):
                # 如果索引文件存在，尝试加载它
                try:
                    index.load(index_path)
                    logger.info(f"成功加载索引: {name}, 包含 {index.get_n_items()} 个项目")
                    return index
                except Exception as e:
                    logger.error(f"加载索引 {name} 失败，将创建新索引: {str(e)}")
                    # 如果加载失败，创建新的索引
                    return AnnoyIndex(self.vector_dim, self.index_type)
            else:
                logger.info(f"索引文件不存在，创建新索引: {name}")
                return index
        except Exception as e:
            logger.error(f"初始化索引 {name} 失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 返回 None 表示索引创建失败
            return None
    
    def _create_new_indices(self):
        """创建新的索引"""
        self.description_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.steps_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.expected_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.actual_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.code_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.log_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.env_index = AnnoyIndex(self.vector_dim, self.index_type)
    
    def _save_indices(self):
        """保存索引和元数据"""
        # 在保存之前转换datetime对象为ISO格式字符串
        metadata_copy = {
            "bugs": {},
            "next_id": self.metadata["next_id"]
        }
        
        for bug_id, bug_data in self.metadata["bugs"].items():
            metadata_copy["bugs"][bug_id] = bug_data.copy()
            metadata_copy["bugs"][bug_id]["created_at"] = bug_data["created_at"].isoformat()
            metadata_copy["bugs"][bug_id]["updated_at"] = bug_data["updated_at"].isoformat()
        
        # 保存元数据
        with open(os.path.join(self.data_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata_copy, f, ensure_ascii=False, indent=2)
        
        # 构建并保存索引
        self._build_and_save_index(self.description_index, "description")
        self._build_and_save_index(self.steps_index, "steps")
        self._build_and_save_index(self.expected_index, "expected")
        self._build_and_save_index(self.actual_index, "actual")
        self._build_and_save_index(self.code_index, "code")
        self._build_and_save_index(self.log_index, "log")
        self._build_and_save_index(self.env_index, "env")
    
    def _build_and_save_index(self, index: Optional[AnnoyIndex], name: str):
        """构建并保存单个索引"""
        if index is None:
            logger.warning(f"索引 {name} 为 None，无法保存")
            return
        
        # 检查索引是否包含项目
        if index.get_n_items() <= 0:
            logger.info(f"索引 {name} 为空，跳过保存")
            return
        
        temp_path = None
        try:
            # 构建索引
            index.build(10)  # 使用10棵树
            # 保存到临时文件
            temp_path = os.path.join(self.data_dir, f"{name}.ann.tmp")
            index.save(temp_path)
            # 原子地替换旧文件
            final_path = os.path.join(self.data_dir, f"{name}.ann")
            os.replace(temp_path, final_path)
            logger.info(f"成功保存索引: {name}")
        except Exception as e:
            logger.error(f"保存索引 {name} 失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    logger.warning(f"删除临时索引文件失败: {temp_path}")
            
    def add_bug_report(self, bug_report: BugReport, vectors: Dict[str, Any]):
        """添加bug报告到索引"""
        try:
            # 获取新的ID
            idx = self.metadata["next_id"]
            self.metadata["next_id"] += 1
            
            # 保存bug报告元数据
            self.metadata["bugs"][str(idx)] = {
                "id": bug_report.id,
                "description": bug_report.description,
                "reproducible": bug_report.reproducible,
                "steps_to_reproduce": bug_report.steps_to_reproduce,
                "expected_behavior": bug_report.expected_behavior,
                "actual_behavior": bug_report.actual_behavior,
                "code_context": {
                    "code": bug_report.code_context.code if bug_report.code_context else "",
                    "file_path": bug_report.code_context.file_path if bug_report.code_context else "",
                    "line_range": bug_report.code_context.line_range if bug_report.code_context else [],
                    "language": bug_report.code_context.language if bug_report.code_context else ""
                },
                "error_logs": bug_report.error_logs,
                "environment": {
                    "runtime_env": bug_report.environment.runtime_env if bug_report.environment else "",
                    "os_info": bug_report.environment.os_info if bug_report.environment else "",
                    "network_env": bug_report.environment.network_env if bug_report.environment else ""
                },
                "created_at": bug_report.created_at,
                "updated_at": bug_report.updated_at
            }
            
            # 添加向量到索引
            success = True
            try:
                if "description_vector" in vectors and self.description_index is not None:
                    self.description_index.add_item(idx, vectors["description_vector"])
                if "steps_vector" in vectors and self.steps_index is not None:
                    self.steps_index.add_item(idx, vectors["steps_vector"])
                if "expected_vector" in vectors and self.expected_index is not None:
                    self.expected_index.add_item(idx, vectors["expected_vector"])
                if "actual_vector" in vectors and self.actual_index is not None:
                    self.actual_index.add_item(idx, vectors["actual_vector"])
                if "code_vector" in vectors and self.code_index is not None:
                    self.code_index.add_item(idx, vectors["code_vector"])
                if "log_vector" in vectors and self.log_index is not None:
                    self.log_index.add_item(idx, vectors["log_vector"])
                if "env_vector" in vectors and self.env_index is not None:
                    self.env_index.add_item(idx, vectors["env_vector"])
                
                # 保存更改
                self._save_indices()
                
            except Exception as e:
                logger.error(f"添加向量到索引失败: {str(e)}")
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                success = False
                # 如果添加向量失败，回滚元数据更改
                if str(idx) in self.metadata["bugs"]:
                    del self.metadata["bugs"][str(idx)]
                self.metadata["next_id"] = idx
            
            return success
            
        except Exception as e:
            logger.error(f"添加bug报告失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False
    
    def search(self, query_vectors: Dict[str, Any], n_results: int = 5, weights: Dict[str, float] = None) -> List[Dict]:
        """搜索相似的bug报告"""
        try:
            logger.info(f"开始搜索，请求返回 {n_results} 个结果")
            
            # 如果没有提供权重，使用默认权重
            if weights is None:
                weights = {
                    "description": 0.2,
                    "steps": 0.15,
                    "expected": 0.1,
                    "actual": 0.15,
                    "code": 0.2,
                    "log": 0.2,
                    "env": 0.0
                }
            
            # 确保所有权重都是浮点数
            weights = {k: float(v) for k, v in weights.items()}
            logger.debug(f"搜索权重: {weights}")
            
            # 如果没有查询向量，返回空结果
            if not query_vectors:
                logger.warning("没有提供查询向量，返回空结果")
                return []
            
            logger.debug(f"查询向量类型: {list(query_vectors.keys())}")
            
            # 收集所有结果
            results = {}
            
            # 获取所有索引中的结果数量
            total_index_items = 0
            if self.description_index:
                total_index_items = max(total_index_items, self.description_index.get_n_items())
            
            # 计算要请求的结果数量 - 确保足够多
            requested_results = min(max(50, n_results * 10), total_index_items) if total_index_items > 0 else max(50, n_results * 10)
            logger.info(f"预计返回 {requested_results} 个初始结果进行排序和过滤")
            
            # 对每个向量进行搜索
            if "description_vector" in query_vectors and self.description_index is not None:
                description_results = self._search_index(self.description_index, query_vectors["description_vector"], 
                                               requested_results, weights.get("description", 0))
                results.update(description_results)
            
            if "steps_vector" in query_vectors and self.steps_index is not None:
                steps_results = self._search_index(self.steps_index, query_vectors["steps_vector"], 
                                               requested_results, weights.get("steps", 0))
                results.update(steps_results)
            
            if "expected_vector" in query_vectors and self.expected_index is not None:
                expected_results = self._search_index(self.expected_index, query_vectors["expected_vector"], 
                                               requested_results, weights.get("expected", 0))
                results.update(expected_results)
            
            if "actual_vector" in query_vectors and self.actual_index is not None:
                actual_results = self._search_index(self.actual_index, query_vectors["actual_vector"], 
                                               requested_results, weights.get("actual", 0))
                results.update(actual_results)
            
            if "code_vector" in query_vectors and self.code_index is not None:
                code_results = self._search_index(self.code_index, query_vectors["code_vector"], 
                                               requested_results, weights.get("code", 0))
                results.update(code_results)
            
            if "log_vector" in query_vectors and self.log_index is not None:
                log_results = self._search_index(self.log_index, query_vectors["log_vector"], 
                                               requested_results, weights.get("log", 0))
                results.update(log_results)
            
            if "env_vector" in query_vectors and self.env_index is not None:
                env_results = self._search_index(self.env_index, query_vectors["env_vector"], 
                                               requested_results, weights.get("env", 0))
                results.update(env_results)
            
            # 如果没有结果，返回空列表
            if not results:
                logger.info("搜索没有找到任何结果")
                return []
            
            logger.info(f"合并索引搜索结果: 找到 {len(results)} 个唯一ID")
            
            # 对结果进行排序 - 按距离升序排序（越小越相似）
            sorted_results = sorted(results.items(), key=lambda x: x[1]["distance"])
            
            # 输出前10个结果的ID和距离
            top_results_info = []
            for i, (idx, score) in enumerate(sorted_results[:10], 1):
                top_results_info.append(f"#{i}: ID={idx}, 距离={score['distance']:.4f}")
            logger.info(f"排序后的前10个结果: {', '.join(top_results_info)}")
            
            # 构建有效结果列表 - 从元数据中获取完整信息
            valid_results = []
            valid_ids = set()  # 用于去重
            
            for idx, score in sorted_results:
                # 防止重复结果
                if idx in valid_ids:
                    continue
                
                # 确保索引存在于元数据中
                str_idx = str(idx)
                if str_idx in self.metadata["bugs"]:
                    bug_data = self.metadata["bugs"][str_idx].copy()
                    bug_data["distance"] = score["distance"]
                    valid_results.append(bug_data)
                    valid_ids.add(idx)
                    
                    # 当收集到足够多的结果后停止
                    if len(valid_results) >= min(n_results * 5, 100):
                        logger.info(f"收集到足够的有效结果: {len(valid_results)}个")
                        break
                else:
                    logger.warning(f"索引 {idx} 在元数据中不存在，跳过")
            
            # 确保返回数量不超过请求数量
            final_results = valid_results[:n_results]
            logger.info(f"搜索完成，返回 {len(final_results)} 个结果")
            
            # 记录返回的结果ID和距离
            for i, result in enumerate(final_results, 1):
                logger.info(f"最终结果 #{i}: ID={result['id']}, 距离={result['distance']:.4f}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 返回空结果而不是抛出异常
            return []
    
    def _search_index(self, index: AnnoyIndex, vector: List[float], n_results: int, weight: float) -> Dict[int, Dict]:
        """在单个索引中搜索"""
        if index is None or index.get_n_items() == 0 or weight == 0:
            return {}
        
        try:
            # 获取索引中项目的总数量
            total_items = index.get_n_items()
            if total_items == 0:
                logger.warning("索引为空，无法搜索")
                return {}
                
            # 确定要返回的结果数量，确保不超过索引中的总数量
            search_n_results = min(max(50, n_results * 10), total_items)
            
            logger.info(f"在索引中搜索: 索引项目总数={total_items}, 请求返回={search_n_results}, 权重={weight}")
            
            # 获取最近邻，增加搜索半径，设置include_distances=True表示返回距离信息
            ids, distances = index.get_nns_by_vector(
                vector, 
                search_n_results, 
                include_distances=True, 
                search_k=-1  # -1表示检查所有节点，确保尽可能准确的结果
            )
            
            # 记录找到的结果数量以及前几个ID
            logger.info(f"索引搜索结果: 找到 {len(ids)} 个匹配项")
            if ids:
                first_ids = ids[:min(5, len(ids))]
                first_distances = distances[:min(5, len(distances))]
                id_dist_pairs = [f"({i}:{d:.4f})" for i, d in zip(first_ids, first_distances)]
                logger.info(f"前5个结果 [ID:距离]: {', '.join(id_dist_pairs)}")
            
            # 返回所有结果，不进行距离过滤，交由搜索函数处理
            results = {idx: {"distance": dist * weight} for idx, dist in zip(ids, distances)}
            logger.info(f"返回 {len(results)} 个匹配项的加权结果")
            return results
            
        except Exception as e:
            logger.error(f"搜索索引失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 返回空结果而不是抛出异常
            return {}
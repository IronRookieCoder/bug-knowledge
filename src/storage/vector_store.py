import json
import os
import gc
import traceback
from pathlib import Path
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from annoy import AnnoyIndex
import numpy as np
import time
from functools import lru_cache
from src.utils.log import logger
from src.storage.database import BugDatabase

class VectorStore:
    def __init__(self, data_dir: str = "data/annoy", vector_dim: int = 384, index_type: str = "angular", n_trees: int = 10, similarity_threshold: float = 1.0):
        self.data_dir = Path(data_dir)
        self.vector_dim = vector_dim
        self.index_type = index_type
        self.n_trees = n_trees
        self.similarity_threshold = similarity_threshold  # 相似度阈值

        # 创建数据目录
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "temp").mkdir(exist_ok=True)
        (self.data_dir / "backup").mkdir(exist_ok=True)

        # 初始化索引属性为 None
        self.summary_index: Optional[AnnoyIndex] = None
        self.code_index: Optional[AnnoyIndex] = None
        self.test_info_index: Optional[AnnoyIndex] = None
        self.log_info_index: Optional[AnnoyIndex] = None
        self.environment_index: Optional[AnnoyIndex] = None

        # 初始化数据库
        self.db = BugDatabase()

        # 加载索引（用于查询，add会强制重新加载和构建）
        self._load_indices_for_read()

    def _backup_indices(self):
        """备份索引文件"""
        try:
            backup_dir = self.data_dir / "backup" / time.strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            for name in ["summary", "code", "test_info", "log_info", "environment"]:
                index_path = self._get_index_path(name)
                if index_path.exists():
                    shutil.copy2(index_path, backup_dir / f"{name}.ann")
                    logger.info(f"已备份索引文件: {name}.ann")
            
            logger.info(f"索引备份完成: {backup_dir}")
        except Exception as e:
            logger.error(f"索引备份失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")

    def _get_index_path(self, name: str) -> Path:
        """获取索引文件的完整路径"""
        return self.data_dir / f"{name}.ann"

    def _create_or_load_index(self, name: str, for_read: bool) -> Optional[AnnoyIndex]:
        """创建或加载索引的通用方法"""
        index_path = self._get_index_path(name)
        index = AnnoyIndex(self.vector_dim, self.index_type)
        
        if index_path.exists():
            try:
                index.load(str(index_path))
                logger.info(f"成功加载 {name} 索引，包含 {index.get_n_items()} 个项目")
            except Exception as e:
                logger.warning(f"加载 {name} 索引失败，创建新索引: {str(e)}")
                index = AnnoyIndex(self.vector_dim, self.index_type)
        else:
            logger.info(f"{name} 索引不存在，创建新索引")
        
        if not for_read and index.get_n_items() > 0:
            index.build(10)  # 初始化构建
        
        return index

    def _build_and_save_index(self, index: Optional[AnnoyIndex], name: str) -> Optional[AnnoyIndex]:
        """构建并保存索引"""
        if not index:
            logger.warning(f"尝试构建和保存索引 '{name}'，但实例为 None。")
            return None

        temp_path = self.data_dir / "temp" / f"{name}_{int(time.time())}.ann.tmp"
        target_path = self._get_index_path(name)
        new_index = None # 初始化 new_index

        try:
            logger.info(f"开始构建索引 '{name}'...")
            index.build(self.n_trees)
            logger.info(f"索引 '{name}' 构建完成。")

            # 创建临时文件目录
            temp_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"开始保存索引 '{name}' 到临时文件: {temp_path}")
            index.save(str(temp_path))
            logger.info(f"索引 '{name}' 已保存到临时文件。")

            # --- 关键步骤：在替换前卸载旧索引 ---
            logger.debug(f"准备替换文件: {target_path}")
            logger.debug(f"尝试卸载传入的索引对象 '{name}' (ID: {id(index)}) 以释放潜在锁...")
            try:
                index.unload()
                logger.debug(f"传入的索引对象 '{name}' 已卸载。")
            except Exception as e_unload1:
                # 即使卸载失败也记录并尝试继续，可能锁不在这个对象上
                logger.warning(f"卸载传入的索引对象 '{name}' 时发生错误 (可能无影响): {e_unload1}")

            # 额外保障：获取并尝试卸载当前 self.<name>_index 属性持有的实例
            current_self_index = getattr(self, f"{name}_index", None)
            if current_self_index and current_self_index is not index: # 避免重复卸载同一个对象
                logger.debug(f"尝试卸载存储在 self.{name}_index 的旧实例 (ID: {id(current_self_index)}) ...")
                try:
                    current_self_index.unload()
                    logger.debug(f"存储在 self.{name}_index 的旧实例已卸载。")
                    # 主动触发垃圾回收可能有助于更快释放文件句柄
                    del current_self_index
                    gc.collect()
                except Exception as e_unload2:
                    logger.warning(f"卸载旧的 self.{name}_index 实例时发生错误: {e_unload2}")
            elif current_self_index and current_self_index is index:
                 logger.debug(f"存储在 self.{name}_index 的实例与传入实例相同，无需重复卸载。")

            # --- 文件替换 ---
            logger.info(f"尝试原子替换: '{temp_path}' -> '{target_path}'")
            try:
                # 确保目标文件不存在
                if target_path.exists():
                    target_path.unlink()
                # 使用rename而不是move
                temp_path.rename(target_path)
                logger.info(f"文件替换成功: '{target_path}'")
            except PermissionError as pe:
                logger.error(f"文件替换时再次遇到权限错误 (WinError 32): {pe}")
                logger.error(f"源文件: {temp_path}, 目标文件: {target_path}")
                raise
            except Exception as move_err:
                logger.error(f"文件替换时发生其他错误: {move_err}")
                raise

            # --- 重新加载索引 ---
            logger.info(f"开始重新加载更新后的索引 '{name}' 从: {target_path}")
            new_index = AnnoyIndex(self.vector_dim, self.index_type)
            new_index.load(str(target_path))
            logger.info(f"索引 '{name}' 重新加载成功，包含 {new_index.get_n_items()} 个项目。")

            return new_index

        except Exception as e:
            logger.error(f"处理（构建、保存、替换或重新加载）索引 '{name}' 过程中失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 清理临时文件
            if temp_path.exists():
                try:
                    temp_path.unlink()
                    logger.info(f"已删除失败过程中的临时索引文件: {temp_path}")
                except OSError as rm_e:
                    logger.warning(f"删除临时索引文件 {temp_path} 失败: {rm_e}")
            return None

    def _save_indices(self):
        """保存索引"""
        logger.info("开始保存索引...")
        try:
            # 构建、保存、卸载、重新加载所有新索引
            indices_to_process = {
                "summary": self.summary_index,
                "code": self.code_index,
                "test_info": self.test_info_index,
                "log_info": self.log_info_index,
                "environment": self.environment_index
            }

            new_loaded_indices: Dict[str, Optional[AnnoyIndex]] = {}

            for name, index_instance in indices_to_process.items():
                try:
                    reloaded_instance = self._build_and_save_index(index_instance, name)
                    new_loaded_indices[name] = reloaded_instance
                except Exception as e:
                    logger.error(f"处理索引 {name} 时发生意外错误: {str(e)}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    new_loaded_indices[name] = None

            # 更新类实例的索引属性
            self.summary_index = new_loaded_indices.get("summary")
            self.code_index = new_loaded_indices.get("code")
            self.test_info_index = new_loaded_indices.get("test_info")
            self.log_info_index = new_loaded_indices.get("log_info")
            self.environment_index = new_loaded_indices.get("environment")
            
            logger.info("内存中的索引实例已更新为重新加载后的版本。")
            logger.info("所有索引处理完成。")
            
            # 备份索引
            self._backup_indices()

        except Exception as e:
            logger.error(f"保存索引过程中发生顶层错误: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise

    @lru_cache(maxsize=1000)
    def _cached_search(self, vector_key: str, vector: Tuple[float], n_results: int) -> Dict[int, float]:
        """缓存搜索结果"""
        index = getattr(self, f"{vector_key}_index")
        if not index:
            return {}
            
        try:
            # 获取最近邻
            ids, distances = index.get_nns_by_vector(
                list(vector),
                n_results,
                include_distances=True,
                search_k=100
            )
            return dict(zip(ids, distances))
        except Exception as e:
            logger.error(f"缓存搜索失败: {str(e)}")
            return {}

    def add_bug_report(self, bug_report: Any, vectors: Dict[str, Any]):
        """添加单个bug报告及其向量到索引"""
        logger.info(f"开始添加 bug report...")
        start_time = time.time()

        try:
            # 从bug_report中获取bug_id和其他数据
            bug_data = bug_report if isinstance(bug_report, dict) else vars(bug_report)
            bug_id = bug_data.get('bug_id')
            
            if not bug_id:
                logger.error("bug_id 不能为空")
                return False
                
            logger.info(f"使用提供的 bug_id: {bug_id}")

            # 先添加或更新
            exists = self.db.bug_id_exists(bug_id)
            if exists:
                logger.info(f"正在更新已存在的bug报告: {bug_id}")
                success = self.db.update_bug_report(bug_id, bug_data)
            else:
                logger.info(f"正在添加新的bug报告: {bug_id}")
                success = self.db.add_bug_report(bug_id, bug_data)

            if not success:
                logger.error("保存bug报告到数据库失败")
                return False

            # 获取数据库id
            bug_report = self.db.get_bug_report(bug_id)
            if not bug_report:
                logger.error("无法获取bug报告")
                return False
            db_id = bug_report['id']

            logger.info(f"使用数据库id: {db_id}")

            # 合并测试相关字段的向量
            if "test_steps_vector" in vectors or "expected_result_vector" in vectors or "actual_result_vector" in vectors:
                test_info = {
                    "test_steps": bug_report.get("test_steps", ""),
                    "expected_result": bug_report.get("expected_result", ""),
                    "actual_result": bug_report.get("actual_result", "")
                }
                vectors["test_info_vector"] = next(
                    (vectors[k] for k in ["test_steps_vector", "expected_result_vector", "actual_result_vector"] 
                    if k in vectors and vectors[k] is not None),
                    None
                )

            index_definitions = [
                ("summary", "summary_vector"),
                ("code", "code_vector"),
                ("test_info", "test_info_vector"),
                ("log_info", "log_info_vector"),
                ("environment", "environment_vector"),
            ]

            new_indices: Dict[str, AnnoyIndex] = {}
            success = True

            # 为每个索引类型创建新实例
            for index_name, vector_key in index_definitions:
                logger.debug(f"处理索引: {index_name}")
                new_index = AnnoyIndex(self.vector_dim, self.index_type)
                new_indices[index_name] = new_index

                # 加载现有索引数据
                old_index_path = self._get_index_path(index_name)
                if old_index_path.exists():
                    try:
                        old_index = AnnoyIndex(self.vector_dim, self.index_type)
                        old_index.load(str(old_index_path))
                        # 复制现有向量
                        for item_id in range(old_index.get_n_items()):
                            try:
                                vector = old_index.get_item_vector(item_id)
                                new_index.add_item(item_id, vector)
                            except Exception as e:
                                logger.warning(f"Index {index_name}: 复制向量 ID {item_id} 失败: {e}")
                        old_index.unload()
                    except Exception as e:
                        logger.warning(f"加载旧索引 {index_name} 失败: {e}")

                # 添加新项目的向量
                if vector_key in vectors and vectors[vector_key] is not None:
                    try:
                        new_index.add_item(db_id, vectors[vector_key])
                    except Exception as e_add_new:
                        logger.error(f"Index {index_name}: 添加新项目 ID {db_id} 时出错: {e_add_new}")
                        success = False
                        break
                else:
                    logger.debug(f"Index {index_name}: 没有为新项目提供向量 (key: {vector_key})。")

            if not success:
                logger.error("由于添加新向量时出错，中止添加操作。")
                return False

            # 更新内存中的索引实例
            self.summary_index = new_indices.get("summary")
            self.code_index = new_indices.get("code")
            self.test_info_index = new_indices.get("test_info")
            self.log_info_index = new_indices.get("log_info")
            self.environment_index = new_indices.get("environment")

            # 保存索引
            self._save_indices()

            # 记录性能指标
            end_time = time.time()
            logger.info(f"添加 bug report 完成，耗时: {end_time - start_time:.3f}秒")
            return True

        except Exception as e:
            logger.error(f"添加 bug 报告失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False

    def _keyword_search(self, query_text: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """使用关键词匹配进行搜索
        
        Args:
            query_text: 查询文本
            n_results: 返回结果数量
            
        Returns:
            List[Dict[str, Any]]: 匹配的bug报告列表
        """
        try:
            # 直接使用数据库的关键词搜索功能
            return self.db.keyword_search(query_text, n_results)
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return []

    def search(self, query_vectors: Dict[str, Any], query_text: str = "", n_results: int = 10, weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """搜索相似的 bug 报告，当向量检索结果相似度低于阈值时使用关键词检索兜底"""
        start_time = time.time()
        try:
            # 执行向量检索
            vector_results = self._vector_search(query_vectors, n_results, weights)
            
            # 检查向量检索结果的相似度
            low_similarity = all(
                result.get('distance', float('inf')) > self.similarity_threshold 
                for result in vector_results
            )

            similarity_distances = [result.get('distance', float('inf')) for result in vector_results]
            logger.info(f"向量检索结果的相似度: {similarity_distances}")
            logger.info(f"相似度阈值: {self.similarity_threshold}")
            
            # 如果有查询文本且向量检索结果相似度都很低，使用关键词检索
            if low_similarity and query_text:
                logger.warning("向量检索结果相似度较低，启用关键词检索兜底")
                keyword_results = self._keyword_search(query_text, n_results)
                
                if keyword_results:
                    logger.info(f"关键词检索找到 {len(keyword_results)} 个结果")
                    return keyword_results
            
            return vector_results

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            end_time = time.time()
            logger.error(f"搜索失败，耗时: {end_time - start_time:.3f}秒")
            return []

    def _vector_search(self, query_vectors: Dict[str, Any], n_results: int = 10, weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """执行向量检索"""
        try:
            # 设置默认权重
            if weights is None:
                weights = {
                    "summary": 0.2,           # 摘要权重
                    "code": 0.25,             # 代码权重
                    "test_info": 0.15,        # 测试信息权重
                    "log_info": 0.3,          # 日志权重
                    "environment": 0.1        # 环境权重
                }

            logger.debug(f"搜索权重: {weights}")

            # 对每个向量进行搜索
            all_results: Dict[int, Dict[str, float]] = {}
            
            for vector_key, vector in query_vectors.items():
                if vector is None:
                    continue
                    
                # 获取对应的索引名称
                index_name = vector_key.replace("_vector", "")
                
                # 使用缓存进行搜索
                results = self._cached_search(index_name, tuple(vector), n_results * 10)
                
                # 应用权重
                weight = weights.get(index_name, 0.0)
                for db_id, distance in results.items():
                    if db_id not in all_results:
                        all_results[db_id] = {"raw_distance": 0.0, "weight": 0.0}
                    all_results[db_id]["raw_distance"] += distance
                    all_results[db_id]["weight"] += weight

            # 计算加权距离
            weighted_results = []
            for db_id, data in all_results.items():
                if data["weight"] > 0:
                    weighted_distance = data["raw_distance"] / data["weight"]
                    weighted_results.append((db_id, weighted_distance))

            # 按距离排序
            weighted_results.sort(key=lambda x: x[1])
            
            # 获取前N个结果
            top_results = weighted_results[:n_results]
            
            # 获取完整的bug报告信息
            final_results = []
            for db_id, distance in top_results:
                bug_report = self.db.get_bug_report_by_id(db_id)
                if bug_report:
                    bug_report["distance"] = distance
                    final_results.append(bug_report)

            return final_results

        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return []

    def _load_indices_for_read(self):
        """加载所有索引文件用于读取（查询）"""
        logger.info("开始加载现有索引数据（用于读取）...")
        loaded_indices = self._load_all_indices(for_read=True)
        
        # 更新类实例的索引属性
        self.summary_index = loaded_indices.get("summary")
        self.code_index = loaded_indices.get("code")
        self.test_info_index = loaded_indices.get("test_info")
        self.log_info_index = loaded_indices.get("log_info")
        self.environment_index = loaded_indices.get("environment")
        
        logger.info("索引加载（用于读取）完成。")

    def _load_all_indices(self, for_read: bool = True):
        """
        统一加载所有索引的函数
        
        Args:
            for_read (bool): 是否以只读模式加载索引
            
        Returns:
            Dict[str, Optional[AnnoyIndex]]: 加载的索引字典
        """
        index_names = ["summary", "code", "test_info", "log_info", "environment"]
        loaded_indices = {}
        
        for name in index_names:
            try:
                loaded_index = self._create_or_load_index(name, for_read)
                loaded_indices[name] = loaded_index
                if loaded_index:
                    logger.info(f"成功加载索引 {name}，包含 {loaded_index.get_n_items()} 个项目")
                else:
                    logger.warning(f"索引 {name} 加载失败或为空")
            except Exception as e:
                logger.error(f"加载索引 {name} 时发生错误: {str(e)}")
                loaded_indices[name] = None
                
        return loaded_indices
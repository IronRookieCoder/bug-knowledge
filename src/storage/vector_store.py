import logging
import json
import time
import traceback
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import tempfile

import numpy as np
from annoy import AnnoyIndex
from src.models.bug_models import BugReport

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, data_dir: str = "data/annoy", vector_dim: int = 384, index_type: str = "angular", n_trees: int = 10):
        self.data_dir = Path(data_dir)
        self.vector_dim = vector_dim
        self.index_type = index_type
        self.n_trees = n_trees  # 添加树的数量参数

        # 创建数据目录
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "temp").mkdir(exist_ok=True)

        # 初始化索引属性为 None
        self.summary_index: Optional[AnnoyIndex] = None
        self.code_index: Optional[AnnoyIndex] = None
        self.test_steps_index: Optional[AnnoyIndex] = None
        self.expected_result_index: Optional[AnnoyIndex] = None
        self.actual_result_index: Optional[AnnoyIndex] = None
        self.log_info_index: Optional[AnnoyIndex] = None
        self.environment_index: Optional[AnnoyIndex] = None

        # 初始化元数据
        self.metadata: Dict[str, Any] = {
            "bugs": {},
            "next_id": 0
        }

        # 加载元数据和索引（用于查询，add会强制重新加载和构建）
        self._load_metadata()
        self._load_indices_for_read()  # Load indices initially for potential querying

    def _load_metadata(self):
        """仅加载元数据"""
        metadata_path = self.data_dir / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"成功加载元数据，next_id: {self.metadata.get('next_id', 0)}")
            except json.JSONDecodeError:
                logger.error(f"元数据文件 {metadata_path} 格式错误，将使用默认值。")
                self.metadata = {"bugs": {}, "next_id": 0}
            except Exception as e:
                logger.error(f"加载元数据失败: {str(e)}")
                self.metadata = {"bugs": {}, "next_id": 0}
        else:
            logger.info("元数据文件不存在，将使用默认值。")
            self.metadata = {"bugs": {}, "next_id": 0}

    def _get_index_path(self, name: str) -> Path:
        """获取索引文件的完整路径"""
        return self.data_dir / f"{name}.ann"

    def _load_single_index_for_read(self, name: str) -> Optional[AnnoyIndex]:
        """加载单个索引文件用于读取（查询）"""
        index_path = self._get_index_path(name)
        if index_path.exists():
            try:
                index = AnnoyIndex(self.vector_dim, self.index_type)
                index.load(str(index_path))
                # index.get_n_items() # Ensure it loaded correctly, might raise error on corrupt file
                logger.info(f"成功加载只读索引: {name}, 包含 {index.get_n_items()} 个项目")
                return index
            except Exception as e:
                logger.error(f"加载只读索引 {name} 失败: {str(e)}. 文件可能已损坏或与维度/类型不匹配。")
                # Optionally: attempt to delete or backup the corrupted file
                # backup_corrupted_index(index_path)
                return None
        else:
            logger.info(f"只读索引文件 {name}.ann 不存在。")
            return None

    def _load_all_indices(self, for_read: bool = True):
        """
        统一加载所有索引的函数
        
        Args:
            for_read (bool): 是否以只读模式加载索引
            
        Returns:
            Dict[str, Optional[AnnoyIndex]]: 加载的索引字典
        """
        index_names = ["summary", "code", "test_steps", "expected_result", "actual_result", "log_info", "environment"]
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

    def _load_indices_for_read(self):
        """加载所有索引文件用于读取（查询）"""
        logger.info("开始加载现有索引数据（用于读取）...")
        loaded_indices = self._load_all_indices(for_read=True)
        
        # 更新类实例的索引属性
        self.summary_index = loaded_indices.get("summary")
        self.code_index = loaded_indices.get("code")
        self.test_steps_index = loaded_indices.get("test_steps")
        self.expected_result_index = loaded_indices.get("expected_result")
        self.actual_result_index = loaded_indices.get("actual_result")
        self.log_info_index = loaded_indices.get("log_info")
        self.environment_index = loaded_indices.get("environment")
        
        logger.info("索引加载（用于读取）完成。")

    # 在 VectorStore 类中添加以下方法
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
        """
        构建、保存、卸载并重新加载单个索引。
        返回重新加载后的索引对象，如果失败则返回 None。
        """
        if index is None:
            logger.warning(f"索引 {name} 实例为 None，无法构建或保存。")
            return None

        num_items = index.get_n_items()
        final_path = self._get_index_path(name)

        if num_items <= 0:
            logger.info(f"索引 {name} 为空 (包含 {num_items} 个项目)，跳过构建和保存。")
            if final_path.exists():
                try:
                    final_path.unlink()
                    logger.info(f"删除了空的旧索引文件: {final_path}")
                except OSError as e:
                    logger.warning(f"无法删除空的旧索引文件 {final_path}: {e}")
            return None

        logger.info(f"开始构建索引 {name} (包含 {num_items} 个项目)...")
        start_build_time = time.time()
        try:
            index.build(self.n_trees, n_jobs=-1)  # 使用配置的树数量
            build_duration = time.time() - start_build_time
            logger.info(f"索引 {name} 构建完成，耗时: {build_duration:.2f} 秒。")
        except Exception as e:
            logger.error(f"构建索引 {name} 失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None

        logger.info(f"开始保存索引 {name}...")
        start_save_time = time.time()

        temp_dir = self.data_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        # 使用 tempfile 创建临时文件
        with tempfile.NamedTemporaryFile(dir=temp_dir, suffix='.ann.tmp', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.close()

        reloaded_index: Optional[AnnoyIndex] = None
        try:
            # 1. 保存到临时文件
            index.save(str(temp_path))
            save_duration = time.time() - start_save_time
            logger.info(f"索引 {name} 已保存到临时文件 {temp_path}，耗时: {save_duration:.2f} 秒。")

            # 2. 显式卸载以释放文件句柄
            index.unload()
            logger.info(f"索引 {name} 已从内存卸载以释放文件句柄。")

            # 3. 原子替换最终文件
            try:
                temp_path.replace(final_path)
                logger.info(f"成功将临时索引替换到最终位置: {final_path}")
            except OSError as replace_e:
                logger.error(f"替换索引文件失败，尝试使用 shutil.move: {replace_e}")
                temp_path.replace(final_path)
                logger.info(f"通过 shutil.move 成功替换索引文件: {final_path}")

            # 4. 重新加载索引
            try:
                logger.info(f"尝试从 {final_path} 重新加载索引 {name}...")
                reloaded_index = AnnoyIndex(self.vector_dim, self.index_type)
                reloaded_index.load(str(final_path))
                logger.info(f"索引 {name} 重新加载成功，包含 {reloaded_index.get_n_items()} 个项目。")
            except Exception as reload_e:
                logger.error(f"重新加载索引 {name} 失败: {reload_e}")
                reloaded_index = None

            return reloaded_index

        except Exception as e:
            logger.error(f"保存、替换或重新加载索引 {name} 过程中失败: {str(e)}")
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
        """保存索引和元数据，并更新内存中的索引实例为重新加载后的版本"""
        logger.info("开始保存索引和元数据...")
        try:
            # --- 保存元数据 ---
            metadata_copy = {
                "bugs": {},
                "next_id": self.metadata["next_id"]
            }
            
            # 改进序列化处理
            for bug_id, bug_data in self.metadata["bugs"].items():
                if isinstance(bug_data, dict):
                    metadata_copy["bugs"][bug_id] = bug_data
                elif hasattr(bug_data, "dict"):  # 处理 Pydantic 模型
                    metadata_copy["bugs"][bug_id] = bug_data.dict()
                elif hasattr(bug_data, "__dict__"):  # 处理普通对象
                    metadata_copy["bugs"][bug_id] = {
                        k: v for k, v in bug_data.__dict__.items()
                        if not k.startswith('_')  # 排除私有属性
                    }
                else:
                    logger.warning(f"无法序列化的 bug_data 类型: {type(bug_data)}")
                    continue

            metadata_path = self.data_dir / "metadata.json"
            temp_metadata_path = self.data_dir / "temp" / f"metadata_{int(time.time())}.json.tmp"

            with open(temp_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_copy, f, ensure_ascii=False, indent=2)

            try:
                temp_metadata_path.replace(metadata_path)
                logger.info("元数据保存成功。")
            except OSError as e:
                logger.error(f"原子替换元数据文件失败: {e}")
                raise

            # --- 构建、保存、卸载、重新加载索引 ---
            indices_to_process = {
                "summary": self.summary_index,
                "test_steps": self.test_steps_index,
                "expected_result": self.expected_result_index,
                "actual_result": self.actual_result_index,
                "code": self.code_index,
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
            self.test_steps_index = new_loaded_indices.get("test_steps")
            self.expected_result_index = new_loaded_indices.get("expected_result")
            self.actual_result_index = new_loaded_indices.get("actual_result")
            self.code_index = new_loaded_indices.get("code")
            self.log_info_index = new_loaded_indices.get("log_info")
            self.environment_index = new_loaded_indices.get("environment")
            
            logger.info("内存中的索引实例已更新为重新加载后的版本。")
            logger.info("所有索引处理和元数据保存完成。")

        except Exception as e:
            logger.error(f"保存索引和元数据过程中发生顶层错误: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise  # 重新抛出异常，让调用者知道保存失败

    def add_bug_report(self, bug_report: Any, vectors: Dict[str, Any]): # Changed BugReport type hint
        """
        添加单个bug报告及其向量到索引。
        (逻辑基本不变，依赖 _save_indices 更新内存状态)
        """
        logger.info(f"开始添加 bug report...") # Simplified log

        self._load_metadata()
        new_idx = self.metadata["next_id"]
        logger.info(f"新项目将使用索引 ID: {new_idx}")

        index_definitions = [
            ("summary", "summary_vector"),
            ("code", "code_vector"),
            ("test_steps", "test_steps_vector"),
            ("expected_result", "expected_result_vector"),
            ("actual_result", "actual_result_vector"),
            ("log_info", "log_info_vector"),
            ("environment", "environment_vector"),
        ]

        new_indices: Dict[str, AnnoyIndex] = {}
        success = True

        try:
            # --- 3. 为每个索引类型加载旧向量并添加到新实例 ---
            for index_name, vector_key in index_definitions:
                logger.debug(f"处理索引: {index_name}")
                new_index = AnnoyIndex(self.vector_dim, self.index_type)
                new_indices[index_name] = new_index
                old_index_path = self._get_index_path(index_name)
                old_index = None
                if old_index_path.exists():
                    try:
                        old_index = AnnoyIndex(self.vector_dim, self.index_type)
                        old_index.load(str(old_index_path))
                    except Exception as e:
                        logger.warning(f"加载旧索引 {index_name} ({old_index_path}) 失败: {e}. 将只添加新项目。")

                if old_index:
                    logger.debug(f"从旧索引 {index_name} 添加项目...")
                    # Assuming IDs are 0 to new_idx - 1
                    for item_id in range(new_idx):
                        try:
                            vector = old_index.get_item_vector(item_id)
                            new_index.add_item(item_id, vector)
                        except Exception: # More specific exception?
                           # Log if an expected item is missing
                           if str(item_id) in self.metadata.get("bugs", {}):
                                logger.warning(f"Index {index_name}: 旧索引中未找到预期的项目 ID {item_id}")
                    old_index.unload() # Unload temporary old index

                # --- 4. 添加新项目的向量 ---
                if vector_key in vectors and vectors[vector_key] is not None:
                    try:
                        new_index.add_item(new_idx, vectors[vector_key])
                    except Exception as e_add_new:
                        logger.error(f"Index {index_name}: 添加新项目 ID {new_idx} 时出错: {e_add_new}")
                        success = False
                        break
                else:
                     logger.debug(f"Index {index_name}: 没有为新项目提供向量 (key: {vector_key})。")


            if not success:
                 logger.error("由于添加新向量时出错，中止添加操作。")
                 return False

            # --- 5. 更新内存中的索引实例 (指向未保存的索引) ---
            # These instances will be processed by _save_indices
            self.summary_index = new_indices.get("summary")
            self.code_index = new_indices.get("code")
            self.test_steps_index = new_indices.get("test_steps")
            self.expected_result_index = new_indices.get("expected_result")
            self.actual_result_index = new_indices.get("actual_result")
            self.log_info_index = new_indices.get("log_info")
            self.environment_index = new_indices.get("environment")

            # --- 6. 更新元数据 ---
            logger.debug("更新元数据...")
            bug_data_to_store = bug_report if isinstance(bug_report, dict) else vars(bug_report) # Basic serialization
            self.metadata["bugs"][str(new_idx)] = bug_data_to_store
            self.metadata["next_id"] = new_idx + 1

            # --- 7. 构建、保存、卸载、重新加载所有新索引和元数据 ---
            logger.info("调用 _save_indices 来处理构建、保存和重新加载...")
            self._save_indices() # This now handles build, save, unload, reload, and updates self.*_index

            # Check if reload was successful for at least one index? Optional.
            if self.summary_index is None and self.code_index is None: # Example check
                 logger.warning("添加操作后，主要索引未能成功重新加载。搜索功能可能受限。")

            logger.info(f"Bug report (Index ID: {new_idx}) 添加过程完成。")
            return True

        except Exception as e:
            logger.error(f"添加 bug report (Index ID: {new_idx}) 失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False
            
    def search(self, query_vectors: Dict[str, Any], n_results: int = 5, weights: Optional[Dict[str, float]] = None) -> List[Dict]:
        """
        搜索相似的bug报告
        
        Args:
            query_vectors: 查询向量字典
            n_results: 返回结果数量
            weights: 各字段权重字典
            
        Returns:
            List[Dict]: 相似bug报告列表
        """
        try:
            logger.info(f"开始搜索，请求返回 {n_results} 个结果")
            
            # 使用统一的索引加载函数加载所有索引
            loaded_indices = self._load_all_indices(for_read=True)
            
            # 更新类实例的索引属性
            self.summary_index = loaded_indices.get("summary")
            self.code_index = loaded_indices.get("code")
            self.test_steps_index = loaded_indices.get("test_steps")
            self.expected_result_index = loaded_indices.get("expected_result")
            self.actual_result_index = loaded_indices.get("actual_result")
            self.log_info_index = loaded_indices.get("log_info")
            self.environment_index = loaded_indices.get("environment")
                
            # 如果没有提供权重，使用默认权重
            if weights is None:
                weights = {
                    "summary": 0.25,  # 摘要最重要
                    "code": 0.20,     # 代码相关次之
                    "test_steps": 0.15,    # 测试步骤
                    "expected_result": 0.10,  # 预期结果
                    "actual_result": 0.15,    # 实际结果
                    "log_info": 0.10,       # 日志信息
                    "environment": 0.05        # 环境信息
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
            results: Dict[int, Dict[str, Any]] = {}
            
            # 获取所有索引中的结果数量
            total_index_items = 0
            for index in loaded_indices.values():
                if index:
                    total_index_items = max(total_index_items, index.get_n_items())
            
            # 计算要请求的结果数量 - 确保足够多
            requested_results = min(max(50, n_results * 10), total_index_items) if total_index_items > 0 else max(50, n_results * 10)
            logger.info(f"预计返回 {requested_results} 个初始结果进行排序和过滤")
            
            # 对每个向量进行搜索
            vector_to_index_mapping = {
                "summary_vector": ("summary", self.summary_index),
                "code_vector": ("code", self.code_index),
                "test_steps_vector": ("test_steps", self.test_steps_index),
                "expected_result_vector": ("expected_result", self.expected_result_index),
                "actual_result_vector": ("actual_result", self.actual_result_index),
                "log_info_vector": ("log_info", self.log_info_index),
                "environment_vector": ("environment", self.environment_index)
            }
            
            # 收集所有索引的搜索结果
            for vector_key, (index_name, index) in vector_to_index_mapping.items():
                if vector_key in query_vectors and index is not None:
                    try:
                        index_results = self._search_index(index, query_vectors[vector_key], 
                                                        requested_results, weights.get(index_name, 0))
                        # 合并结果，累加加权距离
                        for idx, result in index_results.items():
                            if idx not in results:
                                results[idx] = {
                                    "weighted_sum": 0.0,
                                    "weight_sum": 0.0,
                                    "raw_distances": {}
                                }
                            results[idx]["weighted_sum"] += result["raw_distance"] * result["weight"]
                            results[idx]["weight_sum"] += result["weight"]
                            results[idx]["raw_distances"][index_name] = result["raw_distance"]
                    except Exception as e:
                        logger.error(f"搜索索引 {index_name} 时出错: {str(e)}")
                        continue
            
            # 如果没有结果，返回空列表
            if not results:
                logger.info("搜索没有找到任何结果")
                return []
            
            logger.info(f"合并索引搜索结果: 找到 {len(results)} 个唯一ID")
            
            # 计算每个结果的加权平均距离
            for idx in results:
                if results[idx]["weight_sum"] > 0:
                    results[idx]["distance"] = results[idx]["weighted_sum"] / results[idx]["weight_sum"]
                else:
                    results[idx]["distance"] = float('inf')
            
            # 对结果进行排序 - 按加权平均距离升序排序（越小越相似）
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
                    bug_data["raw_distances"] = score["raw_distances"]  # 添加原始距离信息
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
                logger.info(f"最终结果 #{i}: ID={result['bug_id']}, 距离={result['distance']:.4f}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return []
    
    def _search_index(self, index: AnnoyIndex, vector: List[float], n_results: int, weight: float) -> Dict[int, Dict[str, float]]:
        """在单个索引中搜索
        
        Args:
            index: Annoy索引实例
            vector: 查询向量
            n_results: 请求的结果数量
            weight: 该索引的权重
            
        Returns:
            Dict[int, Dict[str, float]]: 键为ID，值为包含原始距离和权重的字典
        """
        if index is None or index.get_n_items() == 0 or weight == 0:
            logger.warning(f"索引为空或权重为0，无法搜索。索引: {index}, 项目数: {index.get_n_items() if index else 0}, 权重: {weight}")
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
            # 使用较小的search_k值以提高性能，同时保持合理的召回率
            ids, distances = index.get_nns_by_vector(
                vector, 
                search_n_results, 
                include_distances=True, 
                search_k=100  # 使用较小的值以提高性能
            )
            
            # 记录找到的结果数量以及前几个ID
            logger.info(f"索引搜索结果: 找到 {len(ids)} 个匹配项")
            if ids:
                first_ids = ids[:min(5, len(ids))]
                first_distances = distances[:min(5, len(distances))]
                id_dist_pairs = [f"({i}:{d:.4f})" for i, d in zip(first_ids, first_distances)]
                logger.info(f"前5个结果 [ID:距离]: {', '.join(id_dist_pairs)}")
            
            # 返回所有结果，包含原始距离和权重，让主搜索函数处理合并策略
            results = {
                idx: {
                    "raw_distance": dist,  # 原始距离
                    "weight": weight       # 权重
                } 
                for idx, dist in zip(ids, distances)
            }
            logger.info(f"返回 {len(results)} 个匹配项的结果")
            return results
            
        except Exception as e:
            logger.error(f"搜索索引失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            logger.error(f"搜索参数: 向量长度={len(vector)}, 请求结果数={n_results}, 权重={weight}")
            return {}

    def add_bug_reports(self, bug_reports: List[Any], vectors_list: List[Dict[str, Any]]) -> bool:
        """
        批量添加多个bug报告及其向量到索引。
        
        Args:
            bug_reports: bug报告列表
            vectors_list: 对应的向量列表，每个元素是一个字典，包含各个字段的向量
            
        Returns:
            bool: 是否全部添加成功
        """
        if len(bug_reports) != len(vectors_list):
            logger.error(f"bug报告数量 ({len(bug_reports)}) 与向量列表数量 ({len(vectors_list)}) 不匹配")
            return False
            
        logger.info(f"开始批量添加 {len(bug_reports)} 个bug报告...")
        
        # 加载元数据
        self._load_metadata()
        start_idx = self.metadata["next_id"]
        
        # 创建新的索引实例
        new_indices: Dict[str, AnnoyIndex] = {
            "summary": AnnoyIndex(self.vector_dim, self.index_type),
            "code": AnnoyIndex(self.vector_dim, self.index_type),
            "test_steps": AnnoyIndex(self.vector_dim, self.index_type),
            "expected_result": AnnoyIndex(self.vector_dim, self.index_type),
            "actual_result": AnnoyIndex(self.vector_dim, self.index_type),
            "log_info": AnnoyIndex(self.vector_dim, self.index_type),
            "environment": AnnoyIndex(self.vector_dim, self.index_type)
        }
        
        # 加载现有索引数据
        for name, index in new_indices.items():
            old_index_path = self._get_index_path(name)
            if old_index_path.exists():
                try:
                    old_index = AnnoyIndex(self.vector_dim, self.index_type)
                    old_index.load(str(old_index_path))
                    # 复制现有向量
                    for item_id in range(start_idx):
                        try:
                            vector = old_index.get_item_vector(item_id)
                            index.add_item(item_id, vector)
                        except Exception as e:
                            if str(item_id) in self.metadata.get("bugs", {}):
                                logger.warning(f"Index {name}: 旧索引中未找到预期的项目 ID {item_id}: {e}")
                    old_index.unload()
                except Exception as e:
                    logger.warning(f"加载旧索引 {name} 失败: {e}")
        
        success = True
        try:
            # 添加新的bug报告和向量
            for i, (bug_report, vectors) in enumerate(zip(bug_reports, vectors_list)):
                current_idx = start_idx + i
                
                # 添加向量到各个索引
                for name, index in new_indices.items():
                    vector_key = f"{name}_vector"
                    if vector_key in vectors and vectors[vector_key] is not None:
                        try:
                            index.add_item(current_idx, vectors[vector_key])
                        except Exception as e:
                            logger.error(f"Index {name}: 添加项目 ID {current_idx} 时出错: {e}")
                            success = False
                            break
                
                if not success:
                    break
                    
                # 更新元数据
                bug_data_to_store = bug_report if isinstance(bug_report, dict) else vars(bug_report)
                self.metadata["bugs"][str(current_idx)] = bug_data_to_store
                self.metadata["next_id"] = current_idx + 1
            
            if success:
                # 更新内存中的索引实例
                self.summary_index = new_indices["summary"]
                self.code_index = new_indices["code"]
                self.test_steps_index = new_indices["test_steps"]
                self.expected_result_index = new_indices["expected_result"]
                self.actual_result_index = new_indices["actual_result"]
                self.log_info_index = new_indices["log_info"]
                self.environment_index = new_indices["environment"]
                
                # 保存所有更改
                self._save_indices()
                logger.info(f"成功批量添加 {len(bug_reports)} 个bug报告")
                return True
            else:
                logger.error("批量添加过程中出现错误，操作已中止")
                return False
                
        except Exception as e:
            logger.error(f"批量添加bug报告失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False
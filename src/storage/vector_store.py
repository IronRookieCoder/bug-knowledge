import logging
import json
import os
import time
import traceback
import shutil
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import tempfile

import numpy as np
from annoy import AnnoyIndex

# Assuming BugReport and other imports are correct
from src.models.bug_models import BugReport
# from src.features.code_features import CodeFeatureExtractor, CodeFeatures # Not used directly here

logger = logging.getLogger(__name__)

class VectorStore:
    # Or adjust its meaning. Let's assume it's for the initial load state.
    def __init__(self, data_dir: str = "data/annoy", vector_dim: int = 384, index_type: str = "angular"):
        self.data_dir = data_dir
        self.vector_dim = vector_dim
        self.index_type = index_type

        # 创建数据目录
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "temp"), exist_ok=True)

        # 初始化索引属性为 None
        self.summary_index: Optional[AnnoyIndex] = None
        self.code_index: Optional[AnnoyIndex] = None
        self.test_steps_index: Optional[AnnoyIndex] = None
        self.expected_result_index: Optional[AnnoyIndex] = None
        self.actual_result_index: Optional[AnnoyIndex] = None
        self.log_info_index: Optional[AnnoyIndex] = None
        self.environment_index: Optional[AnnoyIndex] = None

        # 初始化元数据
        self.metadata = {
            "bugs": {},
            "next_id": 0
        }

        # 加载元数据和索引（用于查询，add会强制重新加载和构建）
        self._load_metadata()
        self._load_indices_for_read() # Load indices initially for potential querying

    def _load_metadata(self):
        """仅加载元数据"""
        metadata_path = os.path.join(self.data_dir, "metadata.json")
        if os.path.exists(metadata_path):
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

    def _get_index_path(self, name: str) -> str:
        """获取索引文件的完整路径"""
        return os.path.join(self.data_dir, f"{name}.ann")

    def _load_single_index_for_read(self, name: str) -> Optional[AnnoyIndex]:
        """加载单个索引文件用于读取（查询）"""
        index_path = self._get_index_path(name)
        if os.path.exists(index_path):
            try:
                index = AnnoyIndex(self.vector_dim, self.index_type)
                index.load(index_path)
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

    def _load_indices_for_read(self):
        """加载所有索引文件用于读取（查询）"""
        logger.info("尝试加载现有索引数据（用于读取）...")
        self.summary_index = self._load_single_index_for_read("summary")
        self.code_index = self._load_single_index_for_read("code")
        self.test_steps_index = self._load_single_index_for_read("test_steps")
        self.expected_result_index = self._load_single_index_for_read("expected_result")
        self.actual_result_index = self._load_single_index_for_read("actual_result")
        self.log_info_index = self._load_single_index_for_read("log_info")
        self.environment_index = self._load_single_index_for_read("environment")
        logger.info("索引加载（用于读取）完成。")


    # _save_indices 和 _build_and_save_index 基本保持不变，但要确保 build() 被调用
    def _save_indices(self):
        """保存索引和元数据"""
        logger.info("开始保存索引和元数据...")
        try:
            # --- 保存元数据 ---
            # Create a serializable copy (BugReport objects might not be directly serializable)
            metadata_copy = {
                "bugs": {},
                "next_id": self.metadata["next_id"]
            }
            # Ensure bug data is serializable if BugReport isn't just a dict
            for bug_id, bug_data in self.metadata["bugs"].items():
                 if isinstance(bug_data, dict):
                     metadata_copy["bugs"][bug_id] = bug_data
                 elif hasattr(bug_data, 'dict'): # Handle Pydantic models
                     metadata_copy["bugs"][bug_id] = bug_data.dict()
                 else: # Fallback or raise error
                     logger.warning(f"无法序列化 bug_id {bug_id} 的元数据，类型: {type(bug_data)}")
                     # Convert to dict manually if possible, otherwise skip or error
                     try:
                         metadata_copy["bugs"][bug_id] = vars(bug_data)
                     except TypeError:
                         logger.error(f"跳过保存 bug_id {bug_id} 的元数据，无法转换为字典。")


            metadata_path = os.path.join(self.data_dir, "metadata.json")
            temp_metadata_path = os.path.join(self.data_dir, "temp", f"metadata_{int(time.time())}.json.tmp")

            with open(temp_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_copy, f, ensure_ascii=False, indent=2)

            # Atomically replace metadata file
            try:
                 # On Windows, os.replace might fail if the target exists.
                 # A common pattern is remove -> rename or use shutil.move
                 if os.path.exists(metadata_path):
                     os.remove(metadata_path)
                 os.rename(temp_metadata_path, metadata_path)
                 # On POSIX, os.replace is generally atomic
                 # os.replace(temp_metadata_path, metadata_path)
                 logger.info("元数据保存成功。")
            except OSError as e:
                 logger.error(f"原子替换元数据文件失败: {e}. 尝试 shutil.move...")
                 try:
                     shutil.move(temp_metadata_path, metadata_path)
                     logger.info("元数据通过 shutil.move 保存成功。")
                 except Exception as move_e:
                     logger.error(f"使用 shutil.move 保存元数据也失败: {move_e}")
                     # Consider keeping the temp file for recovery
                     logger.error(f"未能更新元数据文件: {metadata_path}. 临时文件位于: {temp_metadata_path}")


            # --- 构建并保存索引 ---
            # These indices should already be populated and ready for build/save
            indices_to_save = [
                (self.summary_index, "summary"),
                (self.test_steps_index, "test_steps"),
                (self.expected_result_index, "expected_result"),
                (self.actual_result_index, "actual_result"),
                (self.code_index, "code"),
                (self.log_info_index, "log_info"),
                (self.environment_index, "environment")
            ]

            for index, name in indices_to_save:
                try:
                    # Pass the index object itself to build_and_save
                    self._build_and_save_index(index, name)
                except Exception as e:
                    logger.error(f"构建或保存索引 {name} 失败: {str(e)}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    # Decide if failure is critical. Continue saving others?
                    continue

            logger.info("所有索引和元数据保存完成")

        except Exception as e:
            logger.error(f"保存索引和元数据过程中发生意外错误: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # Depending on the error, you might want to raise it
            # raise RuntimeError(f"保存索引和元数据失败: {str(e)}")

    def _build_and_save_index(self, index: Optional[AnnoyIndex], name: str) -> Optional[AnnoyIndex]:
        """
        构建、保存、卸载并重新加载单个索引。
        返回重新加载后的索引对象，如果失败则返回 None。
        """
        if index is None:
            logger.warning(f"索引 {name} 实例为 None，无法构建或保存。")
            return None # Return None if input index is None

        num_items = index.get_n_items()
        final_path = self._get_index_path(name) # Get final path early

        if num_items <= 0:
            logger.info(f"索引 {name} 为空 (包含 {num_items} 个项目)，跳过构建和保存。")
            # Delete existing file if index is now empty
            if os.path.exists(final_path):
                try:
                    os.remove(final_path)
                    logger.info(f"删除了空的旧索引文件: {final_path}")
                except OSError as e:
                    logger.warning(f"无法删除空的旧索引文件 {final_path}: {e}")
            return None # Return None for empty index, caller should handle

        logger.info(f"开始构建索引 {name} (包含 {num_items} 个项目)...")
        start_build_time = time.time()
        try:
            index.build(10, n_jobs=-1)
            build_duration = time.time() - start_build_time
            logger.info(f"索引 {name} 构建完成，耗时: {build_duration:.2f} 秒。")
        except Exception as e:
            logger.error(f"构建索引 {name} 失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None # Return None if build fails

        logger.info(f"开始保存索引 {name}...")
        start_save_time = time.time()

        temp_dir = os.path.join(self.data_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        timestamp = int(time.time() * 1000)
        temp_path = os.path.join(temp_dir, f"{name}_{timestamp}.ann.tmp")

        reloaded_index: Optional[AnnoyIndex] = None
        try:
            # 1. Save to temporary file
            index.save(temp_path)
            save_duration = time.time() - start_save_time
            logger.info(f"索引 {name} 已保存到临时文件 {temp_path}，耗时: {save_duration:.2f} 秒。")

            # 2. Explicitly unload to release file handles
            index.unload()
            logger.info(f"索引 {name} 已从内存卸载以释放文件句柄。")

            # Brief pause might still be helpful occasionally on Windows
            # time.sleep(0.05)

            # 3. Atomically replace the final file
            try:
                os.replace(temp_path, final_path)
                logger.info(f"成功将临时索引替换到最终位置: {final_path}")
            except Exception as replace_e:
                logger.error(f"替换索引文件 {temp_path} 到 {final_path} 失败: {replace_e}")
                raise RuntimeError(f"无法更新索引文件 {final_path}") from replace_e

            # --- >>> 关键步骤：重新加载索引 <<< ---
            # 4. Reload the index from the final path into a new instance
            try:
                logger.info(f"尝试从 {final_path} 重新加载索引 {name}...")
                reloaded_index = AnnoyIndex(self.vector_dim, self.index_type)
                reloaded_index.load(final_path)
                # Optional: Prefaulting can sometimes speed up the *first* query after load
                # reloaded_index.load(final_path, prefault=True)
                logger.info(f"索引 {name} 重新加载成功，包含 {reloaded_index.get_n_items()} 个项目。")
            except Exception as reload_e:
                logger.error(f"重新加载索引 {name} 从 {final_path} 失败: {reload_e}")
                # Decide how critical this is. If reload fails, the in-memory index is lost.
                reloaded_index = None # Ensure it's None if reload fails
                # Maybe raise an error here? Or just log and return None?
                # Let's log and return None for now.
            # --- >>> 结束重新加载 <<< ---

            return reloaded_index # Return the newly loaded index (or None if reload failed)

        except Exception as e:
            logger.error(f"保存、替换或重新加载索引 {name} 过程中失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"已删除失败过程中的临时索引文件: {temp_path}")
                except OSError as rm_e:
                    logger.warning(f"删除临时索引文件 {temp_path} 失败: {rm_e}")
            return None # Return None on failure


    def _save_indices(self):
        """保存索引和元数据，并更新内存中的索引实例为重新加载后的版本"""
        logger.info("开始保存索引和元数据...")
        try:
            # --- 保存元数据 (保持不变) ---
            # ... (元数据保存逻辑) ...
            metadata_copy = {
                "bugs": {},
                "next_id": self.metadata["next_id"]
            }
            for bug_id, bug_data in self.metadata["bugs"].items():
                 # Basic serialization, improve if needed
                 metadata_copy["bugs"][bug_id] = bug_data if isinstance(bug_data, dict) else vars(bug_data)

            metadata_path = os.path.join(self.data_dir, "metadata.json")
            temp_metadata_path = os.path.join(self.data_dir, "temp", f"metadata_{int(time.time())}.json.tmp")

            with open(temp_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_copy, f, ensure_ascii=False, indent=2)

            try:
                 os.replace(temp_metadata_path, metadata_path)
                 logger.info("元数据保存成功。")
            except OSError as e:
                 logger.error(f"原子替换元数据文件失败: {e}. 尝试 shutil.move...")
                 try:
                     shutil.move(temp_metadata_path, metadata_path)
                     logger.info("元数据通过 shutil.move 保存成功。")
                 except Exception as move_e:
                     logger.error(f"使用 shutil.move 保存元数据也失败: {move_e}")


            # --- 构建、保存、卸载并重新加载索引 ---
            indices_to_process = { # Use a dict for easier update
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
                    # Call build/save/unload/reload function
                    reloaded_instance = self._build_and_save_index(index_instance, name)
                    # Store the result (which is the reloaded index or None)
                    new_loaded_indices[name] = reloaded_instance
                except Exception as e:
                    logger.error(f"处理索引 {name} 时发生意外错误: {str(e)}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    new_loaded_indices[name] = None # Ensure it's None on error

            # --- >>> 关键：更新类实例的索引属性 <<< ---
            self.summary_index = new_loaded_indices.get("summary")
            self.test_steps_index = new_loaded_indices.get("test_steps")
            self.expected_result_index = new_loaded_indices.get("expected_result")
            self.actual_result_index = new_loaded_indices.get("actual_result")
            self.code_index = new_loaded_indices.get("code")
            self.log_info_index = new_loaded_indices.get("log_info")
            self.environment_index = new_loaded_indices.get("environment")
            logger.info("内存中的索引实例已更新为重新加载后的版本。")
            # --- >>> 结束更新 <<< ---

            logger.info("所有索引处理和元数据保存完成。")

        except Exception as e:
            logger.error(f"保存索引和元数据过程中发生顶层错误: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")


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
                if os.path.exists(old_index_path):
                    try:
                        old_index = AnnoyIndex(self.vector_dim, self.index_type)
                        old_index.load(old_index_path)
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
            
    def _load_existing_data(self):
        """从现有索引文件加载已有数据"""
        logger.info("尝试加载现有索引数据")
        try:
            # 加载元数据
            metadata_path = os.path.join(self.data_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            
            # 加载所有索引
            indices = [
                (self.summary_index, "summary"),
                (self.test_steps_index, "test_steps"),
                (self.expected_result_index, "expected_result"),
                (self.actual_result_index, "actual_result"),
                (self.code_index, "code"),
                (self.log_info_index, "log_info"),
                (self.environment_index, "environment")
            ]
            
            for index, name in indices:
                index_path = os.path.join(self.data_dir, f"{name}.ann")
                if os.path.exists(index_path):
                    try:
                        index.load(index_path)
                        logger.info(f"成功加载索引: {name}, 包含 {index.get_n_items()} 个项目")
                    except Exception as e:
                        logger.warning(f"加载索引 {name} 失败: {str(e)}")
                        # 如果加载失败，创建新的空索引
                        index = AnnoyIndex(self.vector_dim, self.index_type)
                        index.build(10)
                        logger.info(f"创建新的空索引: {name}")
        except Exception as e:
            logger.error(f"加载现有数据失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 如果加载失败，创建新的空索引
            self._create_new_indices()
    
    def search(self, query_vectors: Dict[str, Any], n_results: int = 5, weights: Dict[str, float] = None) -> List[Dict]:
        """搜索相似的bug报告"""
        try:
            logger.info(f"开始搜索，请求返回 {n_results} 个结果")
            
            # 如果索引为None，尝试加载
            if self.summary_index is None:
                self.summary_index = self._create_or_load_index("summary", True)
            if self.code_index is None:
                self.code_index = self._create_or_load_index("code", True)
            if self.test_steps_index is None:
                self.test_steps_index = self._create_or_load_index("test_steps", True)
            if self.expected_result_index is None:
                self.expected_result_index = self._create_or_load_index("expected_result", True)
            if self.actual_result_index is None:
                self.actual_result_index = self._create_or_load_index("actual_result", True)
            if self.log_info_index is None:
                self.log_info_index = self._create_or_load_index("log_info", True)
            if self.environment_index is None:
                self.environment_index = self._create_or_load_index("environment", True)
                
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
            results = {}
            
            # 获取所有索引中的结果数量
            total_index_items = 0
            if self.summary_index:
                total_index_items = max(total_index_items, self.summary_index.get_n_items())
            
            # 计算要请求的结果数量 - 确保足够多
            requested_results = min(max(50, n_results * 10), total_index_items) if total_index_items > 0 else max(50, n_results * 10)
            logger.info(f"预计返回 {requested_results} 个初始结果进行排序和过滤")
            
            # 对每个向量进行搜索
            if "summary_vector" in query_vectors and self.summary_index is not None:
                summary_results = self._search_index(self.summary_index, query_vectors["summary_vector"], 
                                               requested_results, weights.get("summary", 0))
                results.update(summary_results)
            
            if "code_vector" in query_vectors and self.code_index is not None:
                code_results = self._search_index(self.code_index, query_vectors["code_vector"], 
                                               requested_results, weights.get("code", 0))
                results.update(code_results)
            
            if "test_steps_vector" in query_vectors and self.test_steps_index is not None:
                test_steps_results = self._search_index(self.test_steps_index, query_vectors["test_steps_vector"], 
                                               requested_results, weights.get("test_steps", 0))
                results.update(test_steps_results)
            
            if "expected_result_vector" in query_vectors and self.expected_result_index is not None:
                expected_results = self._search_index(self.expected_result_index, query_vectors["expected_result_vector"], 
                                               requested_results, weights.get("expected_result", 0))
                results.update(expected_results)
            
            if "actual_result_vector" in query_vectors and self.actual_result_index is not None:
                actual_results = self._search_index(self.actual_result_index, query_vectors["actual_result_vector"], 
                                               requested_results, weights.get("actual_result", 0))
                results.update(actual_results)
            
            if "log_info_vector" in query_vectors and self.log_info_index is not None:
                log_results = self._search_index(self.log_info_index, query_vectors["log_info_vector"], 
                                               requested_results, weights.get("log_info", 0))
                results.update(log_results)
            
            if "environment_vector" in query_vectors and self.environment_index is not None:
                environment_results = self._search_index(self.environment_index, query_vectors["environment_vector"], 
                                               requested_results, weights.get("environment", 0))
                results.update(environment_results)
            
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
                logger.info(f"最终结果 #{i}: ID={result['bug_id']}, 距离={result['distance']:.4f}")
            
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
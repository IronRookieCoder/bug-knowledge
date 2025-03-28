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

    # _build_and_save_index remains largely the same, ensure build() is called correctly
    def _build_and_save_index(self, index: Optional[AnnoyIndex], name: str):
        """构建并保存单个索引"""
        if index is None:
            logger.warning(f"索引 {name} 实例为 None，无法构建或保存。")
            return

        # Check item count before building
        num_items = index.get_n_items()
        if num_items <= 0:
            logger.info(f"索引 {name} 为空 (包含 {num_items} 个项目)，跳过构建和保存。")
            # Optionally delete the existing .ann file if it exists and the index is now empty
            index_path = self._get_index_path(name)
            if os.path.exists(index_path):
                try:
                    os.remove(index_path)
                    logger.info(f"删除了空的旧索引文件: {index_path}")
                except OSError as e:
                    logger.warning(f"无法删除空的旧索引文件 {index_path}: {e}")
            return

        logger.info(f"开始构建索引 {name} (包含 {num_items} 个项目)...")
        start_build_time = time.time()
        try:
            # --- 构建索引 ---
            # num_trees: 10 is a starting point, might need tuning
            # Use -1 for n_jobs to use all available CPU cores, potentially speeding up build
            index.build(10, n_jobs=-1)
            build_duration = time.time() - start_build_time
            logger.info(f"索引 {name} 构建完成，耗时: {build_duration:.2f} 秒。")

        except Exception as e:
            logger.error(f"构建索引 {name} 失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return # Do not proceed to save if build failed

        logger.info(f"开始保存索引 {name}...")
        start_save_time = time.time()

        # --- 保存索引 (使用临时文件和原子替换) ---
        temp_dir = os.path.join(self.data_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True) # Ensure temp dir exists

        timestamp = int(time.time() * 1000) # Higher resolution timestamp
        temp_path = os.path.join(temp_dir, f"{name}_{timestamp}.ann.tmp")
        final_path = self._get_index_path(name)
        # backup_path = os.path.join(self.data_dir, f"{name}.ann.bak") # Backup logic seems complex and maybe error-prone, simplify first

        try:
            # Save to temporary file first
            index.save(temp_path)
            save_duration = time.time() - start_save_time
            logger.info(f"索引 {name} 已保存到临时文件 {temp_path}，耗时: {save_duration:.2f} 秒。")

            # Atomically replace the final file with the temporary file
            # Use shutil.move for better cross-platform compatibility than os.replace/rename chain
            try:
                shutil.move(temp_path, final_path)
                logger.info(f"成功将临时索引移动到最终位置: {final_path}")
            except Exception as move_e:
                logger.error(f"移动索引文件 {temp_path} 到 {final_path} 失败: {move_e}")
                # Attempt cleanup of temp file if move fails?
                try:
                    os.remove(temp_path)
                except OSError:
                    pass # Ignore cleanup error
                raise RuntimeError(f"无法更新索引文件 {final_path}") from move_e

            # Unload the index from memory after saving? Optional, depends on usage pattern.
            # index.unload()
            # logger.info(f"索引 {name} 已从内存卸载。")

        except Exception as e:
            logger.error(f"保存索引 {name} 到文件失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"已删除失败保存的临时索引文件: {temp_path}")
                except OSError as rm_e:
                    logger.warning(f"删除临时索引文件 {temp_path} 失败: {rm_e}")
            # Re-raise or handle error appropriately
            raise


    def add_bug_report(self, bug_report: BugReport, vectors: Dict[str, Any]):
        """
        添加单个bug报告及其向量到索引。
        这将加载现有索引，将所有旧向量和新向量添加到一个新的内存索引中，
        然后构建并保存这个新索引，覆盖旧文件。
        """
        logger.info(f"开始添加 bug report (ID: {bug_report.bug_id})...")

        # --- 1. 准备新数据和ID ---
        self._load_metadata() # Ensure metadata is up-to-date before getting next_id
        new_idx = self.metadata["next_id"]
        logger.info(f"新项目将使用索引 ID: {new_idx}")

        # --- 2. 定义所有索引类型 ---
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
        old_indices: Dict[str, Optional[AnnoyIndex]] = {}
        success = True

        try:
            # --- 3. 为每个索引类型加载旧向量并添加到新实例 ---
            for index_name, vector_key in index_definitions:
                logger.debug(f"处理索引: {index_name}")

                # Create a new empty index instance for this type
                new_index = AnnoyIndex(self.vector_dim, self.index_type)
                new_indices[index_name] = new_index

                # Try to load the old index *temporarily* to get old vectors
                old_index_path = self._get_index_path(index_name)
                old_index = None
                if os.path.exists(old_index_path):
                    try:
                        old_index = AnnoyIndex(self.vector_dim, self.index_type)
                        old_index.load(old_index_path)
                        logger.debug(f"临时加载旧索引 {index_name} 成功, {old_index.get_n_items()} items.")
                        old_indices[index_name] = old_index # Store for potential later use? Unlikely needed.
                    except Exception as e:
                        logger.warning(f"加载旧索引 {index_name} ({old_index_path}) 失败: {e}. 将只添加新项目。")
                        old_indices[index_name] = None # Ensure it's None if load fails
                        # Consider if this failure should halt the process
                else:
                    logger.debug(f"旧索引文件 {old_index_path} 不存在。")
                    old_indices[index_name] = None

                # Add old items to the new index instance
                if old_index:
                    num_old_items = old_index.get_n_items()
                    # Iterate based on expected IDs in metadata, safer than relying on get_n_items range
                    added_count = 0
                    skipped_count = 0
                    existing_ids = set(map(int, self.metadata.get("bugs", {}).keys()))

                    # Annoy expects contiguous IDs from 0 up to n-1 usually.
                    # If metadata IDs are sparse, this needs careful handling.
                    # Assuming IDs are 0 to next_id - 1 for now.
                    for item_id in range(new_idx): # Iterate up to the ID *before* the new one
                        # Double check if this ID really existed according to metadata? Optional.
                        # if str(item_id) not in self.metadata['bugs']:
                        #     logger.warning(f"Index {index_name}: ID {item_id} not in metadata, skipping.")
                        #     continue

                        # Check if item exists in the loaded old_index
                        # Annoy doesn't have a direct 'has_item' check. Rely on get_item_vector + try/except.
                        try:
                            vector = old_index.get_item_vector(item_id)
                            new_index.add_item(item_id, vector)
                            added_count += 1
                        except IndexError:
                            # This might happen if index file and metadata are out of sync,
                            # or if IDs are not contiguous 0..n-1 in the .ann file.
                            logger.warning(f"Index {index_name}: 旧索引中未找到项目 ID {item_id} (可能已删除或ID不连续)")
                            skipped_count += 1
                        except Exception as e_get:
                            logger.error(f"Index {index_name}: 获取旧项目 ID {item_id} 的向量时出错: {e_get}")
                            skipped_count += 1
                            # Decide if this error is critical

                    logger.debug(f"Index {index_name}: 从旧索引添加了 {added_count} 个项目到新实例，跳过 {skipped_count} 个。")
                    # Unload the temporary old index to free memory
                    old_index.unload()
                    logger.debug(f"临时旧索引 {index_name} 已卸载。")

                # --- 4. 添加新项目的向量 ---
                if vector_key in vectors and vectors[vector_key] is not None:
                    try:
                        new_index.add_item(new_idx, vectors[vector_key])
                        logger.debug(f"Index {index_name}: 成功添加新项目 ID {new_idx}。")
                    except Exception as e_add_new:
                        logger.error(f"Index {index_name}: 添加新项目 ID {new_idx} 到新实例时出错: {e_add_new}")
                        success = False
                        break # Stop processing further indices if adding the new item fails
                else:
                    logger.debug(f"Index {index_name}: 没有为新项目提供向量 (key: {vector_key})，跳过添加。")

            # --- End loop for index_definitions ---

            if not success:
                 logger.error("由于添加新向量时出错，中止添加操作。")
                 return False

            # --- 5. 更新内存中的索引实例 ---
            logger.debug("使用新构建的索引更新内存中的实例...")
            self.summary_index = new_indices.get("summary")
            self.code_index = new_indices.get("code")
            self.test_steps_index = new_indices.get("test_steps")
            self.expected_result_index = new_indices.get("expected_result")
            self.actual_result_index = new_indices.get("actual_result")
            self.log_info_index = new_indices.get("log_info")
            self.environment_index = new_indices.get("environment")

            # --- 6. 更新元数据 ---
            logger.debug("更新元数据...")
            # Ensure bug_report data is stored correctly (e.g., as dict)
            bug_data_to_store = {}
            if isinstance(bug_report, dict):
                bug_data_to_store = bug_report
            elif hasattr(bug_report, 'dict'): # Pydantic
                bug_data_to_store = bug_report.dict()
            else: # Attempt conversion
                 try:
                      bug_data_to_store = vars(bug_report)
                 except TypeError:
                      logger.error(f"无法将 bug_report (类型: {type(bug_report)}) 转换为字典以存入元数据。")
                      # Decide how to handle - store partial data? Raise error?
                      bug_data_to_store = {"bug_id": bug_report.bug_id, "error": "Metadata serialization failed"}


            self.metadata["bugs"][str(new_idx)] = bug_data_to_store
            self.metadata["next_id"] = new_idx + 1
            logger.debug(f"元数据已更新，next_id 现在是 {self.metadata['next_id']}")

            # --- 7. 构建并保存所有新索引和元数据 ---
            logger.info("开始构建和保存所有更新后的索引及元数据...")
            self._save_indices() # This now handles build() and save()

            logger.info(f"Bug report (ID: {bug_report.bug_id}, Index ID: {new_idx}) 添加成功。")
            return True

        except Exception as e:
            logger.error(f"添加 bug report (ID: {bug_report.bug_id}) 失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # No rollback implemented here, state might be inconsistent if error occurs mid-process
            # Consider adding rollback logic if necessary (e.g., restore previous metadata/index files)
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
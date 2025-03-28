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
import time

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, data_dir: str = "data/annoy", vector_dim: int = 384, index_type: str = "angular", read_only: bool = True):
        self.data_dir = data_dir
        self.vector_dim = vector_dim
        self.index_type = index_type
        self.read_only = read_only
        
        # 创建数据目录
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "temp"), exist_ok=True)
        
        # 初始化索引
        self.summary_index = None
        self.code_index = None
        self.test_steps_index = None
        self.expected_result_index = None
        self.actual_result_index = None
        self.log_info_index = None
        self.environment_index = None
        
        # 初始化元数据
        self.metadata = {
            "bugs": {},
            "next_id": 0
        }
        
        # 加载或创建索引
        self._load_or_create_indices(read_only)
    
    def _load_or_create_indices(self, read_only: bool = True):
        """加载或创建索引
        
        Args:
            read_only: 是否以只读模式加载索引
        """
        try:
            # 加载元数据
            metadata_path = os.path.join(self.data_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            
            # 创建或加载索引
            self.summary_index = self._create_or_load_index("summary", read_only)
            self.code_index = self._create_or_load_index("code", read_only)
            self.test_steps_index = self._create_or_load_index("test_steps", read_only)
            self.expected_result_index = self._create_or_load_index("expected_result", read_only)
            self.actual_result_index = self._create_or_load_index("actual_result", read_only)
            self.log_info_index = self._create_or_load_index("log_info", read_only)
            self.environment_index = self._create_or_load_index("environment", read_only)
            
        except Exception as e:
            logger.error(f"加载索引失败，将创建新索引: {str(e)}")
            # 创建新的索引
            self._create_new_indices()
    
    def _create_or_load_index(self, name: str, read_only: bool = False) -> Optional[AnnoyIndex]:
        """创建或加载单个索引
        
        Args:
            name: 索引名称
            read_only: 是否以只读模式加载索引，如果为False则创建新索引
            
        Returns:
            Optional[AnnoyIndex]: 索引对象
        """
        try:
            index = AnnoyIndex(self.vector_dim, self.index_type)
            index_path = os.path.join(self.data_dir, f"{name}.ann")
            
            if os.path.exists(index_path) and read_only:
                # 如果索引文件存在且是只读模式，尝试加载它
                try:
                    index.load(index_path)
                    logger.info(f"成功加载索引: {name}, 包含 {index.get_n_items()} 个项目")
                    return index
                except Exception as e:
                    logger.error(f"加载索引 {name} 失败，将创建新索引: {str(e)}")
                    # 如果加载失败，创建新的索引
                    return AnnoyIndex(self.vector_dim, self.index_type)
            else:
                if os.path.exists(index_path):
                    logger.info(f"索引文件存在，但以写入模式创建新索引: {name}")
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
        self.summary_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.code_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.test_steps_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.expected_result_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.actual_result_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.log_info_index = AnnoyIndex(self.vector_dim, self.index_type)
        self.environment_index = AnnoyIndex(self.vector_dim, self.index_type)
    
    def _save_indices(self):
        """保存索引和元数据"""
        try:
            # 保存元数据
            metadata_copy = {
                "bugs": {},
                "next_id": self.metadata["next_id"]
            }
            
            for bug_id, bug_data in self.metadata["bugs"].items():
                metadata_copy["bugs"][bug_id] = bug_data.copy()
            
            # 保存元数据
            metadata_path = os.path.join(self.data_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_copy, f, ensure_ascii=False, indent=2)
            
            # 构建并保存索引
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
                try:
                    self._build_and_save_index(index, name)
                except Exception as e:
                    logger.error(f"保存索引 {name} 失败: {str(e)}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    # 继续保存其他索引
                    continue
            
            logger.info("所有索引和元数据保存完成")
            
        except Exception as e:
            logger.error(f"保存索引和元数据失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"保存索引和元数据失败: {str(e)}")
    
    def _build_and_save_index(self, index: Optional[AnnoyIndex], name: str) -> Optional[AnnoyIndex]:
        """构建并保存索引
        
        Args:
            index: AnnoyIndex对象
            name: 索引名称
            
        Returns:
            Optional[AnnoyIndex]: 保存后的索引对象
        """
        if index is None:
            logger.warning(f"索引 {name} 为 None，无法保存")
            return None
            
        # 检查索引是否包含项目
        if index.get_n_items() <= 0:
            logger.info(f"索引 {name} 为空，跳过保存")
            return index
            
        try:
            # 创建临时目录
            temp_dir = os.path.join(self.data_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 使用时间戳创建唯一的临时文件名
            timestamp = int(time.time())
            temp_path = os.path.join(temp_dir, f"{name}_{timestamp}.ann.tmp")
            final_path = os.path.join(self.data_dir, f"{name}.ann")
            backup_path = os.path.join(self.data_dir, f"{name}.ann.bak")  # 提前定义backup_path
            
            # 构建索引
            index.build(10)  # 10 trees for better accuracy
            
            # 保存到临时文件
            index.save(temp_path)
            
            # 等待一小段时间，确保文件写入完成
            time.sleep(0.5)
            
            # 尝试替换文件
            max_retries = 5
            retry_delay = 1.0  # 秒
            
            for attempt in range(max_retries):
                try:
                    # 如果目标文件存在，先尝试创建备份
                    if os.path.exists(final_path):
                        try:
                            if os.path.exists(backup_path):
                                try:
                                    os.remove(backup_path)
                                    time.sleep(0.2)  # 等待文件系统操作完成
                                except:
                                    logger.warning(f"无法删除旧的备份文件 {backup_path}，尝试继续")
                                    
                            # 使用复制而不是重命名
                            shutil.copy2(final_path, backup_path)
                            time.sleep(0.2)  # 等待文件系统操作完成
                            
                        except Exception as e:
                            logger.warning(f"无法备份目标文件 {final_path}，尝试直接更新: {str(e)}")
                    
                    # 使用复制而不是重命名
                    try:
                        # 将临时文件复制到目标位置
                        shutil.copy2(temp_path, final_path)
                        time.sleep(0.2)  # 等待文件系统操作完成
                        logger.info(f"成功保存索引 {name}")
                        
                        # 尝试删除临时文件
                        try:
                            os.remove(temp_path)
                        except Exception as e:
                            logger.debug(f"删除临时文件失败，但索引已成功保存: {str(e)}")
                        
                        # 如果备份文件存在且不再需要，尝试删除
                        if os.path.exists(backup_path):
                            try:
                                os.remove(backup_path)
                            except Exception as e:
                                logger.warning(f"删除备份文件失败: {str(e)}")
                        
                        return index
                        
                    except Exception as copy_error:
                        logger.warning(f"复制索引文件失败: {str(copy_error)}")
                        # 如果有备份，尝试恢复
                        if os.path.exists(backup_path):
                            try:
                                shutil.copy2(backup_path, final_path)
                                logger.info(f"已恢复备份索引 {name}")
                            except Exception as e:
                                logger.error(f"恢复备份失败: {str(e)}")
                        raise copy_error
                    
                except Exception as e:
                    logger.warning(f"保存索引 {name} 失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        raise
            
            # 如果所有重试都失败，抛出异常
            raise RuntimeError(f"保存索引 {name} 失败，已达到最大重试次数")
            
        except Exception as e:
            logger.error(f"保存索引 {name} 失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            
            # 清理临时文件和备份文件
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                        logger.info(f"已删除临时索引文件: {temp_path}")
                    except Exception as e:
                        logger.debug(f"删除临时文件失败，但索引已成功保存: {str(e)}")
                
                if os.path.exists(backup_path):
                    try:
                        os.remove(backup_path)
                        logger.info(f"已删除备份索引文件: {backup_path}")
                    except Exception as e:
                        logger.warning(f"删除备份文件失败: {str(e)}")
            except Exception as cleanup_error:
                logger.error(f"清理文件失败: {str(cleanup_error)}")
            
            return None
    
    def add_bug_report(self, bug_report: BugReport, vectors: Dict[str, Any]):
        """添加bug报告到索引"""
        try:
            # 每次添加都创建新的索引实例
            logger.info("为添加新项目创建新的索引实例")
            self.summary_index = AnnoyIndex(self.vector_dim, self.index_type)
            self.code_index = AnnoyIndex(self.vector_dim, self.index_type)
            self.test_steps_index = AnnoyIndex(self.vector_dim, self.index_type)
            self.expected_result_index = AnnoyIndex(self.vector_dim, self.index_type)
            self.actual_result_index = AnnoyIndex(self.vector_dim, self.index_type)
            self.log_info_index = AnnoyIndex(self.vector_dim, self.index_type)
            self.environment_index = AnnoyIndex(self.vector_dim, self.index_type)
            
            # 如果已有索引文件，先加载现有数据
            self._load_existing_data()
            
            # 获取新的ID
            idx = self.metadata["next_id"]
            self.metadata["next_id"] += 1
            
            # 保存bug报告元数据
            self.metadata["bugs"][str(idx)] = {
                "bug_id": bug_report.bug_id,
                "summary": bug_report.summary,
                "file_paths": bug_report.file_paths,
                "code_diffs": bug_report.code_diffs,
                "aggregated_added_code": bug_report.aggregated_added_code,
                "aggregated_removed_code": bug_report.aggregated_removed_code,
                "test_steps": bug_report.test_steps,
                "expected_result": bug_report.expected_result,
                "actual_result": bug_report.actual_result,
                "log_info": bug_report.log_info,
                "severity": bug_report.severity,
                "is_reappear": bug_report.is_reappear,
                "environment": bug_report.environment,
                "root_cause": bug_report.root_cause,
                "fix_solution": bug_report.fix_solution,
                "related_issues": bug_report.related_issues,
                "fix_person": bug_report.fix_person,
                "create_at": bug_report.create_at,
                "fix_date": bug_report.fix_date,
                "reopen_count": bug_report.reopen_count,
                "handlers": bug_report.handlers,
                "project_id": bug_report.project_id
            }
            
            # 添加向量到索引
            success = True
            try:
                if "summary_vector" in vectors and self.summary_index is not None:
                    self.summary_index.add_item(idx, vectors["summary_vector"])
                if "code_vector" in vectors and self.code_index is not None:
                    self.code_index.add_item(idx, vectors["code_vector"])
                if "test_steps_vector" in vectors and self.test_steps_index is not None:
                    self.test_steps_index.add_item(idx, vectors["test_steps_vector"])
                if "expected_result_vector" in vectors and self.expected_result_index is not None:
                    self.expected_result_index.add_item(idx, vectors["expected_result_vector"])
                if "actual_result_vector" in vectors and self.actual_result_index is not None:
                    self.actual_result_index.add_item(idx, vectors["actual_result_vector"])
                if "log_info_vector" in vectors and self.log_info_index is not None:
                    self.log_info_index.add_item(idx, vectors["log_info_vector"])
                if "environment_vector" in vectors and self.environment_index is not None:
                    self.environment_index.add_item(idx, vectors["environment_vector"])
                
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
            
            # 确保所有索引以只读模式加载
            if not self.read_only:
                logger.info("当前索引为写入模式，切换到只读模式进行搜索")
                self._load_or_create_indices(read_only=True)
                self.read_only = True
            
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
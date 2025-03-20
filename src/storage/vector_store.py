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
from src.features.code_features import CodeFeatureExtractor, CodeFeatures

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
            
            # 初始化代码特征提取器
            self.code_feature_extractor = CodeFeatureExtractor()
            
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
            # 提取代码特征
            code_features = self.code_feature_extractor.extract_features(bug_report.code_context.code)
            
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
                "description": bug_report.description,
                "reproducible": bug_report.reproducible,
                "steps_to_reproduce": bug_report.steps_to_reproduce,
                "expected_behavior": bug_report.expected_behavior,
                "actual_behavior": bug_report.actual_behavior,
                "created_at": bug_report.created_at.isoformat(),
                "updated_at": bug_report.updated_at.isoformat(),
                "tags": bug_report.tags
            })
            
            self.metadata["codes"].append({
                "id": bug_report.id,
                "code": bug_report.code_context.code,
                "file_path": bug_report.code_context.file_path,
                "line_range": bug_report.code_context.line_range,
                "language": bug_report.code_context.language,
                "dependencies": bug_report.code_context.dependencies,
                "diff": bug_report.code_context.diff,
                "features": {
                    "ast": code_features.ast_features,
                    "symbol": code_features.symbol_features,
                    "structure": code_features.structure_features
                }
            })
            
            self.metadata["logs"].append({
                "id": bug_report.id,
                "log": bug_report.error_logs
            })
            
            self.metadata["envs"].append({
                "id": bug_report.id,
                "runtime_env": bug_report.environment.runtime_env,
                "os_info": bug_report.environment.os_info,
                "network_env": bug_report.environment.network_env,
                "additional_info": bug_report.environment.additional_info
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
                weights = {
                    "question": 3.0,
                    "code": 1.0,
                    "log": 0.5,
                    "env": 0.3
                }
            
            if not self.question_index:
                logger.warning("索引为空，无法搜索")
                return []
            
            # 添加原始查询文本到向量字典中
            if "query_text" in query_vectors:
                query_vectors = dict(query_vectors)  # 创建副本以避免修改原始数据
            
            # 1. 初筛阶段：文本+代码语义的并行ANN搜索
            initial_results = self._initial_screening(query_vectors, n_results=200)
            
            # 2. 粗排阶段：结构特征快速过滤
            filtered_results = self._coarse_ranking(initial_results, n_results=50)
            
            # 3. 精排阶段：符号匹配+加权得分计算
            final_results = self._fine_ranking(filtered_results, n_results=n_results)
            
            return final_results
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise RuntimeError(f"搜索失败: {str(e)}")
    
    def _initial_screening(self, query_vectors, n_results=200):
        """初筛阶段：文本+代码语义的并行ANN搜索"""
        # 获取每个向量的最近邻
        question_neighbors = self.question_index.get_nns_by_vector(
            query_vectors["question_vector"], n_results, include_distances=True)
        code_neighbors = self.code_index.get_nns_by_vector(
            query_vectors["code_vector"], n_results, include_distances=True)
        
        # 合并结果
        results = {}
        for i, (idx, dist) in enumerate(zip(question_neighbors[0], question_neighbors[1])):
            results[idx] = {"distance": dist * 0.6}  # 文本相似度权重
        
        for i, (idx, dist) in enumerate(zip(code_neighbors[0], code_neighbors[1])):
            if idx in results:
                results[idx]["distance"] += dist * 0.4  # 代码语义权重
            else:
                results[idx] = {"distance": dist * 0.4}
        
        # 添加关键词匹配得分
        query_text = query_vectors.get("query_text", "")
        if query_text:
            for idx in list(results.keys()):
                keyword_score = self._calculate_keyword_score(
                    query_text, 
                    self.metadata["questions"][idx],
                    self.metadata["codes"][idx]
                )
                # 将关键词匹配得分与向量相似度得分结合
                results[idx]["distance"] = results[idx]["distance"] * 0.7 + (1 - keyword_score) * 0.3
        
        return sorted(results.items(), key=lambda x: x[1]["distance"])[:n_results]
    
    def _calculate_keyword_score(self, query: str, question_data: Dict, code_data: Dict) -> float:
        """计算关键词匹配得分
        
        Args:
            query: 查询文本
            question_data: 问题元数据
            code_data: 代码元数据
            
        Returns:
            float: 匹配得分 (0-1)
        """
        # 对查询文本进行分词
        keywords = set(query.lower().split())
        
        # 准备要搜索的文本
        title = question_data["title"].lower()
        description = question_data["description"].lower()
        code = code_data["code"].lower()
        
        # 计算每个关键词的匹配情况
        matches = 0
        for keyword in keywords:
            if keyword in title:
                matches += 2  # 标题匹配权重更高
            if keyword in description:
                matches += 1
            if keyword in code:
                matches += 1
        
        # 计算最终得分
        max_possible_matches = len(keywords) * 4  # 每个关键词最多可以得到4分
        if max_possible_matches == 0:
            return 0.0
        
        return min(1.0, matches / max_possible_matches)
    
    def _coarse_ranking(self, initial_results, n_results=50):
        """粗排阶段：结构特征快速过滤"""
        filtered_results = []
        for idx, score in initial_results:
            code_data = self.metadata["codes"][idx]
            if "features" in code_data and "structure" in code_data["features"]:
                structure_features = code_data["features"]["structure"]
                # 根据结构特征进行过滤
                if self._is_structure_similar(structure_features):
                    filtered_results.append((idx, score))
        
        return filtered_results[:n_results]
    
    def _fine_ranking(self, filtered_results, n_results=10):
        """精排阶段：符号匹配+加权得分计算"""
        final_results = []
        for idx, initial_score in filtered_results:
            code_data = self.metadata["codes"][idx]
            if "features" in code_data:
                features = code_data["features"]
                # 计算符号匹配度
                symbol_score = self._calculate_symbol_score(features)
                # 计算最终得分
                final_score = initial_score["distance"] * 0.7 + symbol_score * 0.3
                final_results.append((idx, final_score))
            else:
                final_results.append((idx, initial_score["distance"]))
        
        # 按得分排序并返回结果
        sorted_results = []
        for idx, score in sorted(final_results, key=lambda x: x[1])[:n_results]:
            # 获取完整的 bug 报告信息
            question_data = self.metadata["questions"][idx]
            code_data = self.metadata["codes"][idx]
            env_data = self.metadata["envs"][idx]
            log_data = self.metadata["logs"][idx]
            
            result = {
                "id": question_data["id"],
                "title": question_data["title"],
                "description": question_data["description"],
                "reproducible": question_data["reproducible"],
                "steps_to_reproduce": question_data["steps_to_reproduce"],
                "expected_behavior": question_data["expected_behavior"],
                "actual_behavior": question_data["actual_behavior"],
                "code_context": {
                    "code": code_data["code"],
                    "file_path": code_data["file_path"],
                    "line_range": code_data["line_range"],
                    "language": code_data["language"],
                    "dependencies": code_data["dependencies"],
                    "diff": code_data["diff"]
                },
                "error_logs": log_data["log"],
                "environment": {
                    "runtime_env": env_data["runtime_env"],
                    "os_info": env_data["os_info"],
                    "network_env": env_data["network_env"],
                    "additional_info": env_data["additional_info"]
                },
                "created_at": question_data["created_at"],
                "updated_at": question_data["updated_at"],
                "tags": question_data["tags"],
                "distance": score
            }
            sorted_results.append(result)
        
        return sorted_results
    
    def _is_structure_similar(self, structure_features):
        """判断结构特征是否相似
        
        Args:
            structure_features: 目标代码的结构特征
            
        Returns:
            bool: 是否相似
        """
        # 1. 检查控制结构数量是否接近
        def is_control_count_similar(control_counts: Dict[str, int], threshold: float = 0.5) -> bool:
            total = sum(control_counts.values())
            if total == 0:
                return True
                
            # 计算每种控制结构的比例
            ratios = {k: v/total for k, v in control_counts.items()}
            
            # 检查是否有过于主导的控制结构 - 允许更高的阈值
            return all(ratio <= threshold for ratio in ratios.values())
        
        # 2. 检查嵌套深度是否在合理范围
        def is_depth_reasonable(depth: int, max_depth: int = 8) -> bool:
            return depth <= max_depth
        
        # 3. 检查异常处理是否合理
        def is_exception_reasonable(handlers: List[Dict]) -> bool:
            if not handlers:
                return True
            
            # 放宽异常处理的限制
            if len(handlers) > 8:  # 增加允许的异常处理数量
                return False
            
            # 增加允许的处理器代码行数
            return all(handler["body_length"] <= 30 for handler in handlers)
        
        # 综合判断 - 只要满足两个条件即可
        conditions = [
            is_control_count_similar(structure_features["control_structures"]),
            is_depth_reasonable(structure_features["nesting_depth"]),
            is_exception_reasonable(structure_features["exception_handlers"])
        ]
        
        return sum(1 for c in conditions if c) >= 2  # 只要满足两个条件即可
    
    def _calculate_symbol_score(self, features):
        """计算符号匹配度得分
        
        Args:
            features: 代码特征字典，包含ast、symbol和structure特征
            
        Returns:
            float: 相似度分数 (0-1)
        """
        if "symbol" not in features:
            return 0.0
        
        symbol_features = features["symbol"]
        
        # 1. 计算变量命名模式的一致性得分
        def calculate_pattern_score() -> float:
            patterns = symbol_features["symbol_patterns"]
            if not patterns:
                return 0.0
            
            # 计算命名模式的分布
            total = sum(patterns.values())
            if total == 0:
                return 0.0
            
            pattern_ratios = {k: v/total for k, v in patterns.items()}
            
            # 评估命名一致性 - 如果某个模式占比过高说明命名比较一致
            max_ratio = max(pattern_ratios.values())
            return min(max_ratio * 2, 1.0)  # 将比例转换为0-1的分数
        
        # 2. 计算标识符长度的合理性得分
        def calculate_length_score() -> float:
            all_symbols = (
                symbol_features["variables"] + 
                symbol_features["functions"] + 
                symbol_features["classes"]
            )
            
            if not all_symbols:
                return 0.0
            
            # 计算平均标识符长度
            avg_length = sum(len(s) for s in all_symbols) / len(all_symbols)
            
            # 标识符长度在2-30个字符之间比较合理
            if avg_length < 2:
                return 0.0
            elif avg_length > 30:
                return 0.0
            elif 2 <= avg_length <= 15:  # 最理想的长度范围
                return 1.0
            else:  # 15-30的长度，分数线性下降
                return max(0, (30 - avg_length) / 15)
        
        # 3. 计算命名规范性得分
        def calculate_convention_score() -> float:
            def is_snake_case(s: str) -> bool:
                return s.islower() and "_" in s
            
            def is_camel_case(s: str) -> bool:
                return not s[0].isupper() and not "_" in s and not s.islower()
            
            def is_pascal_case(s: str) -> bool:
                return s[0].isupper() and not "_" in s
            
            all_symbols = (
                symbol_features["variables"] + 
                symbol_features["functions"] + 
                symbol_features["classes"]
            )
            
            if not all_symbols:
                return 0.0
            
            # 统计各种命名规范的使用数量
            conventions = {
                "snake": sum(1 for s in all_symbols if is_snake_case(s)),
                "camel": sum(1 for s in all_symbols if is_camel_case(s)),
                "pascal": sum(1 for s in all_symbols if is_pascal_case(s))
            }
            
            # 计算主导的命名规范的比例
            total = sum(conventions.values())
            if total == 0:
                return 0.0
            
            max_convention_ratio = max(conventions.values()) / total
            return max_convention_ratio
        
        # 综合三个维度的得分
        pattern_score = calculate_pattern_score()
        length_score = calculate_length_score()
        convention_score = calculate_convention_score()
        
        # 加权平均
        weights = {
            "pattern": 0.4,      # 命名模式一致性权重
            "length": 0.3,       # 标识符长度合理性权重
            "convention": 0.3    # 命名规范性权重
        }
        
        final_score = (
            pattern_score * weights["pattern"] +
            length_score * weights["length"] +
            convention_score * weights["convention"]
        )
        
        return final_score
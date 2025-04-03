import ast
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
from src.utils.log import logger

@dataclass
class CodeFeatures:
    """代码特征数据类"""
    ast_features: Dict[str, Any]  # AST相关特征
    symbol_features: Dict[str, Any]  # 符号相关特征
    structure_features: Dict[str, Any]  # 结构相关特征

class CodeFeatureExtractor:
    def __init__(self):
        self.feature_weights = {
            "semantic": 0.4,
            "structural": 0.3,
            "symbolic": 0.2,
            "log": 0.1
        }
    
    def extract_features(self, code: str) -> CodeFeatures:
        """提取代码的所有特征"""
        try:
            tree = ast.parse(code)
            return CodeFeatures(
                ast_features=self._extract_ast_features(tree),
                symbol_features=self._extract_symbol_features(tree),
                structure_features=self._extract_structure_features(tree)
            )
        except Exception as e:
            logger.error(f"代码特征提取失败: {str(e)}")
            return CodeFeatures({}, {}, {})
    
    def _extract_ast_features(self, tree: ast.AST) -> Dict[str, Any]:
        """提取AST相关特征"""
        features = {
            "function_defs": [],
            "class_defs": [],
            "api_calls": [],
            "imports": []
        }
        
        class ASTVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                features["function_defs"].append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [decorator.id for decorator in node.decorator_list if isinstance(decorator, ast.Name)]
                })
            
            def visit_ClassDef(self, node):
                features["class_defs"].append({
                    "name": node.name,
                    "bases": [base.id for base in node.bases if isinstance(base, ast.Name)],
                    "methods": [method.name for method in node.body if isinstance(method, ast.FunctionDef)]
                })
            
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    features["api_calls"].append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    features["api_calls"].append(node.func.attr)
            
            def visit_Import(self, node):
                features["imports"].extend(alias.name for alias in node.names)
            
            def visit_ImportFrom(self, node):
                features["imports"].extend(alias.name for alias in node.names)
        
        ASTVisitor().visit(tree)
        return features
    
    def _extract_symbol_features(self, tree: ast.AST) -> Dict[str, Any]:
        """提取符号相关特征"""
        features = {
            "variables": [],
            "functions": [],
            "classes": [],
            "symbol_patterns": defaultdict(int)
        }
        
        class SymbolVisitor(ast.NodeVisitor):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):  # 变量赋值
                    features["variables"].append(node.id)
                    # 提取变量名模式
                    pattern = self._normalize_identifier(node.id)
                    features["symbol_patterns"][pattern] += 1
            
            def visit_FunctionDef(self, node):
                features["functions"].append(node.name)
                pattern = self._normalize_identifier(node.name)
                features["symbol_patterns"][pattern] += 1
            
            def visit_ClassDef(self, node):
                features["classes"].append(node.name)
                pattern = self._normalize_identifier(node.name)
                features["symbol_patterns"][pattern] += 1
            
            def _normalize_identifier(self, name: str) -> str:
                """标识符归一化处理"""
                # 驼峰命名转下划线
                name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
                # 移除数字
                name = re.sub(r'\d+', '', name)
                # 移除特殊字符
                name = re.sub(r'[^a-z_]', '', name)
                return name
        
        SymbolVisitor().visit(tree)
        return features
    
    def _extract_structure_features(self, tree: ast.AST) -> Dict[str, Any]:
        """提取结构相关特征"""
        features = {
            "nesting_depth": 0,
            "control_structures": defaultdict(int),
            "exception_handlers": [],
            "code_blocks": []
        }
        
        class StructureVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_depth = 0
                self.max_depth = 0
            
            def visit(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                super().visit(node)
                self.current_depth -= 1
            
            def visit_If(self, node):
                features["control_structures"]["if"] += 1
            
            def visit_For(self, node):
                features["control_structures"]["for"] += 1
            
            def visit_While(self, node):
                features["control_structures"]["while"] += 1
            
            def visit_Try(self, node):
                features["control_structures"]["try"] += 1
                for handler in node.handlers:
                    handler_type = handler.type.id if handler.type and isinstance(handler.type, ast.Name) else "Exception"
                    features["exception_handlers"].append({
                        "type": handler_type,
                        "body_length": len(handler.body)
                    })
            
            def visit_With(self, node):
                features["control_structures"]["with"] += 1
        
        visitor = StructureVisitor()
        visitor.visit(tree)
        features["nesting_depth"] = visitor.max_depth
        return features
    
    def calculate_similarity(self, query_features: CodeFeatures, target_features: CodeFeatures) -> float:
        """计算代码特征相似度"""
        scores = {
            "semantic": self._calculate_semantic_similarity(query_features, target_features),
            "structural": self._calculate_structural_similarity(query_features, target_features),
            "symbolic": self._calculate_symbolic_similarity(query_features, target_features)
        }
        
        return sum(score * self.feature_weights[weight_type] 
                  for weight_type, score in scores.items())
    
    def _calculate_semantic_similarity(self, query: CodeFeatures, target: CodeFeatures) -> float:
        """计算语义相似度"""
        # 比较函数定义、类定义和API调用的相似度
        query_funcs = set(f["name"] for f in query.ast_features["function_defs"])
        target_funcs = set(f["name"] for f in target.ast_features["function_defs"])
        
        query_classes = set(c["name"] for c in query.ast_features["class_defs"])
        target_classes = set(c["name"] for c in target.ast_features["class_defs"])
        
        query_apis = set(query.ast_features["api_calls"])
        target_apis = set(target.ast_features["api_calls"])
        
        func_sim = len(query_funcs & target_funcs) / len(query_funcs | target_funcs) if query_funcs or target_funcs else 0
        class_sim = len(query_classes & target_classes) / len(query_classes | target_classes) if query_classes or target_classes else 0
        api_sim = len(query_apis & target_apis) / len(query_apis | target_apis) if query_apis or target_apis else 0
        
        return (func_sim + class_sim + api_sim) / 3
    
    def _calculate_structural_similarity(self, query: CodeFeatures, target: CodeFeatures) -> float:
        """计算结构相似度"""
        # 比较嵌套深度、控制结构和异常处理的相似度
        depth_diff = abs(query.structure_features["nesting_depth"] - 
                        target.structure_features["nesting_depth"])
        depth_sim = 1 / (1 + depth_diff)
        
        query_controls = query.structure_features["control_structures"]
        target_controls = target.structure_features["control_structures"]
        
        control_sim = sum(min(query_controls[k], target_controls[k]) 
                         for k in set(query_controls) | set(target_controls)) / \
                     sum(max(query_controls[k], target_controls[k]) 
                         for k in set(query_controls) | set(target_controls)) if query_controls or target_controls else 0
        
        return (depth_sim + control_sim) / 2
    
    def _calculate_symbolic_similarity(self, query: CodeFeatures, target: CodeFeatures) -> float:
        """计算符号相似度"""
        # 比较变量名、函数名和类名的模式相似度
        query_patterns = query.symbol_features["symbol_patterns"]
        target_patterns = target.symbol_features["symbol_patterns"]
        
        pattern_sim = sum(min(query_patterns[k], target_patterns[k]) 
                         for k in set(query_patterns) | set(target_patterns)) / \
                     sum(max(query_patterns[k], target_patterns[k]) 
                         for k in set(query_patterns) | set(target_patterns)) if query_patterns or target_patterns else 0
        
        return pattern_sim 
    
    def _calculate_symbol_score(self, query_symbols: List[str], target_symbols: List[str]) -> float:
        """计算符号相似度分数
        
        Args:
            query_symbols: 查询代码的符号列表
            target_symbols: 目标代码的符号列表
            
        Returns:
            float: 相似度分数 (0-1)
        """
        if not query_symbols or not target_symbols:
            return 0.0
            
        # 计算最长公共子序列(LCS)长度
        def lcs_length(s1: str, s2: str) -> int:
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            for i in range(m):
                for j in range(n):
                    if s1[i] == s2[j]:
                        dp[i + 1][j + 1] = dp[i][j] + 1
                    else:
                        dp[i + 1][j + 1] = max(dp[i + 1][j], dp[i][j + 1])
            return dp[m][n]
        
        # 计算编辑距离
        def edit_distance(s1: str, s2: str) -> int:
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            for i in range(m + 1):
                dp[i][0] = i
            for j in range(n + 1):
                dp[0][j] = j
            for i in range(m):
                for j in range(n):
                    if s1[i] == s2[j]:
                        dp[i + 1][j + 1] = dp[i][j]
                    else:
                        dp[i + 1][j + 1] = min(dp[i][j + 1], dp[i + 1][j], dp[i][j]) + 1
            return dp[m][n]
        
        # 计算每对符号的相似度
        total_score = 0
        count = 0
        for q_sym in query_symbols:
            best_score = 0
            for t_sym in target_symbols:
                # 计算LCS得分
                lcs_score = 2 * lcs_length(q_sym, t_sym) / (len(q_sym) + len(t_sym)) if q_sym and t_sym else 0
                # 计算编辑距离得分
                edit_score = 1 - edit_distance(q_sym, t_sym) / max(len(q_sym), len(t_sym)) if q_sym and t_sym else 0
                # 综合得分
                score = 0.6 * lcs_score + 0.4 * edit_score
                best_score = max(best_score, score)
            total_score += best_score
            count += 1
            
        return total_score / count if count > 0 else 0.0
    
    def _is_structure_similar(self, query_structure: Dict[str, Any], target_structure: Dict[str, Any]) -> bool:
        """判断两个代码结构是否相似
        
        Args:
            query_structure: 查询代码的结构特征
            target_structure: 目标代码的结构特征
            
        Returns:
            bool: 是否相似
        """
        # 1. 检查控制结构数量是否接近
        def is_control_count_similar(q_count: Dict[str, int], t_count: Dict[str, int], threshold: float = 0.3) -> bool:
            total_q = sum(q_count.values())
            total_t = sum(t_count.values())
            if total_q == 0 and total_t == 0:
                return True
            if total_q == 0 or total_t == 0:
                return False
            
            # 计算每种控制结构的比例差异
            for control_type in set(q_count.keys()) | set(t_count.keys()):
                q_ratio = q_count.get(control_type, 0) / total_q
                t_ratio = t_count.get(control_type, 0) / total_t
                if abs(q_ratio - t_ratio) > threshold:
                    return False
            return True
        
        # 2. 检查嵌套深度是否接近
        def is_depth_similar(q_depth: int, t_depth: int, max_diff: int = 2) -> bool:
            return abs(q_depth - t_depth) <= max_diff
        
        # 3. 检查异常处理是否相似
        def is_exception_similar(q_handlers: List[Dict], t_handlers: List[Dict], threshold: float = 0.5) -> bool:
            if not q_handlers and not t_handlers:
                return True
            if not q_handlers or not t_handlers:
                return False
                
            # 比较异常类型集合的重叠度
            q_types = {h["type"] for h in q_handlers}
            t_types = {h["type"] for h in t_handlers}
            overlap = len(q_types & t_types)
            union = len(q_types | t_types)
            return overlap / union >= threshold
        
        # 综合判断
        control_similar = is_control_count_similar(
            query_structure["control_structures"],
            target_structure["control_structures"]
        )
        
        depth_similar = is_depth_similar(
            query_structure["nesting_depth"],
            target_structure["nesting_depth"]
        )
        
        exception_similar = is_exception_similar(
            query_structure["exception_handlers"],
            target_structure["exception_handlers"]
        )
        
        # 至少满足两个条件即认为结构相似
        similar_count = sum([control_similar, depth_similar, exception_similar])
        return similar_count >= 2
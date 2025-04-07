import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.retrieval.searcher_manager import get_bug_searcher

def search_bugs():
    # 获取搜索器实例
    searcher = get_bug_searcher()
    
    # 搜索示例
    print("\n=== Bug 知识库搜索系统 ===\n")
    
    while True:
        print("\n请选择搜索类型：")
        print("1. 按问题描述搜索")
        print("2. 按代码内容搜索")
        print("3. 按错误日志搜索")
        print("4. 按环境信息搜索")
        print("5. 混合搜索")
        print("0. 退出")
        
        choice = input("\n请输入选项（0-5）: ")
        
        if choice == "0":
            break
        
        n_results = int(input("请输入要返回的结果数量（默认5）: ") or "5")
        
        if choice == "1":
            query = input("\n请输入问题描述: ")
            results = searcher.search(
                summary=query,
                n_results=n_results,
                weights={"question": 1.0, "code": 0.0, "log": 0.0, "env": 0.0}
            )
        elif choice == "2":
            query = input("\n请输入代码片段: ")
            results = searcher.search(
                code_snippet=query,
                n_results=n_results,
                weights={"question": 0.0, "code": 1.0, "log": 0.0, "env": 0.0}
            )
        elif choice == "3":
            query = input("\n请输入错误日志: ")
            results = searcher.search(
                error_log=query,
                n_results=n_results,
                weights={"question": 0.0, "code": 0.0, "log": 1.0, "env": 0.0}
            )
        elif choice == "4":
            query = input("\n请输入环境信息: ")
            results = searcher.search(
                env_info=query,
                n_results=n_results,
                weights={"question": 0.0, "code": 0.0, "log": 0.0, "env": 1.0}
            )
        elif choice == "5":
            print("\n=== 混合搜索 ===")
            summary = input("问题描述: ")
            code_snippet = input("代码片段: ")
            error_log = input("错误日志: ")
            env_info = input("环境信息: ")
            
            # 设置权重
            print("\n请设置各部分的权重（0-1之间的小数）：")
            w_question = float(input("问题描述权重（默认0.4）: ") or "0.4")
            w_code = float(input("代码片段权重（默认0.3）: ") or "0.3")
            w_log = float(input("错误日志权重（默认0.2）: ") or "0.2")
            w_env = float(input("环境信息权重（默认0.1）: ") or "0.1")
            
            results = searcher.search(
                summary=summary,
                code_snippet=code_snippet,
                error_log=error_log,
                env_info=env_info,
                n_results=n_results,
                weights={
                    "question": w_question,
                    "code": w_code,
                    "log": w_log,
                    "env": w_env
                }
            )
        else:
            print("\n无效的选项！")
            continue
        
        # 显示搜索结果
        print("\n=== 搜索结果 ===\n")
        for i, result in enumerate(results, 1):
            print(f"结果 {i}:")
            print(f"Bug ID: {result['id']}")
            print(f"描述: {result['description']}")
            print(f"相似度得分: {1 - result['distance']:.4f}")
            print("-" * 50)

if __name__ == "__main__":
    search_bugs()
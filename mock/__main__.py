import argparse
import sys
from pathlib import Path
from rich.console import Console

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.ui.web import start_web_app
from src.retrieval.searcher import BugSearcher
from src.config import AppConfig
from mock.generate_mock_data import save_mock_data
from mock.load_mock_data import load_mock_data
from src.storage.vector_store import VectorStore

console = Console()

def main():
    """主函数"""
    # 初始化配置
    config = AppConfig(
        vector_store={
            "data_dir": "data/annoy",
            "vector_dim": 768,
            "index_type": "annoy"
        },
        web={
            "templates_dir": "src/ui/templates",
            "static_dir": "src/ui/static"
        },
        searcher={
            "max_results": 10,
            "similarity_threshold": 0.7
        }
    )
    
    # 初始化搜索器
    vector_store = VectorStore(data_dir=config.vector_store["data_dir"])
    searcher = BugSearcher(vector_store=vector_store)
    
    # 生成并加载测试数据
    print("正在生成测试数据...")
    save_mock_data()

    print("正在加载测试数据...")
    searcher = load_mock_data(searcher=searcher)

    if searcher is None:
        console.print("[red]错误：加载测试数据失败[/red]")
        return
    
    # 启动Web应用
    start_web_app(searcher=searcher, config=config)

if __name__ == "__main__":
    main()

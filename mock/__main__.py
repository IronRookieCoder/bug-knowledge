import argparse
import sys
from pathlib import Path
from rich.console import Console

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.ui.web import start_web_app
from src.retrieval.searcher import BugSearcher
from src.config import config
from mock.generate_mock_data import save_mock_data
from mock.load_mock_data import load_mock_data
from src.storage.vector_store import VectorStore

console = Console()

def main():
    """主函数"""
    # 初始化搜索器
    vector_store = VectorStore(
        data_dir=config.get('VECTOR_STORE')['data_dir'],
        vector_dim=config.get('VECTOR_STORE')['vector_dim'],
        index_type=config.get('VECTOR_STORE')['index_type'],
        n_trees=config.get('VECTOR_STORE')['n_trees'],
        similarity_threshold=config.get('VECTOR_STORE')['similarity_threshold']
    )
    searcher = BugSearcher(vector_store=vector_store)
    
    # 生成并加载测试数据
    print("正在生成测试数据...")
    save_mock_data()

    print("正在加载测试数据...")
    searcher = load_mock_data(searcher=searcher)

    if searcher is None:
        console.print("[red]错误：加载测试数据失败[/red]")
        return
    
    # 启动Web应用，移除 config 参数
    start_web_app(searcher=searcher)

if __name__ == "__main__":
    main()

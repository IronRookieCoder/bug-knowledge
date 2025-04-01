import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.ui.web import start_web_app
from src.retrieval.searcher import BugSearcher
from src.config import AppConfig
from src.crawler.__main__ import main as crawler_main
from src.storage.__main__ import main as storage_main

def main():
    parser = argparse.ArgumentParser(description="Bug知识库系统")
    parser.add_argument("--mode", choices=["crawler", "storage", "web"], required=True,
                      help="运行模式：crawler(爬取数据), storage(构建向量索引), web(启动Web服务)")
    parser.add_argument("--host", default="127.0.0.1", help="Web服务器主机地址")
    parser.add_argument("--port", type=int, default=8010, help="Web服务器端口")
    
    args = parser.parse_args()
    
    # 初始化配置
    config = AppConfig(
        vector_store={
            "data_dir": "data/annoy",
            "vector_dim": 384,
            "index_type": "angular"
        },
        web={
            "templates_dir": "src/ui/templates",
            "static_dir": "src/ui/static"
        },
        searcher={}
    )
    
    if args.mode == "crawler":
        print("开始爬取数据...")
        crawler_main()
    elif args.mode == "storage":
        print("开始构建向量索引...")
        storage_main()
    elif args.mode == "web":
        print("启动Web服务...")
        # 初始化搜索器
        searcher = BugSearcher()
        
        # 启动Web应用
        start_web_app(
            searcher=searcher,
            config=config,
            host=args.host,
            port=args.port,
        )

if __name__ == "__main__":
    main()

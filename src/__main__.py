import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.ui.web import start_web_app
from src.retrieval.searcher import BugSearcher
from src.config import AppConfig

def main():
    parser = argparse.ArgumentParser(description="Bug知识库系统")
    parser.add_argument("command", choices=["web"], help="要执行的命令")
    parser.add_argument("--host", default="127.0.0.1", help="Web服务器主机地址")
    parser.add_argument("--port", type=int, default=8000, help="Web服务器端口")
    parser.add_argument("--reload", action="store_true", help="是否启用热重载")
    
    args = parser.parse_args()
    
    if args.command == "web":
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
        
        # 初始化搜索器
        searcher = BugSearcher()
        
        # 启动Web应用
        start_web_app(
            searcher=searcher,
            config=config,
            host=args.host,
            port=args.port,
            reload=args.reload
        )

if __name__ == "__main__":
    main() 
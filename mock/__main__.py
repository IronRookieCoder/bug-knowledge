import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.ui.web import start_web_app
from src.retrieval.searcher import BugSearcher
from src.config import AppConfig
from mock.generate_mock_data import save_mock_data
from mock.load_mock_data import load_mock_data

def main():
    parser = argparse.ArgumentParser(description="Bug知识库系统 - Mock测试模式")
    parser.add_argument("command", choices=["web"], help="要执行的命令")
    parser.add_argument("--host", default="127.0.0.1", help="Web服务器主机地址")
    parser.add_argument("--port", type=int, default=8000, help="Web服务器端口")
    parser.add_argument("--reload", action="store_true", help="是否启用热重载")
    parser.add_argument("--data-count", type=int, default=10, help="生成的测试数据数量")
    
    args = parser.parse_args()
    
    if args.command == "web":
        # 初始化配置
        config = AppConfig(
            vector_store={
                "data_dir": "mock/data/annoy",
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
        
        # 生成并加载测试数据
        print("正在生成测试数据...")
        save_mock_data(args.data_count)
        print("正在加载测试数据...")
        searcher = load_mock_data(searcher=searcher)
        
        print(f"\n测试数据已准备就绪，共 {args.data_count} 条记录")
        print("正在启动 Web 应用...")
        
        # 启动Web应用
        start_web_app(
            searcher=searcher,
            config=config,
            host=args.host,
            port=args.port,
            reload=args.reload,
            reload_dirs=["src", "mock", "templates", "static"],
            reload_includes=["*.py", "*.html", "*.js", "*.css", "*.json"],
            reload_excludes=["*.pyc", "__pycache__", "*.pyo", "*.pyd", "*.log"]
        )

if __name__ == "__main__":
    main() 
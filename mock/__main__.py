import sys
from pathlib import Path
from rich.console import Console

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.ui.web import start_web_app
from mock.generate_mock_data import save_mock_data
from mock.load_mock_data import load_mock_data

console = Console()

def main():
    """主函数"""
    # 生成并加载测试数据
    print("正在生成测试数据...")
    save_mock_data()

    print("正在加载测试数据...")
    load_mock_data()

    # 启动Web应用
    start_web_app()

if __name__ == "__main__":
    main()

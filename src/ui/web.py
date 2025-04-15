from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List
import uvicorn
import socket
import traceback
import os
import pickle
import json
from pathlib import Path
from annoy import AnnoyIndex
import time
import tempfile

from src.utils.log import get_logger
from src.config import config
from src.ui.routers import bug
from src.retrieval.searcher import BugSearcher
from src.retrieval.searcher_manager import set_bug_searcher

logger = get_logger(__name__)

def find_available_port(start_port: int = 8000, max_port: int = 8999) -> int:
    """查找可用端口"""
    for port in range(start_port, max_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"在端口范围 {start_port}-{max_port} 内没有找到可用端口")

def create_web_app() -> FastAPI:
    """创建Web应用实例"""
    app = FastAPI(title="BUG知识库系统", root_path="/bug-knowledge")

    # 配置模板和静态文件
    templates = Jinja2Templates(directory=config.get("WEB")["templates_dir"])
    app.mount(
        "/static", StaticFiles(directory=config.get("WEB")["static_dir"]), name="static"
    )

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/add", response_class=HTMLResponse)
    async def add_page(request: Request):
        return templates.TemplateResponse("add.html", {"request": request})

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(request: Request):
        return templates.TemplateResponse("search.html", {"request": request})

    # Include routers
    app.include_router(bug.router)

    return app

def init_vector_indices():
    """初始化向量索引"""
    try:
        # 从环境变量获取临时目录路径，如果未设置则使用系统临时目录
        temp_dir = os.environ.get("BUG_KNOWLEDGE_TEMP_DIR")
        if not temp_dir:
            temp_dir = os.path.join(tempfile.gettempdir(), "bug_knowledge")
            os.environ["BUG_KNOWLEDGE_TEMP_DIR"] = temp_dir
            logger.info(f"未设置临时目录路径，使用系统临时目录：{temp_dir}")

        # 获取向量存储配置
        vector_store_config = config.get("VECTOR_STORE", {
            "vector_dim": 384,
            "index_type": "angular",
            "n_trees": 10,
            "similarity_threshold": 1.2,
            "data_dir": "data/annoy"
        })

        # 确保目录存在
        temp_dir_path = Path(temp_dir)
        temp_dir_path.mkdir(parents=True, exist_ok=True)

        # 创建配置目录
        config_path = temp_dir_path / "config.pkl"
        if not config_path.exists():
            with open(config_path, "wb") as f:
                pickle.dump(vector_store_config, f)
            logger.info("创建默认配置文件")

        # 创建索引目录
        indices_dir = temp_dir_path / "indices"
        indices_dir.mkdir(exist_ok=True)

        # 获取向量维度和其他配置
        vector_dim = vector_store_config["vector_dim"]
        index_type = vector_store_config["index_type"]
        n_trees = vector_store_config["n_trees"]
        
        # 初始化向量索引
        index_files = ["summary.ann", "code.ann", "test_info.ann", "log_info.ann", "environment.ann"]
        
        # 添加重试机制
        max_retries = 3
        retry_delay = 0.5  # 秒

        for index_file in index_files:
            index_path = indices_dir / index_file
            logger.info(f"开始处理索引文件: {index_file}")
            
            if not index_path.exists():
                logger.info(f"索引文件不存在，将创建新的空索引: {index_file}")
                try:
                    index = AnnoyIndex(vector_dim, index_type)
                    index.build(n_trees)
                    index.save(str(index_path))
                    logger.info(f"创建新的空索引成功: {index_file}")
                except Exception as e:
                    logger.error(f"创建新的空索引 {index_file} 失败: {str(e)}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    raise
                continue

            for attempt in range(max_retries):
                try:
                    logger.info(f"尝试加载索引 {index_file} (尝试 {attempt + 1}/{max_retries})")
                    index = AnnoyIndex(vector_dim, index_type)
                    index.load(str(index_path))
                    logger.info(f"成功加载索引: {index_file}")
                    break
                except Exception as e:
                    logger.error(f"加载索引 {index_file} 失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    if attempt < max_retries - 1:
                        logger.info(f"将在 {retry_delay} 秒后重试加载 {index_file}")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"加载索引 {index_file} 失败，已达到最大重试次数")
                        try:
                            logger.info(f"尝试创建新的空索引: {index_file}")
                            index = AnnoyIndex(vector_dim, index_type)
                            index.build(n_trees)
                            index.save(str(index_path))
                            logger.info(f"创建并保存新的空索引成功: {index_file}")
                        except Exception as save_e:
                            logger.error(f"创建新的空索引 {index_file} 失败: {str(save_e)}")
                            logger.error(f"错误堆栈: {traceback.format_exc()}")
                            raise RuntimeError(f"处理索引 {index_file} 完全失败，无法继续")

    except Exception as e:
        logger.error(f"初始化向量索引失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise RuntimeError(f"初始化向量索引失败: {str(e)}")

def create_app() -> FastAPI:
    """创建FastAPI应用的工厂函数"""
    try:
        # 初始化向量索引
        init_vector_indices()
        
        # 初始化BugSearcher
        searcher = BugSearcher()
        set_bug_searcher(searcher)
        
        # 创建Web应用
        return create_web_app()
    except Exception as e:
        logger.error(f"创建应用失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise RuntimeError(f"创建应用失败: {str(e)}")

def start_web_app(
    host: str = None,
    port: int = None,
    reload: bool = False,
    reload_dirs: List[str] = None,
    reload_includes: List[str] = None,
    reload_excludes: List[str] = None,
):
    """启动Web应用"""
    try:
        import signal
        import sys
        
        app = create_app()
        
        # 使用配置中的host和port，如果没有提供参数的话
        web_config = config.get("WEB", {})
        final_host = host or web_config.get("host", "127.0.0.1")
        final_port = port or web_config.get("port", 8010)
        
        # 配置热重载选项
        uvicorn_config = {
            "host": final_host,
            "port": final_port,
            "log_level": "info"
        }
        
        if reload:
            uvicorn_config["reload"] = True
            uvicorn_config["reload_dirs"] = reload_dirs or ["src"]
            uvicorn_config["reload_includes"] = reload_includes or ["*.py"]
            uvicorn_config["reload_excludes"] = reload_excludes or [
                "*.pyc",
                "__pycache__",
            ]
            
        server = uvicorn.Server(uvicorn.Config(app, **uvicorn_config))
            
        # 添加信号处理器
        def handle_exit(signum, frame):
            logger.info("接收到退出信号，正在停止服务器...")
            server.should_exit = True
            
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
            
        # 启动服务器
        server.run()
            
    except Exception as e:
        logger.error(f"启动Web应用失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise RuntimeError(f"启动Web应用失败: {str(e)}")

def main():
    logger.info("正在启动 Web 服务器...")
    try:
        start_web_app(reload=True)  # 启用热更新
    except Exception as e:
        logger.error(f"Web 服务器启动失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise

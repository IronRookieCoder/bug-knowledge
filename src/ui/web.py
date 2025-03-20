from fastapi import FastAPI, Request, Form, UploadFile, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import logging
import webbrowser
import threading
import time
import socket
import traceback
import os
import pickle
import base64
import tempfile
import json
import shutil
from annoy import AnnoyIndex

from src.models.bug_models import BugReport, CodeContext, EnvironmentInfo
from src.retrieval.searcher import BugSearcher
from src.config import AppConfig

logger = logging.getLogger(__name__)

def find_available_port(start_port: int = 8000, max_port: int = 8999) -> int:
    """查找可用端口"""
    for port in range(start_port, max_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"在端口范围 {start_port}-{max_port} 内没有找到可用端口")

def create_web_app(searcher: BugSearcher, config: AppConfig) -> FastAPI:
    """创建Web应用实例"""
    app = FastAPI(title="BUG知识库系统")
    
    # 配置模板和静态文件
    templates = Jinja2Templates(directory=config.web["templates_dir"])
    app.mount("/static", StaticFiles(directory=config.web["static_dir"]), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})
    
    @app.get("/add", response_class=HTMLResponse)
    async def add_page(request: Request):
        return templates.TemplateResponse("add.html", {"request": request})

    @app.post("/add")
    async def add_bug(
        title: str = Form(...),
        description: str = Form(...),
        reproducible: bool = Form(...),
        steps: str = Form(...),
        expected_behavior: str = Form(...),
        actual_behavior: str = Form(...),
        code: str = Form(...),
        file_path: str = Form(...),
        line_start: int = Form(...),
        line_end: int = Form(...),
        language: str = Form(...),
        runtime_env: str = Form(...),
        os_info: str = Form(...),
        network_env: Optional[str] = Form(None),
        error_logs: str = Form(...)
    ):
        try:
            # 创建BugReport对象
            bug_report = BugReport(
                id=f"BUG-{uuid.uuid4().hex[:8]}",
                title=title,
                description=description,
                reproducible=reproducible,
                steps_to_reproduce=steps.split('\n'),
                expected_behavior=expected_behavior,
                actual_behavior=actual_behavior,
                code_context=CodeContext(
                    code=code,
                    file_path=file_path,
                    line_range=(line_start, line_end),
                    language=language
                ),
                error_logs=error_logs,
                environment=EnvironmentInfo(
                    runtime_env=runtime_env,
                    os_info=os_info,
                    network_env=network_env if network_env else None
                ),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 保存到知识库
            searcher.add_bug_report(bug_report)
            return {"status": "success", "bug_id": bug_report.id}
        except Exception as e:
            logger.error(f"添加Bug报告失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"添加Bug报告失败: {str(e)}")

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(request: Request):
        return templates.TemplateResponse("search.html", {"request": request})

    @app.post("/search")
    async def search_bugs(
        query: str = Form(""),
        code: str = Form(""),
        error_log: str = Form(""),
        env_info: str = Form(""),
        n_results: int = Form(5)
    ):
        try:
            results = searcher.search(
                query_text=query,
                code_snippet=code,
                error_log=error_log,
                env_info=env_info,
                n_results=n_results
            )
            return {"results": results}
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={"error": "搜索失败，请重试", "detail": str(e)}
            )
    
    return app

def start_web_app(
    searcher: BugSearcher,
    config: AppConfig,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = True,  # 默认启用热更新
    reload_dirs: List[str] = None,  # 添加监视目录参数
    reload_includes: List[str] = None,  # 添加监视文件类型参数
    reload_excludes: List[str] = None  # 添加排除文件类型参数
):
    """启动Web应用
    
    Args:
        searcher: BugSearcher实例
        config: 应用配置
        host: 服务器主机地址
        port: 服务器端口
        reload: 是否启用热更新
        reload_dirs: 要监视的目录列表
        reload_includes: 要监视的文件类型列表
        reload_excludes: 要排除的文件类型列表
    """
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix='bug_knowledge_')
        
        # 保存向量存储的状态
        vector_store = searcher.vector_store
        indices_dir = os.path.join(temp_dir, "indices")
        os.makedirs(indices_dir, exist_ok=True)
        
        # 保存索引文件
        if vector_store.question_index:
            vector_store.question_index.save(os.path.join(indices_dir, "question.ann"))
        if vector_store.code_index:
            vector_store.code_index.save(os.path.join(indices_dir, "code.ann"))
        if vector_store.log_index:
            vector_store.log_index.save(os.path.join(indices_dir, "log.ann"))
        if vector_store.env_index:
            vector_store.env_index.save(os.path.join(indices_dir, "env.ann"))
        
        # 保存元数据
        with open(os.path.join(temp_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(vector_store.metadata, f, ensure_ascii=False, indent=2)
        
        # 保存配置
        with open(os.path.join(temp_dir, "config.pkl"), 'wb') as f:
            # 只序列化配置对象，不包含 Annoy 索引
            pickle.dump(config, f)
        
        # 将临时目录路径保存到环境变量
        os.environ['BUG_KNOWLEDGE_TEMP_DIR'] = temp_dir
        
        # 查找可用端口
        try:
            available_port = find_available_port(port, port + 99)
            if available_port != port:
                logger.warning(f"端口 {port} 已被占用，使用端口 {available_port}")
                port = available_port
        except RuntimeError as e:
            logger.error(str(e))
            return
        
        # 在后台线程中打开浏览器
        def open_browser():
            time.sleep(2)  # 等待服务器完全启动
            webbrowser.open(f"http://{host}:{port}")
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        # 设置默认的监视配置
        if reload_dirs is None:
            reload_dirs = ["src", "mock"]
        if reload_includes is None:
            reload_includes = ["*.py", "*.html", "*.js", "*.css"]
        if reload_excludes is None:
            reload_excludes = ["*.pyc", "__pycache__", "*.pyo", "*.pyd"]
        
        try:
            # 启动服务器，使用导入字符串而不是应用实例
            uvicorn.run(
                "src.ui.web:create_app",
                host=host,
                port=port,
                reload=reload,
                reload_dirs=reload_dirs,
                reload_delay=0.25,  # 减少重载延迟
                reload_includes=reload_includes,
                reload_excludes=reload_excludes,
                workers=1,  # 单进程模式，确保热重载正常工作
                log_level="info"
            )
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
    except Exception as e:
        logger.error(f"启动Web应用失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise RuntimeError(f"启动Web应用失败: {str(e)}")

# 为热重载创建一个工厂函数
def create_app():
    """创建FastAPI应用的工厂函数"""
    try:
        # 从环境变量获取临时目录路径
        temp_dir = os.environ.get('BUG_KNOWLEDGE_TEMP_DIR')
        if not temp_dir:
            raise RuntimeError("临时目录路径未设置")
        
        # 加载配置
        with open(os.path.join(temp_dir, "config.pkl"), 'rb') as f:
            config = pickle.load(f)
        
        # 创建新的 BugSearcher 实例
        searcher = BugSearcher()
        vector_store = searcher.vector_store
        
        # 加载元数据
        with open(os.path.join(temp_dir, "metadata.json"), 'r', encoding='utf-8') as f:
            vector_store.metadata = json.load(f)
        
        # 加载索引文件
        indices_dir = os.path.join(temp_dir, "indices")
        
        # 创建并加载索引
        vector_store.question_index = AnnoyIndex(384, 'angular')
        vector_store.code_index = AnnoyIndex(384, 'angular')
        vector_store.log_index = AnnoyIndex(384, 'angular')
        vector_store.env_index = AnnoyIndex(384, 'angular')
        
        if os.path.exists(os.path.join(indices_dir, "question.ann")):
            vector_store.question_index.load(os.path.join(indices_dir, "question.ann"))
        if os.path.exists(os.path.join(indices_dir, "code.ann")):
            vector_store.code_index.load(os.path.join(indices_dir, "code.ann"))
        if os.path.exists(os.path.join(indices_dir, "log.ann")):
            vector_store.log_index.load(os.path.join(indices_dir, "log.ann"))
        if os.path.exists(os.path.join(indices_dir, "env.ann")):
            vector_store.env_index.load(os.path.join(indices_dir, "env.ann"))
        
        return create_web_app(searcher, config)
    except Exception as e:
        logger.error(f"创建应用失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise RuntimeError(f"创建应用失败: {str(e)}")

def main():
    logger.info("正在启动 Web 服务器...")
    
    try:
        # 初始化BugSearcher
        bug_searcher = BugSearcher()
        
        start_web_app(
            bug_searcher,
            AppConfig(),
            host="0.0.0.0",
            port=8000,
            reload=True  # 启用热更新
        )
    except Exception as e:
        logger.error(f"Web 服务器启动失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise 
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
    reload: bool = True  # 默认启用热更新
):
    """启动Web应用"""
    try:
        app = create_web_app(searcher, config)
        
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
        
        # 启动服务器
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,  # 启用热更新
            reload_dirs=["src"],  # 监视src目录的变化
            reload_delay=1,  # 延迟1秒后重新加载
            log_level="info"
        )
    except Exception as e:
        logger.error(f"启动Web应用失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise RuntimeError(f"启动Web应用失败: {str(e)}")

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
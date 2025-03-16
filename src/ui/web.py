from fastapi import FastAPI, Request, Form, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from typing import List, Optional
import uuid
from datetime import datetime
import logging
import webbrowser
import threading
import time

from src.models.bug_models import BugReport, CodeContext, EnvironmentInfo
from src.retrieval.searcher import BugSearcher

app = FastAPI(title="BUG知识库系统")
templates = Jinja2Templates(directory="src/ui/templates")
app.mount("/static", StaticFiles(directory="src/ui/static"), name="static")

bug_searcher = BugSearcher()

def open_browser():
    """等待服务器启动后打开浏览器"""
    time.sleep(2)  # 等待服务器完全启动
    webbrowser.open("http://localhost:8000")

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
    bug_searcher.add_bug_report(bug_report)
    return {"status": "success", "bug_id": bug_report.id}

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
    results = bug_searcher.search(
        query_text=query,
        code_snippet=code,
        error_log=error_log,
        env_info=env_info,
        n_results=n_results
    )
    return {"results": results}

def main():
    logger = logging.getLogger(__name__)
    logger.info("正在启动 Web 服务器...")
    
    # 创建打开浏览器的线程
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        uvicorn.run(
            "src.ui.web:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False  # 禁用热重载以避免 Windows 上的问题
        )
    except Exception as e:
        logger.error(f"Web 服务器启动失败: {str(e)}")
        raise 
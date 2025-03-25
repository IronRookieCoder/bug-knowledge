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

    @app.post("/api/search")
    async def search_bugs(
        description: str = Form(""),
        steps_to_reproduce: str = Form(""),
        expected_behavior: str = Form(""),
        actual_behavior: str = Form(""),
        code: str = Form(""),
        error_logs: str = Form(""),
        n_results: int = Form(5)
    ):
        """搜索BUG"""
        try:
            # 记录搜索参数
            logger.info("收到搜索请求:")
            logger.info(f"  - 描述: {description[:50]}..." if len(description) > 50 else f"  - 描述: {description}")
            logger.info(f"  - 重现步骤长度: {len(steps_to_reproduce)}")
            logger.info(f"  - 期望行为长度: {len(expected_behavior)}")
            logger.info(f"  - 实际行为长度: {len(actual_behavior)}")
            logger.info(f"  - 代码长度: {len(code)}")
            logger.info(f"  - 错误日志长度: {len(error_logs)}")
            logger.info(f"  - 请求结果数量: {n_results}")

            # 检查每个字段是否有内容
            has_content = {
                "description": bool(description.strip()),
                "steps": bool(steps_to_reproduce.strip()),
                "expected": bool(expected_behavior.strip()),
                "actual": bool(actual_behavior.strip()),
                "code": bool(code.strip()),
                "log": bool(error_logs.strip())
            }
            
            logger.info(f"搜索字段内容状态: {has_content}")
            
            # 如果没有任何输入
            if not any(has_content.values()):
                logger.warning("没有提供任何搜索条件")
                return {"status": "error", "message": "请至少输入一个搜索条件"}
            
            # 获取搜索结果, 请求更多结果
            actual_n_results = max(n_results * 2, 10)  # 至少请求10个结果
            logger.info(f"执行搜索, 请求 {actual_n_results} 个结果")
            
            results = searcher.search(
                query_text=description,
                code_snippet=code,
                error_log=error_logs,
                env_info="",
                n_results=actual_n_results
            )
            
            logger.info(f"搜索完成, 获得 {len(results)} 个结果")
            
            # 记录详细的搜索结果信息
            if results:
                result_ids = [r["id"] for r in results[:min(10, len(results))]]
                logger.info(f"搜索结果ID: {result_ids}")
                # 记录每个结果的相似度得分
                for i, result in enumerate(results[:min(5, len(results))], 1):
                    logger.info(f"结果 #{i}: ID={result['id']}, 距离={result['distance']}")
            
            return {
                "status": "success",
                "results": results[:n_results]
            }
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"搜索失败: {str(e)}"
            }
    
    return app

def start_web_app(searcher: BugSearcher, config: AppConfig, host: str = "127.0.0.1", 
                port: int = 8000, reload: bool = False, reload_dirs: List[str] = None,
                reload_includes: List[str] = None, reload_excludes: List[str] = None):
    """启动Web应用"""
    try:
        # 获取向量存储实例
        vector_store = searcher.vector_store
        
        # 创建FastAPI应用
        app = create_web_app(searcher, config)
        
        # 配置热重载选项
        reload_config = None
        if reload:
            reload_config = {
                "reload": True,
                "reload_dirs": reload_dirs or ["src"],
                "reload_includes": reload_includes or ["*.py"],
                "reload_excludes": reload_excludes or ["*.pyc", "__pycache__"]
            }
        
        # 启动服务器
        uvicorn.run(
            app,
            host=host,
            port=port,
            **({} if reload_config is None else reload_config)
        )
        
    except Exception as e:
        logger.error(f"启动Web应用失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise RuntimeError(f"启动Web应用失败: {str(e)}")

# 为热重载创建一个工厂函数
def create_app(searcher: BugSearcher, config: AppConfig) -> FastAPI:
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
        
        # 添加重试机制
        max_retries = 3
        retry_delay = 0.5  # 秒
        
        for index_name, index in [
            ("question", vector_store.question_index),
            ("code", vector_store.code_index),
            ("log", vector_store.log_index),
            ("env", vector_store.env_index)
        ]:
            index_path = os.path.join(indices_dir, f"{index_name}.ann")
            if os.path.exists(index_path):
                for attempt in range(max_retries):
                    try:
                        index.load(index_path)
                        logger.info(f"成功加载索引: {index_name}")
                        break
                    except Exception as e:
                        logger.warning(f"加载索引 {index_name} 失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                        else:
                            logger.error(f"加载索引 {index_name} 失败，已达到最大重试次数")
                            # 如果加载失败，创建一个新的空索引
                            index = AnnoyIndex(384, 'angular')
                            index.build(10)
                            logger.info(f"创建新的空索引: {index_name}")
        
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
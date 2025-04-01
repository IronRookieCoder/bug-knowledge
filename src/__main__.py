import argparse
import sys
from pathlib import Path
import time
from src.utils.log import logging
logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.ui.web import start_web_app
from src.retrieval.searcher import BugSearcher
from src.config import AppConfig
from src.crawler.__main__ import main as crawler_main
from src.storage.__main__ import main as storage_main

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

def main():
    parser = argparse.ArgumentParser(description="Bug知识库系统")
    parser.add_argument("--mode", choices=["crawler", "storage", "web", "all"], required=True,
                      help="运行模式：crawler(爬取数据), storage(构建向量索引), web(启动Web服务), all(按顺序执行所有任务)")
    parser.add_argument("--host", default="127.0.0.1", help="Web服务器主机地址")
    parser.add_argument("--port", type=int, default=8010, help="Web服务器端口")
    parser.add_argument("--schedule", action="store_true", help="启用计划运行模式")  # 支持计划运行模式
    parser.add_argument("--hour", type=int, default=2, help="任务执行的小时 (0-23)，默认为2 (凌晨2点)")
    parser.add_argument("--minute", type=int, default=0, help="任务执行的分钟 (0-59)，默认为0")
    parser.add_argument("--interval", type=int, help="任务执行的间隔时间（小时），与 --hour/--minute 互斥")
    
    args = parser.parse_args()

    # 参数校验：确保用户不能同时指定 --hour/--minute 和 --interval
    if args.hour is not None and args.minute is not None and args.interval is not None:
        raise ValueError("不能同时指定 --hour/--minute 和 --interval，请选择一种调度模式。")

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
    
    def run_task():
        if args.mode == "all":
            logger("开始执行所有任务...")
            
            # 1. 爬虫任务
            try:
                logger("1. 开始爬取数据...")
                crawler_main()
            except Exception as e:
                logger(f"爬虫任务执行失败: {str(e)}")
            
            # 2. 存储任务
            try:
                logger("2. 开始构建向量索引...")
                storage_main()
            except Exception as e:
                logger(f"向量索引构建失败: {str(e)}")
            
            # 3. Web服务
            try:
                logger("3. 启动Web服务...")
                searcher = BugSearcher()
                start_web_app(
                    searcher=searcher,
                    config=config,
                    host=args.host,
                    port=args.port,
                )
            except Exception as e:
                logger(f"Web服务启动失败: {str(e)}")
                raise  # Web服务失败需要终止程序
        elif args.mode == "crawler":
            logger("开始爬取数据...")
            crawler_main()
        elif args.mode == "storage":
            logger("开始构建向量索引...")
            storage_main()
        elif args.mode == "web":
            logger("启动Web服务...")
            # 初始化搜索器
            searcher = BugSearcher()
            
            # 启动Web应用
            start_web_app(
                searcher=searcher,
                config=config,
                host=args.host,
                port=args.port,
            )

    if args.schedule:
        logger("计划运行模式已启用，任务将按设定周期执行...")
        scheduler = BackgroundScheduler()

        def scheduled_task():
            try:
                logger(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始执行计划任务...")
                run_task()
                logger(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 计划任务执行完成")
            except Exception as e:
                logger(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 计划任务执行失败: {str(e)}")

        if args.interval is not None:
            interval_hours = args.interval
            logger(f"任务将按每 {interval_hours} 小时执行一次。")
            scheduler.add_job(scheduled_task, IntervalTrigger(hours=interval_hours))
        else:
            hour = args.hour
            minute = args.minute
            logger(f"任务将每天 {hour:02d}:{minute:02d} 执行一次。")
            scheduler.add_job(scheduled_task, CronTrigger(hour=hour, minute=minute))

        scheduler.start()
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger("\n检测到退出信号，正在停止调度器...")
            scheduler.shutdown()
            logger("调度器已停止，程序退出。")
    else:
        run_task()  # 单次运行模式

if __name__ == "__main__":
    main()
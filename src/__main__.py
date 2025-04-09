import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import argparse
import time
import os
import threading
from src.utils.log import get_logger

logger = get_logger(__name__)

from src.ui.web import start_web_app
from src.retrieval.searcher import BugSearcher
from src.config import config
from src.crawler.__main__ import main as crawler_main
from src.storage.__main__ import main as storage_main

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


def ensure_directories():
    """确保必要的目录结构存在"""
    paths = [
        config.get("DATABASE_PATH", "data/bugs.db"),
        config.get("VECTOR_STORE")["data_dir"],
        config.get("MODEL")["cache_dir"],
        config.get("LOG")["file"],
        os.environ.get("BUG_KNOWLEDGE_TEMP_DIR", "data/temp")
    ]
    
    for path in paths:
        path = Path(path).resolve()  # 解析为绝对路径
        if any(c in str(path.name) for c in ['*', '?', '[', ']']):  # 检查是否包含通配符
            logger.warning(f"路径包含非法字符: {path}")
            continue
            
        # 针对已存在的路径
        if path.exists():
            if path.is_file():
                # 确保文件的父目录存在
                path.parent.mkdir(parents=True, exist_ok=True)
            continue
            
        # 对于不存在的路径，根据约定判断类型
        # 数据库文件、日志文件通常有特定后缀
        if (path.name.endswith('.db') or 
            path.name.endswith('.sqlite') or 
            path.name.endswith('.sqlite3') or 
            path.name.endswith('.log')):
            # 创建父目录
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # 其他情况视为目录
            path.mkdir(parents=True, exist_ok=True)
    
    logger.info("目录结构初始化完成")


def start_web_server():
    """在主线程中启动Web服务"""
    host = config.get("WEB", {}).get("host")
    port = config.get("WEB", {}).get("port")
    
    # 直接在主线程中启动web服务
    start_web_app(host, port)
    return None


def main():
    parser = argparse.ArgumentParser(description="Bug知识库系统")
    parser.add_argument(
        "--mode",
        choices=["crawler", "storage", "web", "all"],
        required=False,
        default="web",
        help="运行模式：crawler(爬取数据), storage(构建向量索引), web(启动Web服务), all(按顺序执行所有任务)",
    )
    parser.add_argument("--host", help="Web服务器主机地址")
    parser.add_argument("--port", type=int, help="Web服务器端口")
    parser.add_argument("--schedule", action="store_true", help="启用计划运行模式")
    parser.add_argument(
        "--schedule-type",
        choices=["daily", "monthly", "interval"],
        default="daily",
        help="调度类型：daily(每天), monthly(每月), interval(间隔时间)"
    )
    parser.add_argument(
        "--day", type=int, default=1,
        help="月度调度时，任务执行的日期 (1-31)，默认为1号"
    )
    parser.add_argument(
        "--hour", type=int, default=2,
        help="任务执行的小时 (0-23)，默认为2 (凌晨2点)"
    )
    parser.add_argument(
        "--minute", type=int, default=0,
        help="任务执行的分钟 (0-59)，默认为0"
    )
    parser.add_argument(
        "--interval",
        type=int,
        help="当调度类型为interval时，任务执行的间隔时间（小时）"
    )

    args = parser.parse_args()

    # 参数校验：确保参数匹配选择的调度类型
    if args.schedule:
        if args.schedule_type == "interval":
            if args.interval is None:
                raise ValueError("使用间隔时间调度时，必须指定 --interval 参数")
            if args.day != parser.get_default("day") or \
               args.hour != parser.get_default("hour") or \
               args.minute != parser.get_default("minute"):
                raise ValueError(
                    "使用间隔时间调度时，不能指定 --day、--hour 或 --minute 参数"
                )
        elif args.schedule_type in ["daily", "monthly"]:
            if args.interval is not None:
                raise ValueError(
                    f"使用{args.schedule_type}调度时，不能指定 --interval 参数"
                )
            if args.schedule_type == "monthly":
                if not 1 <= args.day <= 31:
                    raise ValueError("月度调度的日期必须在1-31之间")
            elif args.schedule_type == "daily" and args.day != parser.get_default("day"):
                raise ValueError("使用每日调度时，不能指定 --day 参数")

    # 使用命令行参数覆盖配置文件中的值
    if args.host:
        config.update_config("WEB.host", args.host)
    if args.port:
        config.update_config("WEB.port", args.port)

    # 确保必要的目录结构存在
    ensure_directories()

    def run_task():
        if args.mode == "all":
            logger.info("开始执行所有任务...")

            # 1. 爬虫任务
            try:
                logger.info("1. 开始爬取数据...")
                crawler_main()
            except Exception as e:
                logger.error(f"爬虫任务执行失败: {str(e)}")

            # 2. 存储任务
            try:
                logger.info("2. 开始构建向量索引...")
                storage_main()
            except Exception as e:
                logger.error(f"向量索引构建失败: {str(e)}")

            # 3. Web服务
            try:
                logger.info("3. 启动Web服务...")
                start_web_server()
            except Exception as e:
                logger.error(f"Web服务启动失败: {str(e)}")
                raise

        elif args.mode == "crawler":
            logger.info("开始爬取数据...")
            crawler_main()
        elif args.mode == "storage":
            logger.info("开始构建向量索引...")
            storage_main()
        elif args.mode == "web":
            logger.info("启动Web服务...")
            start_web_server()

    if args.schedule:
        logger.info("计划运行模式已启用，任务将按设定周期执行...")
        scheduler = BackgroundScheduler()

        def scheduled_task():
            try:
                logger.info(
                    f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始执行计划任务..."
                )
                run_task()
                logger.info(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 计划任务执行完成")
            except Exception as e:
                logger.error(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 计划任务执行失败: {str(e)}"
                )

        if args.schedule_type == "interval":
            interval_hours = args.interval
            logger.info(f"任务将按每 {interval_hours} 小时执行一次。")
            scheduler.add_job(scheduled_task, IntervalTrigger(hours=interval_hours))
        elif args.schedule_type == "monthly":
            logger.info(f"任务将每月 {args.day} 日 {args.hour:02d}:{args.minute:02d} 执行一次。")
            scheduler.add_job(
                scheduled_task,
                CronTrigger(day=args.day, hour=args.hour, minute=args.minute),
                max_instances=1
            )
        else:  # daily
            logger.info(f"任务将每天 {args.hour:02d}:{args.minute:02d} 执行一次。")
            scheduler.add_job(
                scheduled_task,
                CronTrigger(hour=args.hour, minute=args.minute),
                max_instances=1
            )

        scheduler.start()
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("\n检测到退出信号，正在停止调度器...")
            scheduler.shutdown()
            logger.info("调度器已停止，程序退出。")
    else:
        run_task()  # 单次运行模式


if __name__ == "__main__":
    main()

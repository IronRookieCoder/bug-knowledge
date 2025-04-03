import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from src.config import config

# 获取日志配置
log_config = config.get('LOG', {})
log_level = getattr(logging, log_config.get('level', 'INFO'))

# 设置日志格式
formatter = logging.Formatter(log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

def get_logger(name=None):
    """
    获取logger实例
    :param name: logger名称，如果为None则使用调用者的模块名
    :return: logger实例
    """
    if name is None:
        # 获取调用者的模块名
        import inspect
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__ if module else 'bug_knowledge'
    
    logger = logging.getLogger(name)
    
    # 如果logger已经设置过handler，直接返回
    if logger.handlers:
        return logger
        
    logger.setLevel(log_level)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 创建文件处理器
    file_handler = RotatingFileHandler(
        filename=log_config.get('file', 'logs/bug_knowledge.log'),
        maxBytes=log_config.get('max_size', 10*1024*1024),
        backupCount=log_config.get('backup_count', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# 为了保持向后兼容，创建一个默认的logger实例
logger = get_logger('bug_knowledge')

__all__ = ['logger', 'get_logger']
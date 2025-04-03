import requests
import concurrent.futures
import time
import json
from src.utils.log import logger
from functools import wraps
from typing import TypeVar, Callable, List, Optional, Dict, Any, Union
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 1.0  # 初始重试延迟时间(秒)
    max_delay: float = 10.0  # 最大重试延迟时间(秒)
    exponential_base: float = 2.0  # 指数退避的基数

@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_workers: int = 10  # 最大并发线程数
    chunk_size: int = 5  # 批处理时的分块大小
    request_timeout: float = 30.0  # 请求超时时间(秒)

def with_retry(retry_config: RetryConfig) -> Callable:
    """重试装饰器
    
    Args:
        retry_config: 重试配置
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retry_config.max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt == retry_config.max_retries - 1:
                        logger.error(f"请求失败，已达到最大重试次数 {retry_config.max_retries}。错误: {str(e)}")
                        raise e
                        
                    delay = min(
                        retry_config.retry_delay * (retry_config.exponential_base ** attempt), 
                        retry_config.max_delay
                    )
                    logger.warning(f"请求失败，将在 {delay:.2f} 秒后重试。错误: {str(e)}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class HttpClient:
    """HTTP请求客户端，提供重试和并发控制功能"""
    
    def __init__(self, 
                retry_config: Optional[RetryConfig] = None,
                concurrency_config: Optional[ConcurrencyConfig] = None):
        """
        Args:
            retry_config: 重试配置，如果为None则使用默认配置
            concurrency_config: 并发配置，如果为None则使用默认配置
        """
        self.retry_config = retry_config or RetryConfig()
        self.concurrency_config = concurrency_config or ConcurrencyConfig()
        # Apply retry decorator to request method
        self.request = with_retry(self.retry_config)(self._request)

    def _request(self, 
               method: str, 
               url: str, 
               headers: Optional[Dict[str, str]] = None, 
               params: Optional[Dict[str, Any]] = None,
               json: Optional[Dict[str, Any]] = None,
               **kwargs) -> requests.Response:
        """发送HTTP请求，支持重试机制"""
        kwargs['timeout'] = kwargs.get('timeout', self.concurrency_config.request_timeout)
        logger.debug(f"发送 {method} 请求到 {url}")
        logger.debug(f"请求参数: {params}")
        
        start_time = time.time()
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                **kwargs
            )
            response.raise_for_status()
            
            duration = time.time() - start_time
            logger.debug(f"请求完成，耗时: {duration:.2f}秒，状态码: {response.status_code}")
            return response
            
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(f"请求失败，耗时: {duration:.2f}秒，错误: {str(e)}")
            raise

    def get(self, url: str, **kwargs) -> requests.Response:
        """发送GET请求"""
        return self.request('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """发送POST请求"""
        return self.request('POST', url, **kwargs)

    def concurrent_map(self, 
                      func: Callable[[Any], T], 
                      items: List[Any],
                      *args,
                      **kwargs) -> List[T]:
        """并发执行任务"""
        results = []
        total_items = len(items)
        completed = 0
        
        logger.info(f"开始并发处理 {total_items} 个任务，最大并发数: {self.concurrency_config.max_workers}")
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency_config.max_workers) as executor:
            futures = {
                executor.submit(func, item, *args, **kwargs): item 
                for item in items
            }
            
            for future in concurrent.futures.as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        if isinstance(result, list):
                            results.extend(result)
                        else:
                            results.append(result)
                    completed += 1
                    logger.debug(f"任务进度: {completed}/{total_items} ({completed/total_items*100:.1f}%)")
                except Exception as e:
                    logger.error(f"处理项目 {item} 时发生错误: {str(e)}")
        
        duration = time.time() - start_time
        logger.info(f"并发处理完成，总耗时: {duration:.2f}秒，成功处理: {len(results)}/{total_items}")
        return results

    def chunk_concurrent_map(self, 
                           func: Callable[[List[Any]], List[T]], 
                           items: List[Any],
                           chunk_size: Optional[int] = None,
                           *args, 
                           **kwargs) -> List[T]:
        """分块并发执行任务"""
        if not items:
            return []
            
        chunk_size = chunk_size or self.concurrency_config.chunk_size
        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
        total_chunks = len(chunks)
        completed_chunks = 0
        results = []
        
        logger.info(f"开始分块并发处理，共 {len(items)} 个项目，分为 {total_chunks} 个批次，"
                   f"每批次 {chunk_size} 个，最大并发数: {self.concurrency_config.max_workers}")
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency_config.max_workers) as executor:
            futures = {
                executor.submit(func, chunk, *args, **kwargs): chunk 
                for chunk in chunks
            }
            
            for future in concurrent.futures.as_completed(futures):
                chunk = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        if isinstance(result, list):
                            results.extend(result)
                        else:
                            results.append(result)
                    completed_chunks += 1
                    logger.debug(f"批次进度: {completed_chunks}/{total_chunks} "
                               f"({completed_chunks/total_chunks*100:.1f}%)")
                except Exception as e:
                    logger.error(f"处理批次 {completed_chunks + 1} 时发生错误，"
                               f"批次大小: {len(chunk)}，错误: {str(e)}")
        
        duration = time.time() - start_time
        logger.info(f"分块处理完成，总耗时: {duration:.2f}秒，"
                   f"成功处理项目数: {len(results)}/{len(items)}")
        return results

# 全局HTTP客户端实例（使用默认配置）
http_client = HttpClient()
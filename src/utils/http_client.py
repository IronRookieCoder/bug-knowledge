import requests
import concurrent.futures
import time
import json
from src.utils.log import get_logger
from functools import wraps
from typing import TypeVar, Callable, List, Optional, Dict, Any, Union
from dataclasses import dataclass

logger = get_logger(__name__)

T = TypeVar("T")


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

    max_workers: int = 50  # 最大并发线程数
    chunk_size: int = 10  # 批处理时的分块大小
    request_timeout: float = 60.0  # 请求超时时间(秒)


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
                        logger.error(
                            f"请求失败，已达到最大重试次数 {retry_config.max_retries}。错误: {str(e)}"
                        )
                        raise e

                    delay = min(
                        retry_config.retry_delay
                        * (retry_config.exponential_base**attempt),
                        retry_config.max_delay,
                    )
                    logger.warning(
                        f"请求失败，将在 {delay:.2f} 秒后重试。错误: {str(e)}"
                    )
                    time.sleep(delay)
            return None

        return wrapper

    return decorator


class HttpClient:
    """HTTP请求客户端，提供重试和并发控制功能"""

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        concurrency_config: Optional[ConcurrencyConfig] = None,
    ):
        """
        Args:
            retry_config: 重试配置，如果为None则使用默认配置
            concurrency_config: 并发配置，如果为None则使用默认配置
        """
        self.retry_config = retry_config or RetryConfig()
        self.concurrency_config = concurrency_config or ConcurrencyConfig()
        # Apply retry decorator to request method
        self.request = with_retry(self.retry_config)(self._request)

    def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> requests.Response:
        """发送HTTP请求，支持重试机制"""
        kwargs["timeout"] = kwargs.get(
            "timeout", self.concurrency_config.request_timeout
        )
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
                **kwargs,
            )
            response.raise_for_status()

            duration = time.time() - start_time
            logger.debug(
                f"请求完成，耗时: {duration:.2f}秒，状态码: {response.status_code}"
            )
            return response

        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(f"请求失败，耗时: {duration:.2f}秒，错误: {str(e)}")
            raise

    def get(self, url: str, **kwargs) -> requests.Response:
        """发送GET请求"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """发送POST请求"""
        return self.request("POST", url, **kwargs)

    def concurrent_map(
        self, func: Callable[[Any], T], items: List[Any], *args, **kwargs
    ) -> List[T]:
        """并发执行任务"""
        if not items:
            return []
            
        # 检查items是否为列表，如果不是，转换为列表
        if not isinstance(items, list):
            logger.warning(f"输入items不是列表类型，而是 {type(items)}，尝试转换")
            try:
                items = list(items)
            except:
                logger.error(f"无法将输入 {type(items)} 转换为列表")
                return []
            
        results = []
        total_items = len(items)
        completed = 0

        logger.info(f"开始并发处理 {total_items} 个任务，最大并发数: {self.concurrency_config.max_workers}")
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency_config.max_workers) as executor:
            futures = {}
            for item in items:
                try:
                    # 优化项目处理逻辑
                    processed_item = None
                    
                    # 如果是字典类型且不是None，进行深拷贝
                    if isinstance(item, dict) and item is not None:
                        # 使用深拷贝确保不会修改原始对象
                        try:
                            processed_item = json.loads(json.dumps(item))
                        except (TypeError, json.JSONDecodeError) as e:
                            logger.warning(f"无法深拷贝字典项目: {e}")
                            # 备选方案：使用浅拷贝
                            processed_item = item.copy()
                    
                    # 如果是其他可变类型（如列表、集合），使用浅拷贝
                    elif isinstance(item, list) or isinstance(item, set) or isinstance(item, tuple):
                        processed_item = list(item) if isinstance(item, (list, tuple)) else set(item)
                    
                    # 字符串或不可变类型，直接使用
                    else:
                        processed_item = item
                        
                    futures[executor.submit(func, processed_item, *args, **kwargs)] = processed_item
                except Exception as e:
                    logger.error(f"创建任务时发生错误: {str(e)}, 项目类型: {type(item)}, 项目值: {repr(item)[:100]}")
                    continue

            for future in concurrent.futures.as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    
                    # 改进结果处理逻辑
                    if result is not None:
                        # 判断结果是否为基本类型或已知容器类型之外的自定义类型
                        is_custom_object = (
                            not isinstance(result, (dict, list, tuple, set, str, int, float, bool))
                            and result.__class__.__module__ != 'builtins'
                        )
                        
                        if is_custom_object:
                            # 自定义对象（如CodeSnippet）直接添加，不要尝试展平
                            logger.debug(f"添加自定义类型对象: {type(result).__name__}")
                            results.append(result)
                            
                        # 字典类型的结果，作为一个整体添加到结果中
                        elif isinstance(result, dict):
                            logger.debug(f"添加字典类型结果")
                            results.append(result)
                        
                        # 列表类型的结果，取决于是否需要展平
                        elif isinstance(result, (list, tuple)):
                            # 检查是否有自定义对象
                            has_custom_objects = any(
                                not isinstance(x, (dict, list, tuple, set, str, int, float, bool, type(None)))
                                and x.__class__.__module__ != 'builtins'
                                for x in result if x is not None
                            )
                            
                            # 检查是否全是基本类型
                            all_basic_types = all(
                                isinstance(x, (int, float, str, bool, type(None))) 
                                for x in result if x is not None
                            )
                            
                            if all_basic_types or has_custom_objects:
                                # 如果是基本类型列表或包含自定义对象，作为整体添加
                                logger.debug(f"添加含自定义对象的列表或基本类型列表: {len(result)}个元素")
                                results.append(result)
                            else:
                                # 其他复杂类型列表，展平处理
                                logger.debug(f"展平复杂类型列表: {len(result)}个元素")
                                results.extend(list(result))
                        else:
                            # 其他类型直接添加
                            results.append(result)
                    
                    completed += 1
                    if completed % 10 == 0 or completed == total_items:
                        logger.debug(f"任务进度: {completed}/{total_items} ({completed/total_items*100:.1f}%)")
                except Exception as e:
                    logger.error(f"处理项目时发生错误: {str(e)}, 项目类型: {type(item)}")
                    continue

        duration = time.time() - start_time
        logger.info(f"并发处理完成，总耗时: {duration:.2f}秒，成功处理: {len(results)}/{total_items}")
        return results

    def chunk_concurrent_map(
        self,
        func: Callable[[List[Any]], List[T]],
        items: List[Any],
        chunk_size: Optional[int] = None,
        *args,
        **kwargs,
    ) -> List[T]:
        """分块并发执行任务"""
        if not items:
            return []

        # 确保items是列表类型
        if not isinstance(items, list):
            logger.error(f"输入items必须是列表类型，当前类型: {type(items)}")
            return []

        chunk_size = chunk_size or self.concurrency_config.chunk_size
        chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
        total_chunks = len(chunks)
        completed_chunks = 0
        results = []

        logger.info(
            f"开始分块并发处理，共 {len(items)} 个项目，分为 {total_chunks} 个批次，"
            f"每批次 {chunk_size} 个，最大并发数: {self.concurrency_config.max_workers}"
        )
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.concurrency_config.max_workers
        ) as executor:
            futures = {}
            
            # 提交任务时进行类型检查
            for chunk in chunks:
                if not isinstance(chunk, list):
                    logger.error(f"块必须是列表类型，当前类型: {type(chunk)}")
                    continue
                try:
                    futures[executor.submit(func, chunk, *args, **kwargs)] = chunk
                except Exception as e:
                    logger.error(f"提交任务时发生错误: {str(e)}, 块大小: {len(chunk)}")
                    continue

            # 处理任务结果
            for future in concurrent.futures.as_completed(futures):
                chunk = futures[future]
                try:
                    result = future.result()
                    
                    # 类型检查和结果处理
                    if result is not None:
                        if isinstance(result, list):
                            # 过滤掉None值
                            valid_results = [item for item in result if item is not None]
                            results.extend(valid_results)
                            logger.debug(f"成功处理 {len(valid_results)}/{len(result)} 个项目")
                        else:
                            logger.warning(f"任务返回值不是列表类型: {type(result)}")
                    
                    completed_chunks += 1
                    if completed_chunks % 5 == 0 or completed_chunks == total_chunks:
                        logger.debug(
                            f"批次进度: {completed_chunks}/{total_chunks} "
                            f"({completed_chunks/total_chunks*100:.1f}%)"
                        )
                except Exception as e:
                    logger.error(
                        f"处理批次 {completed_chunks + 1} 时发生错误，"
                        f"批次大小: {len(chunk)}，错误: {str(e)}"
                    )
                    if self.retry_config.max_retries > 0:
                        logger.info(f"尝试重试该批次处理")
                        try:
                            retry_result = func(chunk, *args, **kwargs)
                            if isinstance(retry_result, list):
                                results.extend([item for item in retry_result if item is not None])
                        except Exception as retry_e:
                            logger.error(f"重试失败: {str(retry_e)}")

        duration = time.time() - start_time
        logger.info(
            f"分块处理完成，总耗时: {duration:.2f}秒，"
            f"成功处理项目数: {len(results)}/{len(items)}"
        )
        return results


# 全局HTTP客户端实例（使用默认配置）
http_client = HttpClient()

import logging
from typing import Dict, List, Optional, Union
from unidiff import PatchSet
from unidiff.errors import UnidiffParseError

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

PreprocessedDiffResult = Dict[str, Union[str, List[str]]]


def preprocess_bug_diffs(code_diffs_text: str, encoding: str = 'utf-8') -> Optional[PreprocessedDiffResult]:
    """
    预处理包含一个或多个文件diff的文本，提取聚合的新增代码、删除代码和涉及的文件列表。

    Args:
        code_diffs_text: 包含标准统一diff格式（unified diff format）的字符串。
                         可能包含多个文件的diff信息。
        encoding: diff 文本的编码，默认为 'utf-8'。

    Returns:
        一个包含预处理结果的字典，格式如下：
        {
            'aggregated_added_code': str,  # 所有新增行的聚合文本，保留换行符
            'aggregated_removed_code': str, # 所有删除行的聚合文本，保留换行符
            'changed_files': List[str]      # 发生变更的文件路径列表 (去重并排序)
        }
        如果解析失败、输入为空或无效，则返回 None。
    """
    if not code_diffs_text or not code_diffs_text.strip():
        logging.warning("Input code_diffs_text is empty or whitespace only.")
        return None

    added_lines: List[str] = []
    removed_lines: List[str] = []
    changed_files: set[str] = set()  # 使用set去重

    try:
        # 使用 io.StringIO 包装字符串，unidiff 可以更好地处理内存中的字符串
        # 并指定编码
        patch_set = PatchSet.from_string(code_diffs_text)

        for patched_file in patch_set:
            # --- 改进文件路径提取逻辑 ---
            # 优先使用 target_file 或 source_file，并去除常见的 a/ b/ 前缀
            file_path = None
            if patched_file.target_file and patched_file.target_file != '/dev/null':
                # 通常 target_file 是 'b/path/to/file'
                file_path = patched_file.target_file
                if file_path.startswith('b/'):
                    file_path = file_path[2:]
            elif patched_file.source_file and patched_file.source_file != '/dev/null':
                # 如果 target 是 /dev/null (文件删除)，使用 source_file
                file_path = patched_file.source_file
                if file_path.startswith('a/'):
                    file_path = file_path[2:]
            elif patched_file.path:  # 作为最后的备选
                file_path = patched_file.path

            if file_path:
                changed_files.add(file_path)
            else:
                # 如果无法确定文件名，记录一个警告，但继续处理内容
                logging.warning(
                    f"Could not reliably determine file path for a patch section. Headers: source='{patched_file.source_file}', target='{patched_file.target_file}'")

            # 跳过二进制文件的diff
            if patched_file.is_binary_file:
                logging.debug(
                    f"Skipping binary file diff: {file_path if file_path else 'Unknown'}")
                continue

            # 遍历文件中的每个 hunk (代码块变更)
            for hunk in patched_file:
                # 遍历 hunk 中的每一行
                for line in hunk:
                    # line.value 包含原始行内容 (例如 '+ line content\n')
                    # 我们移除第一个字符 ('+' or '-') 和行尾的换行符。
                    # 后续的 "\n".join 会重新添加必要的换行符以保持多行结构。
                    clean_line_content = line.value[1:].rstrip('\n\r')

                    if line.is_added:
                        added_lines.append(clean_line_content)
                    elif line.is_removed:
                        removed_lines.append(clean_line_content)
                    # elif line.is_context: # 上下文行被忽略

    # 捕获特定的解析错误和编码错误
    except UnidiffParseError as e:
        logging.error(f"Failed to parse diff text: {e}")
        return None
    except UnicodeDecodeError as e:
        logging.error(
            f"Failed to decode diff text with encoding '{encoding}': {e}")
        return None
    except Exception as e:
        # 捕获其他意外错误
        logging.exception(
            f"An unexpected error occurred during diff processing: {e}")
        # 使用 logging.exception 会记录堆栈跟踪，更有助于调试
        return None

    # --- 确保即使没有变更行，也返回有效结构 ---
    # 将收集到的行用换行符连接起来
    aggregated_added_code = "\n".join(added_lines)
    aggregated_removed_code = "\n".join(removed_lines)

    # 确保返回定义的结构
    return {
        'aggregated_added_code': aggregated_added_code,
        'aggregated_removed_code': aggregated_removed_code,
        'changed_files': sorted(list(changed_files))  # 转换为列表并排序
    }
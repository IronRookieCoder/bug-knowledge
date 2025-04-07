import sqlite3
import json
from pathlib import Path
import traceback
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from contextlib import contextmanager
from src.utils.log import get_logger

logger = get_logger(__name__)


class BugDatabase:
    _instance = None
    _initialized = False

    def __new__(cls, db_path: str = "data/bugs.db"):
        if cls._instance is None:
            cls._instance = super(BugDatabase, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "data/bugs.db"):
        if not self._initialized:
            self.db_path = Path(db_path)
            self._ensure_db_exists()
            self._initialized = True

    def _ensure_db_exists(self):
        """确保数据库和表存在"""
        db_dir = self.db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 创建bug报告表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bug_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bug_id TEXT UNIQUE,
                    summary TEXT,
                    description TEXT,
                    file_paths TEXT,
                    code_diffs TEXT,
                    aggregated_added_code TEXT,
                    aggregated_removed_code TEXT,
                    test_steps TEXT,
                    expected_result TEXT,
                    actual_result TEXT,
                    log_info TEXT,
                    severity TEXT,
                    is_reappear INTEGER,
                    environment TEXT,
                    root_cause TEXT,
                    fix_solution TEXT,
                    related_issues TEXT,
                    fix_person TEXT,
                    create_at TEXT,
                    fix_date TEXT,
                    reopen_count INTEGER,
                    handlers TEXT,
                    project_id TEXT
                )
            """
            )

            conn.commit()

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        with self.get_connection() as conn:
            try:
                yield conn
            except Exception as e:
                conn.rollback()
                raise
            else:
                conn.commit()

    def bug_id_exists(self, bug_id: str) -> bool:
        """检查bug_id是否已存在"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM bug_reports WHERE bug_id = ?", (bug_id,)
                )
                return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error(f"检查bug_id是否存在失败: {str(e)}")
            return False

    def get_bug_report_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """通过id获取bug报告"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bug_reports WHERE id = ?", (id,))
                row = cursor.fetchone()

                if row:
                    # 获取列名
                    columns = [description[0] for description in cursor.description]
                    result = dict(zip(columns, row))

                    # 处理JSON字段
                    json_fields = [
                        "file_paths",
                        "code_diffs",
                        "related_issues",
                        "handlers",
                    ]
                    for field in json_fields:
                        if result.get(field):
                            try:
                                result[field] = json.loads(result[field])
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析JSON字段 {field} 的值")

                    return result
                return None
        except Exception as e:
            logger.error(f"通过id获取bug报告失败: {str(e)}")
            return None

    def add_bug_report(self, bug_id: str, bug_data: Dict[str, Any]) -> bool:
        """添加bug报告到数据库"""
        try:
            # 检查bug_id是否已存在
            if self.bug_id_exists(bug_id):
                logger.warning(f"bug_id {bug_id} 已存在")
                return False

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 准备数据
                columns = ["bug_id"]
                values = [bug_id]
                for key, value in bug_data.items():
                    if key != "bug_id":  # 跳过bug_id，因为已经单独处理
                        columns.append(key)
                        # 处理列表和字典类型的值
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value, ensure_ascii=False)
                        values.append(value)

                # 构建SQL语句
                columns_str = ", ".join(columns)
                placeholders = ", ".join(["?" for _ in values])
                sql = f"""
                    INSERT INTO bug_reports ({columns_str})
                    VALUES ({placeholders})
                """

                # 执行插入
                cursor.execute(sql, values)
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"添加bug报告失败: {str(e)}")
            return False

    def get_bug_report(self, bug_id: str) -> Optional[Dict[str, Any]]:
        """获取指定bug报告"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bug_reports WHERE bug_id = ?", (bug_id,))
                row = cursor.fetchone()

                if row:
                    # 获取列名
                    columns = [description[0] for description in cursor.description]
                    result = dict(zip(columns, row))

                    # 处理JSON字段
                    json_fields = [
                        "file_paths",
                        "code_diffs",
                        "related_issues",
                        "handlers",
                    ]
                    for field in json_fields:
                        if result.get(field):
                            try:
                                result[field] = json.loads(result[field])
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析JSON字段 {field} 的值")

                    return result
                return None
        except Exception as e:
            logger.error(f"获取bug报告失败: {str(e)}")
            return None

    def get_all_bug_reports(self) -> List[Dict[str, Any]]:
        """获取所有bug报告"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bug_reports")
                rows = cursor.fetchall()

                if rows:
                    # 获取列名
                    columns = [description[0] for description in cursor.description]
                    results = []

                    for row in rows:
                        result = dict(zip(columns, row))

                        # 处理JSON字段
                        json_fields = [
                            "file_paths",
                            "code_diffs",
                            "related_issues",
                            "handlers",
                        ]
                        for field in json_fields:
                            if result.get(field):
                                try:
                                    result[field] = json.loads(result[field])
                                except json.JSONDecodeError:
                                    logger.warning(f"无法解析JSON字段 {field} 的值")

                        results.append(result)

                    return results
                return []
        except Exception as e:
            logger.error(f"获取所有bug报告失败: {str(e)}")
            return []

    def update_bug_report(self, bug_id: str, data: Dict[str, Any]) -> bool:
        """更新bug报告"""
        try:
            # 检查bug_id是否存在
            if not self.bug_id_exists(bug_id):
                logger.warning(f"bug_id {bug_id} 不存在")
                return False

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 准备更新数据
                updates = []
                values = []
                for key, value in data.items():
                    # 跳过id和bug_id字段
                    if key not in ["id", "bug_id"]:
                        updates.append(f"{key} = ?")
                        # 处理列表和字典类型的值
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value, ensure_ascii=False)
                        values.append(value)

                # 构建SQL语句
                updates_str = ", ".join(updates)
                sql = f"UPDATE bug_reports SET {updates_str} WHERE bug_id = ?"

                # 执行更新
                cursor.execute(sql, values + [bug_id])
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"更新bug报告失败: {str(e)}")
            return False

    def delete_bug_report(self, bug_id: str) -> bool:
        """删除bug报告"""
        try:
            # 检查bug_id是否存在
            if not self.bug_id_exists(bug_id):
                logger.warning(f"bug_id {bug_id} 不存在")
                return False

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM bug_reports WHERE bug_id = ?", (bug_id,))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"删除bug报告失败: {str(e)}")
            return False

    def keyword_search(
        self, query_text: str, n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """使用关键词在数据库中搜索bug报告

        Args:
            query_text: 查询文本
            n_results: 返回结果数量

        Returns:
            List[Dict[str, Any]]: 匹配的bug报告列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 生成查询词列表
                search_terms = [
                    word.strip().lower() for word in query_text.split() if word.strip()
                ]
                if not search_terms:
                    return []

                # 构建SQL查询条件
                conditions = []
                params = []
                search_fields = [
                    "summary",
                    "code_diffs",
                    "test_steps",
                    "expected_result",
                    "actual_result",
                    "log_info",
                    "environment",
                ]

                for term in search_terms:
                    field_conditions = []
                    for field in search_fields:
                        field_conditions.append(f"LOWER({field}) LIKE ?")
                        params.append(f"%{term}%")
                    conditions.append("(" + " OR ".join(field_conditions) + ")")

                # 组合所有条件
                where_clause = " AND ".join(conditions)

                # 计算每条记录匹配的关键词数量作为相关度分数
                score_conditions = []
                for field in search_fields:
                    for term in search_terms:
                        score_conditions.append(
                            f"CASE WHEN LOWER({field}) LIKE ? THEN 1 ELSE 0 END"
                        )
                        params.append(f"%{term}%")

                sql = f"""
                    SELECT *, ({' + '.join(score_conditions)}) as score
                    FROM bug_reports 
                    WHERE {where_clause}
                    ORDER BY score DESC
                    LIMIT ?
                """
                params.extend([n_results])

                cursor.execute(sql, params)
                rows = cursor.fetchall()

                if not rows:
                    return []

                # 获取列名
                columns = [description[0] for description in cursor.description]
                results = []

                for row in rows:
                    result = dict(zip(columns, row))

                    # 处理JSON字段
                    json_fields = [
                        "file_paths",
                        "code_diffs",
                        "related_issues",
                        "handlers",
                    ]
                    for field in json_fields:
                        if result.get(field):
                            try:
                                result[field] = json.loads(result[field])
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析JSON字段 {field} 的值")

                    # 移除score字段，因为这只是用于排序
                    result.pop("score", None)
                    results.append(result)

                return results

        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return []

    def get_bug_reports(
        self,
        offset: int = 0,
        limit: int = 10,
        project_id: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """获取bug报告列表，支持分页和过滤

        Args:
            offset: 偏移量
            limit: 返回数量限制
            project_id: 项目ID过滤
            severity: 严重程度过滤

        Returns:
            Tuple[int, List[Dict[str, Any]]]: (总数, bug列表)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 构建WHERE子句和参数
                conditions = []
                params = []
                if project_id:
                    conditions.append("project_id = ?")
                    params.append(project_id)
                if severity:
                    conditions.append("severity = ?")
                    params.append(severity)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # 获取总数
                count_sql = f"SELECT COUNT(*) FROM bug_reports WHERE {where_clause}"
                cursor.execute(count_sql, params)
                total = cursor.fetchone()[0]

                # 获取分页数据
                sql = f"""
                    SELECT * FROM bug_reports 
                    WHERE {where_clause}
                    ORDER BY create_at DESC
                    LIMIT ? OFFSET ?
                """
                cursor.execute(sql, params + [limit, offset])
                rows = cursor.fetchall()

                if not rows:
                    return total, []

                # 获取列名
                columns = [description[0] for description in cursor.description]
                results = []

                for row in rows:
                    result = dict(zip(columns, row))

                    # 处理JSON字段
                    json_fields = [
                        "file_paths",
                        "code_diffs",
                        "related_issues",
                        "handlers",
                    ]
                    for field in json_fields:
                        if result.get(field):
                            try:
                                result[field] = json.loads(result[field])
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析JSON字段 {field} 的值")

                    results.append(result)

                return total, results

        except Exception as e:
            logger.error(f"获取bug报告列表失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return 0, []

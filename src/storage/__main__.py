from typing import List, Dict, Any
from src.storage.vector_store import VectorStore
from src.storage.database import BugDatabase
from src.vectorization.vectorizers import HybridVectorizer
from src.utils.log import get_logger

logger = get_logger(__name__)


def main():
    # 初始化组件
    vector_store = VectorStore(data_dir="data/annoy")
    db = BugDatabase()
    vectorizer = HybridVectorizer()

    # 从数据库获取所有bug报告
    bug_reports = db.get_all_bug_reports()
    logger.info(f"从数据库读取到 {len(bug_reports)} 条bug报告")

    # 处理每个bug报告
    for report in bug_reports:
        try:
            # 生成各个字段的向量
            vectors = {
                "summary_vector": vectorizer.summary_vectorizer.vectorize(
                    report.get("summary", "")
                ),
                "code_vector": vectorizer.code_vectorizer.vectorize(
                    report.get("code", "")
                ),
                "test_info_vector": vectorizer.test_vectorizer.vectorize(
                    {
                        "test_steps": report.get("test_steps", ""),
                        "expected_result": report.get("expected_result", ""),
                        "actual_result": report.get("actual_result", ""),
                    }
                ),
                "log_info_vector": vectorizer.log_vectorizer.vectorize(
                    report.get("log_info", "")
                ),
                "environment_vector": vectorizer.environment_vectorizer.vectorize(
                    report.get("environment", "")
                ),
            }

            # 添加到向量存储
            vector_store.add_bug_report(report, vectors)
            logger.info(f"成功处理bug报告: {report.get('bug_id')}")

        except Exception as e:
            logger.error(f"处理bug报告 {report.get('bug_id')} 时发生错误: {str(e)}")
            continue

    # 保存所有索引
    vector_store._save_indices()  # 确保调用符合接口设计
    logger.info("向量索引构建完成")


if __name__ == "__main__":
    main()

import json
import logging
from pathlib import Path
from src.storage.database import BugDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_from_json_to_sqlite(json_path: str = "data/annoy/metadata.json", db_path: str = "data/bugs.db"):
    """从 JSON 迁移到 SQLite"""
    try:
        # 读取 JSON 文件
        json_path = Path(json_path)
        if not json_path.exists():
            logger.error(f"JSON 文件不存在: {json_path}")
            return False
            
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 创建数据库实例
        db = BugDatabase(db_path)
        
        # 迁移数据
        success_count = 0
        error_count = 0
        
        for bug_id, bug_data in metadata.get('bugs', {}).items():
            try:
                if db.add_bug_report(bug_id, bug_data):
                    success_count += 1
                else:
                    error_count += 1
                    logger.error(f"迁移 bug {bug_id} 失败")
            except Exception as e:
                error_count += 1
                logger.error(f"迁移 bug {bug_id} 时发生错误: {str(e)}")
        
        logger.info(f"迁移完成: 成功 {success_count} 条, 失败 {error_count} 条")
        return error_count == 0
        
    except Exception as e:
        logger.error(f"迁移过程发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    # 执行迁移
    success = migrate_from_json_to_sqlite()
    if success:
        logger.info("数据迁移成功完成")
    else:
        logger.error("数据迁移失败") 
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict
import uuid
from pathlib import Path

# 模拟数据模板
BUG_TITLES = [
    "数据库连接超时问题",
    "用户登录失败",
    "文件上传大小限制异常",
    "内存泄漏警告",
    "API 响应延迟",
    "缓存更新失败",
    "并发请求处理错误",
    "日志记录异常",
    "数据同步失败",
    "权限验证问题"
]

CODE_SNIPPETS = [
    """def connect_db():
    try:
        connection = psycopg2.connect(
            dbname="testdb",
            user="admin",
            password="secret",
            host="localhost",
            port="5432"
        )
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        raise""",
    
    """async def login_user(username: str, password: str):
    user = await db.users.find_one({"username": username})
    if not user or not verify_password(password, user["password"]):
        raise AuthenticationError("用户名或密码错误")
    return generate_token(user)""",
    
    """def upload_file(file: UploadFile):
    if file.size > MAX_FILE_SIZE:
        raise FileTooLargeError("文件大小超过限制")
    return save_file(file)""",
    
    """class DataProcessor:
    def __init__(self):
        self.cache = {}
    
    def process_data(self, data):
        self.cache[data.id] = data
        return self.cache""",
    
    """@app.get("/api/data")
async def get_data():
    await asyncio.sleep(2)  # 模拟延迟
    return {"status": "success"}""",
    
    """def update_cache(key: str, value: Any):
    try:
        redis_client.set(key, value)
    except Exception as e:
        logger.error(f"缓存更新失败: {str(e)}")
        raise""",
    
    """async def handle_request(request):
    async with semaphore:
        return await process_request(request)""",
    
    """def log_error(error: Exception):
    try:
        with open("error.log", "a") as f:
            f.write(f"{datetime.now()}: {str(error)}\\n")
    except Exception as e:
        print(f"日志记录失败: {str(e)}")""",
    
    """def sync_data(source: str, target: str):
    data = fetch_data(source)
    try:
        save_data(target, data)
    except Exception as e:
        logger.error(f"数据同步失败: {str(e)}")
        raise""",
    
    """def check_permission(user: User, resource: str):
    if not user.has_permission(resource):
        raise PermissionError("没有访问权限")
    return True"""
]

ERROR_MESSAGES = [
    "Connection timeout after 30 seconds",
    "Invalid credentials provided",
    "File size exceeds maximum limit of 10MB",
    "Memory usage exceeds 80% threshold",
    "API response time exceeds 500ms",
    "Failed to update Redis cache",
    "Concurrent request limit exceeded",
    "Failed to write to log file",
    "Data synchronization timeout",
    "Insufficient permissions for operation"
]

ENVIRONMENT_INFO = [
    {
        "runtime_env": "Python 3.8.10",
        "os_info": "Ubuntu 20.04 LTS",
        "network_env": "内网环境"
    },
    {
        "runtime_env": "Node.js 14.17.0",
        "os_info": "Windows 10 Pro",
        "network_env": "公网环境"
    },
    {
        "runtime_env": "Java 11.0.12",
        "os_info": "CentOS 7",
        "network_env": "内网环境"
    },
    {
        "runtime_env": "Python 3.9.7",
        "os_info": "macOS 11.6",
        "network_env": "开发环境"
    },
    {
        "runtime_env": "Go 1.16.7",
        "os_info": "Windows Server 2019",
        "network_env": "生产环境"
    },
    {
        "runtime_env": "Python 3.7.9",
        "os_info": "Debian 10",
        "network_env": "测试环境"
    },
    {
        "runtime_env": "Node.js 16.13.0",
        "os_info": "Ubuntu 18.04 LTS",
        "network_env": "内网环境"
    },
    {
        "runtime_env": "Java 8.0.301",
        "os_info": "Windows 10 Enterprise",
        "network_env": "开发环境"
    },
    {
        "runtime_env": "Python 3.10.0",
        "os_info": "macOS 12.0",
        "network_env": "测试环境"
    },
    {
        "runtime_env": "Go 1.17.5",
        "os_info": "CentOS 8",
        "network_env": "生产环境"
    }
]

SEVERITY_LEVELS = ["P0", "P1", "P2", "P3"]
HANDLERS = ["张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十"]
PROJECT_IDS = ["PROJ-001", "PROJ-002", "PROJ-003", "PROJ-004", "PROJ-005"]

def generate_mock_data(count: int = 10) -> List[Dict]:
    """生成指定数量的模拟数据"""
    mock_data = []
    for i in range(count):
        # 生成随机时间戳（在过去30天内）
        create_at = datetime.now() - timedelta(days=random.randint(0, 30))
        fix_date = datetime.now() - timedelta(days=random.randint(0, 30))

        # 随机选择模板
        title_idx = random.randint(0, len(BUG_TITLES) - 1)
        code_idx = random.randint(0, len(CODE_SNIPPETS) - 1)
        env_idx = random.randint(0, len(ENVIRONMENT_INFO) - 1)
        
        # 生成随机处理人员
        num_handlers = random.randint(1, 3)
        handlers = random.sample(HANDLERS, num_handlers)
        
        # 生成随机相关问题
        num_related = random.randint(0, 2)
        related_issues = [f"BUG-{uuid.uuid4().hex[:8]}" for _ in range(num_related)]
        
        bug_report = {
            "bug_id": f"BUG-{uuid.uuid4().hex[:8]}",
            "summary": BUG_TITLES[title_idx],
            "file_paths": [f"src/features/feature_{i+1}.py"],
            "code_diffs": [f"diff --git a/src/features/feature_{i+1}.py b/src/features/feature_{i+1}.py"],
            "aggregated_added_code": CODE_SNIPPETS[code_idx],
            "aggregated_removed_code": "",
            "test_steps": "1. 启动系统\n2. 执行特定操作\n3. 观察错误现象",
            "expected_result": "系统应该正常运行并返回预期结果",
            "actual_result": f"系统出现{BUG_TITLES[title_idx]}，导致功能异常",
            "log_info": ERROR_MESSAGES[title_idx],
            "severity": random.choice(SEVERITY_LEVELS),
            "is_reappear": random.choice(["是", "否"]),
            "environment": ENVIRONMENT_INFO[env_idx]["runtime_env"],
            "root_cause": "初步分析为代码逻辑问题",
            "fix_solution": "修复代码中的逻辑错误",
            "related_issues": related_issues,
            "fix_person": random.choice(HANDLERS),
            "create_at": create_at.isoformat(),
            "fix_date": fix_date.isoformat(),
            "reopen_count": random.randint(0, 2),
            "handlers": handlers,
            "project_id": random.choice(PROJECT_IDS)
        }
        mock_data.append(bug_report)
    
    return mock_data

def save_mock_data(count: int = 10):
    """生成并保存测试数据"""
    mock_data = generate_mock_data(count)
    
    # 确保目录存在
    data_dir = Path("mock/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存数据
    with open(data_dir / "bug_reports.json", "w", encoding="utf-8") as f:
        json.dump(mock_data, f, ensure_ascii=False, indent=2)
    print(f"测试数据已生成并保存到 mock/data/bug_reports.json，共 {count} 条记录")

if __name__ == "__main__":
    save_mock_data() 
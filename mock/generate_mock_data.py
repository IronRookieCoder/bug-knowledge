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
    "权限验证问题",
    "前端页面加载缓慢",  # 新增
    "第三方服务调用失败",  # 新增
    "配置文件解析错误",  # 新增
    "资源竞争导致死锁",  # 新增
    "定时任务未按预期执行"  # 新增
]

CODE_SNIPPETS = [
    """const connectDb = async () => {
        try {
            const connection = await pool.connect({
                database: "testdb",
                user: "admin",
                password: "secret",
                host: "localhost",
                port: 5432
            });
            return connection;
        } catch (error) {
            console.error(`数据库连接失败: ${error.message}`);
            throw error;
        }
    };""",
    
    """const loginUser = async (username: string, password: string) => {
        const user = await db.users.findOne({ username });
        if (!user || !verifyPassword(password, user.password)) {
            throw new AuthenticationError("用户名或密码错误");
        }
        return generateToken(user);
    };""",
    
    """const uploadFile = (file: Express.Multer.File) => {
        if (file.size > MAX_FILE_SIZE) {
            throw new FileTooLargeError("文件大小超过限制");
        }
        return saveFile(file);
    };""",
    
    """class DataProcessor {
        private cache: Record<string, any> = {};
        
        processData(data: { id: string }) {
            this.cache[data.id] = data;
            return this.cache;
        }
    }""",
    
    """app.get("/api/data", async (req, res) => {
        await new Promise(resolve => setTimeout(resolve, 2000)); // 模拟延迟
        res.json({ status: "success" });
    });""",
    
    """const updateCache = (key: string, value: any) => {
        try {
            redisClient.set(key, value);
        } catch (error) {
            console.error(`缓存更新失败: ${error.message}`);
            throw error;
        }
    };""",
    
    """const handleRequest = async (request: Request) => {
        const release = await semaphore.acquire();
        try {
            return await processRequest(request);
        } finally {
            release();
        }
    };""",
    
    """const logError = (error: Error) => {
        try {
            const logEntry = `${new Date().toISOString()}: ${error.message}\n`;
            fs.appendFileSync("error.log", logEntry);
        } catch (e) {
            console.error(`日志记录失败: ${e.message}`);
        }
    };""",
    
    """const syncData = (source: string, target: string) => {
        const data = fetchData(source);
        try {
            saveData(target, data);
        } catch (error) {
            console.error(`数据同步失败: ${error.message}`);
            throw error;
        }
    };""",
    
    """const checkPermission = (user: User, resource: string) => {
        if (!user.hasPermission(resource)) {
            throw new PermissionError("没有访问权限");
        }
        return true;
    };""",
    
    """const loadConfig = (configPath: string) => {
        try {
            const config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
            return config;
        } catch (error) {
            console.error(`配置文件解析失败: ${error.message}`);
            throw error;
        }
    };""",
    
    """const callThirdPartyService = async (url: string, payload: Record<string, any>) => {
        try {
            const response = await axios.post(url, payload);
            return response.data;
        } catch (error) {
            console.error(`第三方服务调用失败: ${error.message}`);
            throw error;
        }
    };""",
    
    """const acquireLock = (lockKey: string) => {
        try {
            const lock = redisClient.lock(lockKey, { timeout: 10 });
            if (!lock.acquire()) {
                throw new ResourceLockError("资源锁获取失败");
            }
            return lock;
        } catch (error) {
            console.error(`资源竞争导致死锁: ${error.message}`);
            throw error;
        }
    };""",
    
    """const scheduleTask = (taskId: string, cronExpr: string) => {
        try {
            scheduler.addJob(taskId, { trigger: CronTrigger.fromCrontab(cronExpr) });
        } catch (error) {
            console.error(`定时任务未按预期执行: ${error.message}`);
            throw error;
        }
    };"""
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
    "Insufficient permissions for operation",
    "Page load time exceeds 5 seconds",  # 新增
    "Third-party service returned HTTP 500",  # 新增
    "Failed to parse configuration file",  # 新增
    "Resource deadlock detected",  # 新增
    "Scheduled task did not execute as expected"  # 新增
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
        
        # 随机生成文件路径
        file_name = f"src/features/feature_{uuid.uuid4().hex[:6]}.ts"
        
        # 随机生成代码变更内容
        original_code = "\n".join([f'console.log("Original line {j}");' for j in range(random.randint(1, 5))])
        modified_code = "\n".join([f'console.log("Modified line {j}");' for j in range(random.randint(1, 5))])
        added_code = "\n".join([f'console.log("Added line {j}");' for j in range(random.randint(1, 3))])
        removed_code = "\n".join([f'console.log("Removed line {j}");' for j in range(random.randint(1, 3))])

        # 构造多样化的 diff 内容
        diff_content = f"""diff --git a/{file_name} b/{file_name}
        --- a/{file_name}
        +++ b/{file_name}
        @@ -1,{len(original_code.splitlines())} +1,{len(modified_code.splitlines())} @@
        {original_code}
        +{added_code}
        -{removed_code}
        {modified_code}
        """

        bug_report = {
            "bug_id": f"BUG-{uuid.uuid4().hex[:8]}",
            "summary": BUG_TITLES[title_idx],
            "file_paths": [file_name],
            "code_diffs": [diff_content],  # 使用标准diff格式
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
import random
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path

class TestDataGenerator:
    """测试数据生成器"""
    
    def __init__(self):
        self.error_messages = [
            "Connection refused: connect",
            "OutOfMemoryError: Java heap space",
            "Thread pool rejection",
            "FileNotFoundException",
            "SocketTimeoutException",
            "DeadlockException",
            "NullPointerException",
            "IOException: Broken pipe",
            "ConfigurationException",
            "StackOverflowError"
        ]
        
        self.code_templates = [
            ("Python", "app.py", (10, 20), "try:\n    with open(file_path, 'r') as f:\n        data = f.read()\nexcept IOError as e:\n    logger.error(f'Failed to read file: {e}')"),
            ("Java", "Main.java", (100, 150), "public void connect() throws SQLException {\n    try (Connection conn = DriverManager.getConnection(url)) {\n        // ...\n    } catch (Exception e) {\n        log.error('Connection failed', e);\n    }\n}"),
            ("JavaScript", "server.js", (50, 60), "async function fetchData() {\n    try {\n        const response = await fetch(url);\n        return await response.json();\n    } catch (error) {\n        console.error('API request failed:', error);\n    }\n}"),
            ("Go", "main.go", (30, 40), "func processData(data []byte) error {\n    if len(data) == 0 {\n        return errors.New('empty data')\n    }\n    // ...\n    return nil\n}"),
            ("C++", "processor.cpp", (200, 250), "void processQueue() {\n    std::lock_guard<std::mutex> lock(mtx);\n    while (!queue.empty()) {\n        auto item = queue.front();\n        queue.pop();\n    }\n}")
        ]
        
        self.environments = [
            {
                "runtime_env": "Python 3.8.5",
                "os_info": "Windows 10 Pro 64-bit",
                "network_env": "LAN"
            },
            {
                "runtime_env": "Java 11.0.8",
                "os_info": "Ubuntu 20.04 LTS",
                "network_env": "Cloud"
            },
            {
                "runtime_env": "Node.js 14.15.0",
                "os_info": "macOS Big Sur",
                "network_env": "WAN"
            },
            {
                "runtime_env": "Go 1.15.2",
                "os_info": "CentOS 8",
                "network_env": "VPN"
            },
            {
                "runtime_env": "C++ GCC 9.3.0",
                "os_info": "Debian 10",
                "network_env": "Intranet"
            }
        ]
    
    def generate_bug_report(self, bug_id: str) -> Dict:
        """生成一个随机的bug报告"""
        # 随机选择模板
        error_msg = random.choice(self.error_messages)
        code_template = random.choice(self.code_templates)
        env = random.choice(self.environments)
        
        # 生成时间
        create_at = datetime.now() - timedelta(days=random.randint(1, 30))
        fix_date = create_at + timedelta(days=random.randint(1, 30))
        
        return {
            "bug_id": bug_id,
            "summary": f"在执行操作时遇到了问题。系统返回错误：{error_msg}",
            "file_paths": [code_template[1]],
            "code_diffs": [f"diff --git a/{code_template[1]} b/{code_template[1]}"],
            "aggregated_added_code": code_template[3],
            "aggregated_removed_code": "",
            "description": f"这是一个关于{error_msg}的详细描述。问题出现在系统运行过程中，影响了正常功能的使用。",
            "test_steps": "1. 启动应用\n2. 执行相关操作\n3. 观察错误发生",
            "expected_result": "操作应该正常完成，没有错误发生",
            "actual_result": f"操作失败，产生错误：{error_msg}",
            "log_info": f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {error_msg}\n" + \
                       f"[DEBUG] Stack trace:\n{error_msg}\nAt {code_template[1]}:{code_template[2][0]}",
            "severity": random.choice(["P0", "P1", "P2", "P3"]),
            "is_reappear": random.choice(["是", "否"]),
            "environment": env,
            "root_cause": "初步分析为代码逻辑问题",
            "fix_solution": "修复代码中的逻辑错误",
            "related_issues": [],
            "fix_person": random.choice(["张三", "李四", "王五"]),
            "create_at": create_at.isoformat(),
            "fix_date": fix_date.isoformat(),
            "reopen_count": random.randint(0, 2),
            "handlers": random.sample(["张三", "李四", "王五", "赵六", "钱七"], random.randint(1, 3)),
            "project_id": f"PROJ-{random.randint(1, 10):03d}"
        }
    
    def generate_bug_reports(self, count: int = 10) -> List[Dict]:
        """生成指定数量的bug报告"""
        bug_reports = []
        for i in range(count):
            bug_id = f"BUG-{uuid.uuid4().hex[:8]}"
            bug_reports.append(self.generate_bug_report(bug_id))
        return bug_reports
    
    def save_to_file(self, bug_reports: List[Dict], output_file: str):
        """将bug报告保存到文件"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(bug_reports, f, ensure_ascii=False, indent=2)
        
        print(f"测试数据已生成并保存到 {output_file}")

def generate_test_data(count: int = 10, output_file: str = "tests/data/bug_reports.json"):
    """生成测试数据的便捷函数"""
    generator = TestDataGenerator()
    bug_reports = generator.generate_bug_reports(count)
    generator.save_to_file(bug_reports, output_file)
    return bug_reports

if __name__ == "__main__":
    generate_test_data() 
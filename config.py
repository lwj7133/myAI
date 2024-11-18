import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 管理员账户设置
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# API默认设置
DEFAULT_API_KEY = os.getenv('DEFAULT_API_KEY')
DEFAULT_API_BASE = os.getenv('DEFAULT_API_BASE')
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'gpt-4o-all')

# 添加数据库配置
DB_CONFIG = {
    "db_name": "cookie_ai.db",
    "backup_path": "backup/",
    "max_sessions_per_user": 50,
}

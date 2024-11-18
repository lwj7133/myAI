import streamlit as st

# 从 Streamlit Secrets 获取配置
ADMIN_USERNAME = st.secrets["ADMIN_USERNAME"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
DEFAULT_API_KEY = st.secrets["DEFAULT_API_KEY"]
DEFAULT_API_BASE = st.secrets["DEFAULT_API_BASE"]
DEFAULT_MODEL = st.secrets["DEFAULT_MODEL"]

# 添加数据库配置
DB_CONFIG = {
    "db_name": "cookie_ai.db",
    "backup_path": "backup/",
    "max_sessions_per_user": 50,
}

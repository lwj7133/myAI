import re
import requests
import json
import html
import streamlit as st
from datetime import datetime, timedelta
from database import Database
import bcrypt

# 初始化数据库并创建管理员账户
try:
    db = Database()
    db.create_admin_if_not_exists()  # 确保管理员账户存在
except Exception as e:
    st.error(f"初始化数据库时出错: {str(e)}")
    st.stop()

# 登录部分
if "user_id" not in st.session_state:
    st.title("登录")
    
    login_username = st.text_input("用户名")
    login_password = st.text_input("密码", type="password")
    
    if st.button("登录"):
        try:
            success, user_id = db.verify_user(login_username, login_password)
            if success:
                st.session_state.user_id = user_id
                st.experimental_rerun()
            else:
                st.error("用户名或密码错误")
        except Exception as e:
            st.error(f"登录时出错: {str(e)}")

import re
import requests
import json
import html
import streamlit as st
from datetime import datetime, timedelta
from database import Database
import bcrypt
import pandas as pd
import io

# 初始化数据库
db = Database()

# 确保所需的表都已创建
try:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER,
            sessions TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # 提交事务并关闭连接
    conn.commit()
    conn.close()
except Exception as e:
    st.error(f"初始化数据库表时出错: {str(e)}")

# 设置页面配置，使用机器人emoji作为图标
st.set_page_config(
    page_title="Cookie-AI智能助手",
    page_icon="🤖",  # 使用机器人emoji作为图标
    layout="wide"
)

# 在st.set_page_config之后添加会话状态初始化
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

# 在主要内容之前添加登录/注册界面的部分进行修改
if not st.session_state.user_id:
    # 添加自定义CSS来实现居中布局
    st.markdown("""
        <style>
        /* 整体容器样式 */
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            background-color: white;
        }
        
        /* 标题样式 */
        .login-header {
            text-align: center;
            margin-bottom: 30px;
            color: #2E4053;
        }
        
        .login-header h2 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        
        /* 按钮样式 */
        .stButton > button {
            width: 100%;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        /* 标签页样式 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            background-color: #F8FAFC;
            border-radius: 10px;
            padding: 5px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            border-radius: 8px;
            gap: 2px;
            padding: 10px 20px;
            font-weight: 600;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: white;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        /* 提示信息样式 */
        .stAlert {
            padding: 10px;
            border-radius: 8px;
            margin-top: 10px;
        }
        
        /* 帮助文本样式 */
        .help-text {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }
        
        /* 动画效果 */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .login-container {
            animation: fadeIn 0.5s ease-out;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 创建三列布局，使用中间列
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        #st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown("""
            <div class="login-header">
                <h1 style="font-size: 2.5em">🤖 Cookie-AI</h1>
                <p style="font-size: 1.2em">
                    <span style="font-size:1.4em">✅</span> 连续对话 | 
                    <span style="font-size:1.4em">📄</span> 文件解析 | 
                    <span style="font-size:1.4em">🌐</span> 实时联网 | 
                    <span style="font-size:1.4em">📝</span> 文档生成 | 
                    <span style="font-size:1.4em">🎨</span> 图像处理
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["👤 登录", "✨ 注册"])
        
        # 检查是否刚刚完成注册
        if hasattr(st.session_state, 'registration_successful'):
            # 删除标记以避免重复显示
            delattr(st.session_state, 'registration_successful')
            # 获取注册的用户名
            registered_username = st.session_state.registered_username
            delattr(st.session_state, 'registered_username')
            # 显示成功消息
            st.success(f"✅ 注册成功！请使用账号 {registered_username} 登录")
        
        with tab1:
            with st.form("login_form", clear_on_submit=True):
                st.markdown("##### 账号登录")
                login_username = st.text_input("用户名", 
                                            key="login_username",
                                            placeholder="请输入用户名")
                login_password = st.text_input("密码", 
                                            type="password", 
                                            key="login_password",
                                            placeholder="请输入密码")
                login_submit = st.form_submit_button("登 录", 
                                                       use_container_width=True,
                                                       )
                
                if login_submit:
                    if login_username and login_password:
                        success, user_id = db.verify_user(login_username, login_password)
                        if success:
                            # 设置基本会话状态
                            st.session_state.user_id = user_id
                            st.session_state.username = login_username
                            
                            # 加载用户的会话数据
                            saved_sessions = db.load_user_sessions(user_id)
                            if saved_sessions:
                                st.session_state.sessions = saved_sessions
                                # 检查最新会话是否为空会话
                                latest_session = max(saved_sessions.items(), key=lambda x: x[1]['timestamp'])
                                if not latest_session[1]['chat_history']:
                                    # 如果最新会话是空会话，直接使用它
                                    st.session_state.current_session_id = latest_session[0]
                                else:
                                    # 如果最新会话不是空会话，创建一个新的空会话
                                    new_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                    st.session_state.sessions[new_session_id] = {
                                        'chat_history': [],
                                        'chat_context': [],
                                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        'title': '新会话',
                                        'is_favorite': False
                                    }
                                    st.session_state.current_session_id = new_session_id
                            else:
                                # 初始化默认会话
                                st.session_state.sessions = {
                                    'default': {
                                        'chat_history': [],
                                        'chat_context': [],
                                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        'title': '新会话',
                                        'is_favorite': False
                                    }
                                }
                                st.session_state.current_session_id = 'default'
                            
                            # 加载用户设置
                            settings = db.load_user_settings(user_id)
                            if settings:
                                st.session_state.api_key = settings.get('api_key', "sk-1xOLoJ1NRluWwc5oC5Cc8f32E8D940C791AdEb8b656bD4C6")
                                st.session_state.api_base = settings.get('api_base', "https://api.tu-zi.com")
                                st.session_state.model = settings.get('model', "gpt-4o-all")
                            else:
                                # 设置默认值
                                st.session_state.api_key = "sk-1xOLoJ1NRluWwc5oC5Cc8f32E8D940C791AdEb8b656bD4C6"
                                st.session_state.api_base = "https://api.tu-zi.com"
                                st.session_state.model = "gpt-4o-all"
                            
                            # 检查是否是管理员
                            is_admin = db.verify_admin(user_id)
                            st.session_state.is_admin = is_admin
                            
                            # 初始化显示默认值的标记
                            st.session_state.show_default = {
                                'api_key': True,
                                'api_base': True,
                                'model': True
                            }
                            
                            st.rerun()
                        else:
                            st.error("❌ 用户名或密码错误")
                    else:
                        st.warning("⚠️ 请输入用户名和密码")
        
        with tab2:
            with st.form("register_form", clear_on_submit=True):
                st.markdown("##### 注册账号")
                reg_username = st.text_input("用户名", 
                                           key="reg_username",
                                           placeholder="仅支持英文字母、数字和下划线",
                                           help="用户名长度4-20个字符")
                
                reg_password = st.text_input("密码", 
                                           type="password", 
                                           key="reg_password",
                                           placeholder="请设置登录密码",
                                           help="密码长度至少6个字符")
                
                reg_password_confirm = st.text_input("确认密码", 
                                                   type="password", 
                                                   key="reg_password_confirm",
                                                   placeholder="请再次输入密码")
                
                register_submit = st.form_submit_button("注 册", 
                                                      use_container_width=True,
                                                      )
                
                if register_submit:
                    if reg_username and reg_password and reg_password_confirm:
                        # 验证用户名长度
                        if len(reg_username) < 4 or len(reg_username) > 20:
                            st.error("❌ 用户名长度必须在4-20个字符之间")
                        # 验证用户名是否包含中文
                        elif re.search(r'[\u4e00-\u9fff]', reg_username):
                            st.error("❌ 用户名不能包含中文字符")
                        # 验证用户名格式
                        elif not re.match(r'^[a-zA-Z0-9_]+$', reg_username):
                            st.error("❌ 用户名只能包含英文字母、数字和划线")
                        # 验证密码长度
                        elif len(reg_password) < 6:
                            st.error("❌ 密码长度至少需要6个字符")
                        # 验证密码是否包含中文
                        elif re.search(r'[\u4e00-\u9fff]', reg_password):
                            st.error("❌ 密码不能包含中文字符")
                        # 验证两次输入的密码是否一致
                        elif reg_password != reg_password_confirm:
                            st.error("❌ 两次输入的密码不一致")
                        else:
                            success, message = db.register_user(reg_username, reg_password)
                            if success:
                                st.success("✅ " + message)
                                st.session_state.registration_successful = True
                                st.session_state.registered_username = reg_username
                                st.rerun()
                            else:
                                st.error("❌ " + message)
                    else:
                        st.warning("⚠️ 请填写所有字段")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 如果用户未登录，停止显示后续内容
    st.stop()

# 在用户认证相关代码之后，API设置部分之前添加这些变量的初始化
if 'api_key' not in st.session_state:
    st.session_state.api_key = "sk-1xOLoJ1NRluWwc5oC5Cc8f32E8D940C791AdEb8b656bD4C6"  # default_api_key
if 'api_base' not in st.session_state:
    st.session_state.api_base = "https://api.tu-zi.com"  # default_api_base
if 'model' not in st.session_state:
    st.session_state.model = "gpt-4o-all"  # 修改默认模型为 gpt-4o-all
if 'show_default' not in st.session_state:
    st.session_state.show_default = {'api_key': True, 'api_base': True, 'model': True}

# API设置部分保留在侧边栏
with st.sidebar:
    # 用户信息和登出按钮
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"### 👤 当前用户: {st.session_state.username}")
    with col2:
        if st.button("退出登录", use_container_width=True):
            # 保存用户数据
            db.save_user_sessions(st.session_state.user_id, st.session_state.sessions)
            db.save_user_settings(
                st.session_state.user_id,
                st.session_state.api_key,
                st.session_state.api_base,
                st.session_state.model
            )
            # 清除会话状态
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # API设置表单
    with st.form(key="api_settings_form"):
        st.subheader("API 设置")
        
        api_key = st.text_input("API密钥", 
                               value="默认" if st.session_state.show_default['api_key'] else st.session_state.api_key, 
                               type="password", 
                               key="api_key_input")
        api_base = st.text_input("API基础URL", 
                                value="默认" if st.session_state.show_default['api_base'] else st.session_state.api_base, 
                                key="api_base_input")
        
        # 使用下拉选择框替代文本输入框
        available_models = [
            ("gpt-4o-all", "———全能版 | 联网、代码、文件、图像"),
            ("gpt-4o", "———基础版 | 日常任务"),
            ("gpt-4o-mini", "———轻量版 | 快速响应"),
            ("claude-3-5-sonnet-20240620", "———代码突出 | 强大理解"),
            ("claude-3-5-sonnet-20240620-fast", "———代码突出 | 快速版"),
            ("claude-3-5-sonnet-20241022", "———代码突出 | 最新版"),
            ("claude-3-5-sonnet-20241022-fast", "———代码突出 | 快速版"),
            ("claude-3-5-haiku-20241022-fast", "———Haiku | 轻量快速"),
            ("openai-gpt-4o", "———GPT-4 | 原生接口"),
            ("OpenAI-gpt-4o", "———GPT-4 | 备用接口"),
            ("Claude-claude-3-5-sonnet-20240620", "———Sonnet 06 | 原生"),
            ("Claude-claude-3-5-sonnet-20241022", "———Sonnet 10 | 原生"),
            ("gemini-2.0-flash-exp", "———gemini-2.0-flash-exp"),
            ("o1-mini-all", "———深度推理 | o1轻量"),
            ("o1-all", "———深度推理 | o1预览版"),
            ("o1", "———深度推理 | o1"),
            ("o1-mini", "———深度推理 | o1快速版"),
            ("o1-pro", "———深度推理 | o1"),
            ("o1-pro-all", "———深度推理 | o1"),
            ("dall-e-3", "———DALL-E 3 | 图像生成"),
            ("ideogram", "———Ideogram | 图像生成"),
            ("midjourney", "———Midjourney | 图像生成"),
            ("suno-v3.5", "———Suno | 音乐生成"),
            ("gpt-4-gizmo-g-bo0FiWLY7", "———Consensus科研文献"),
            ("gpt-4-gizmo-g-pmuQfob8d-image-generator", "———图像生成"),
            ("gpt-4-gizmo-g-NgAcklHd8-scispace", "———SciSpace科研助手"),
            ("gpt-4-gizmo-g-B3hgivKK9-write-for-me", "———WriteForMe写作助手"),
            ("gpt-4-gizmo-g-gFt1ghYJl-logo-creator", "———Logo设计"),
            ("gpt-4-gizmo-g-Lq7UjNxjV-lun-wen-xie-shou", "———论文写手"),
            ("gpt-4-gizmo-g-RfusSJbgM-chao-ji-pptsheng-cheng-super-ppt", "———SuperPPT生成")
        ]
        model = st.selectbox(
            "模型名称",
            options=[m[0] for m in available_models],
            format_func=lambda x: f"{x} ({dict(available_models)[x]})",
            index=[m[0] for m in available_models].index(st.session_state.model) if st.session_state.model in [m[0] for m in available_models] else 0,
            key="model_input"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit_button = st.form_submit_button("保存新设置", use_container_width=True)
        with col2:
            reset_button = st.form_submit_button("恢复默认设置", use_container_width=True)
        
        if submit_button:
            st.session_state.api_key = "sk-1xOLoJ1NRluWwc5oC5Cc8f32E8D940C791AdEb8b656bD4C6" if api_key == "默认" else api_key
            st.session_state.api_base = "https://api.tu-zi.com" if api_base == "默认" else api_base
            st.session_state.model = model
            st.session_state.show_default = {
                'api_key': api_key == "默认",
                'api_base': api_base == "默认",
                'model': model == "gpt-4o-all"
            }
            # 保存用户设置
            db.save_user_settings(
                st.session_state.user_id,
                st.session_state.api_key,
                st.session_state.api_base,
                st.session_state.model
            )
            st.success("API设置已更新")
        
        if reset_button:
            st.session_state.api_key = "sk-1xOLoJ1NRluWwc5oC5Cc8f32E8D940C791AdEb8b656bD4C6"
            st.session_state.api_base = "https://api.tu-zi.com"
            st.session_state.model = "gpt-4o-all"
            st.session_state.show_default = {'api_key': True, 'api_base': True, 'model': True}
            # 保存默认设置
            db.save_user_settings(
                st.session_state.user_id,
                st.session_state.api_key,
                st.session_state.api_base,
                st.session_state.model
            )
            st.success("API设置已恢复为默认值")
            st.rerun()

    # 在用户信息显示后添加
    if hasattr(st.session_state, 'is_admin') and st.session_state.is_admin:
        st.markdown("---")
        st.markdown("## 👑 管理员功能")
        if st.button("管理用户", use_container_width=True):
            st.session_state.show_admin_panel = True
            st.rerun()

# 主要内容移到主区域
st.markdown("""
    <div style="text-align: center;">
        <h1>🤖 Cookie-AI多模态智能助手</h1>
        <h4>✅连续对话 | 📄文件解析 | 🌐实时联网 | 📝文档生成 | 🎨图像处理</h4>
    </div>
""", unsafe_allow_html=True)

# 在初始化聊天历史和上下文的部分之前添加
if 'sessions' not in st.session_state:
    st.session_state.sessions = {}
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = 'default'
    st.session_state.sessions['default'] = {
        'chat_history': [],
        'chat_context': [],
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'title': '新会话',
        'is_favorite': False  # 添加收藏标记
    }

# 初始化聊天历史和上下文时修改为
if st.session_state.current_session_id not in st.session_state.sessions:
    st.session_state.sessions[st.session_state.current_session_id] = {
        'chat_history': [],
        'chat_context': [],
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'title': '新会话'
    }

# 替换所有 st.session_state.chat_history 为
# st.session_state.sessions[st.session_state.current_session_id]['chat_history']
# 替换所有 st.session_state.chat_context 为
# st.session_state.sessions[st.session_state.current_session_id]['chat_context']

system_message = """你叫Cookie，是一个专业、友好的AI助手。你能够回答各种领域的问题，解释复杂概念，并协助用户完成各种任务。
请用清晰、易懂的语言回答问题，适时使用例子来说明，必要时可以使用图表或公式来辅助解释。
回答时保持友好和专业，适当使用emoji让对话更生动，对用户保持积极鼓励的态度。"""

# 使用保存的设置
api_key_to_use = st.session_state.api_key
api_base_to_use = st.session_state.api_base
model_to_use = st.session_state.model

def post_process_latex(text):
    """
    后处理 AI 输出，确保数学公式被正确包裹在 $$ 符号内
    """
    # 移除多余的 $ 符号
    text = re.sub(r'\${2,}', '$$', text)
    
    # 查找可能的公式开始和结束
    pattern = r'(\\begin\{.*?\}|\\end\{.*?\}|\\\[|\\\]|\\(|\\))'
    
    def replace_func(match):
        formula = match.group(1)
        if formula in ['\\(', '\\)']:
            return '$$'
        if formula in ['\\[', '\\]']:
            return '$$'
        return formula
    
    # 使用正则表达式查找可能的公式边界并替换
    processed_text = re.sub(pattern, replace_func, text)
    
    return processed_text

def render_message(message):
    """渲染消息，处理LaTeX公式"""
    # 分割文本和公式
    parts = re.split(r'(\$\$.*?\$\$|\$.*?\$)', message)
    for part in parts:
        if part.startswith('$') and part.endswith('$'):
            # 这是一个公式，使用 st.latex 渲染
            st.latex(part.strip('$'))
        else:
            # 这是普通文本，使用 st.markdown 渲染
            st.markdown(part)

# 创建一个空的容器用于显示AI响应
ai_response_container = st.empty()

# 添加自定义CSS样式
st.markdown("""
<style>
.chat-message {
    padding: 0.5rem; 
    border-radius: 0.5rem; 
    margin-bottom: 1rem; 
    display: flex;
    align-items: flex-start;
}
.chat-message.user {
    background-color: #E6FFE6;  /* 淡绿色 */
    justify-content: flex-end;
}
.chat-message.bot {
    background-color: #FFE6E6;  /* 淡粉色 */
}
.chat-message .message {
    width: 100%;
    padding: 0.5rem 1rem;
    color: #333;  /* 深灰色文字，确保在浅色背景上可读 */
}
.chat-message.user .message {
    text-align: right;
}
</style>
""", unsafe_allow_html=True)

# 显示聊天历史
for message in st.session_state.sessions[st.session_state.current_session_id]['chat_history']:
    if isinstance(message, dict):
        if message['type'] == 'image':
            # 显示图片
            st.image(f"data:image/jpeg;base64,{message['data']}")
            if 'user_input' in message and message['user_input']:
                st.markdown(f'''
                <div class="chat-message user">
                    <div class="message"><strong>:You</strong> 🙋<br>[图片: {message['filename']}] {message['user_input']}</div>
                </div>
                ''', unsafe_allow_html=True)
        elif message['type'] == 'document':
            # 显示文档上传信息
            st.markdown(f'''
            <div class="chat-message user">
                <div class="message"><strong>:You</strong> 🙋<br>[文档: {message['filename']}] {message['user_input']}</div>
            </div>
            ''', unsafe_allow_html=True)
    elif isinstance(message, str):
        if message.startswith("你:"):
            st.markdown(f'''
            <div class="chat-message user">
                <div class="message"><strong>:You</strong> 🙋<br>{html.escape(message[3:])}</div>
            </div>
            ''', unsafe_allow_html=True)
        elif message.startswith("AI:"):
            st.markdown(f'''
            <div class="chat-message bot">
                <div class="message">🤖 <strong>Cookie:</strong><br>{post_process_latex(message[3:])}</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.text(message)

def simplify_context(context, max_messages=7):
    """简化上下文，保留最近的消息"""
    if len(context) <= max_messages:
        return context
    
    # 保留系统消息（如果存在）
    simplified = [msg for msg in context if msg["role"] == "system"]
    
    # 添加最近的消息，确保用户和助手的消息交替出现
    recent_messages = context[-max_messages:]
    for i, msg in enumerate(recent_messages):
        if i == 0 and msg["role"] == "assistant":
            simplified.append({"role": "user", "content": "继续我们的对话。"})
        simplified.append(msg)
    
    return simplified

# 在文件开头添加特殊模型的提示词映射
SPECIAL_MODELS_PROMPTS = {
    "gpt-4-gizmo-g-bo0FiWLY7": "",  # 使用空字符串表示不需要系统提示词
    "gpt-4-gizmo-g-pmuQfob8d-image-generator": "",
    "gpt-4-gizmo-g-NgAcklHd8-scispace": "",
    "gpt-4-gizmo-g-B3hgivKK9-write-for-me": "",
    "gpt-4-gizmo-g-gFt1ghYJl-logo-creator": "",
    "gpt-4-gizmo-g-Lq7UjNxjV-lun-wen-xie-shou": "",
    "gpt-4-gizmo-g-RfusSJbgM-chao-ji-pptsheng-cheng-super-ppt": "",
    "o1-all": "",
    "o1-pro-all": "",
    "o1": "",
    "o1-pro": ""
}

def stream_api_call(context):
    """调用API并流式返回响应"""
    headers = {
        "Authorization": f"Bearer {api_key_to_use}",
        "Content-Type": "application/json"
    }
    
    simplified_context = simplify_context(context)
    
    # 检查是否是特殊模型，如果不是才添加系统提示词
    # if model_to_use not in SPECIAL_MODELS_PROMPTS and simplified_context[0]["role"] != "system":
    #     simplified_context.insert(0, {"role": "system", "content": system_message})
    
    data = {
        "model": model_to_use,
        "messages": simplified_context,
        "max_tokens": 1000,
        "stream": True
    }
    
    try:
        url = f"{api_base_to_use}/v1/chat/completions"
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
        full_response = ""
        response_container = st.empty()
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8').split('data: ')[1])
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        if 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                            content = chunk['choices'][0]['delta']['content']
                            full_response += content
                            processed_response = post_process_latex(full_response)
                            response_container.markdown(processed_response)
                except json.JSONDecodeError:
                    continue
                except IndexError:
                    continue
        
        return post_process_latex(full_response)
    except Exception as e:
        return f"API请求错误: {str(e)}"

# 在process_document函数之前添加新的辅助函数
def compress_image(image_data, max_size_mb=2):
    """压缩图片到指定大小以下"""
    import io
    from PIL import Image
    
    # 将bytes转换为PIL Image对象
    image = Image.open(io.BytesIO(image_data))
    
    # 初始压缩质量
    quality = 95
    output = io.BytesIO()
    
    # 如果是PNG，转换为JPEG以获得更好的压缩
    if image.format == 'PNG':
        # 如果有透明通道，先将背景转为白色
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        else:
            image = image.convert('RGB')
    
    # 保存图片并检查大小
    image.save(output, format='JPEG', quality=quality)
    
    # 如果大小超过限制，逐步降低质量直到满足要求
    while output.tell() > max_size_mb * 1024 * 1024 and quality > 10:
        output = io.BytesIO()
        quality -= 5
        image.save(output, format='JPEG', quality=quality)
    
    return output.getvalue()

# 修改process_document函数
def process_document(file):
    """处理上传的文档，提取文本内容"""
    import io
    import docx
    import PyPDF2
    from PIL import Image
    import base64
    import pandas as pd
    
    # 检查文件大小（50MB限制）
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
    if len(file.getvalue()) > MAX_FILE_SIZE:
        st.error(f"文件大小超过限制（50MB），请上传更小的文件。")
        return None
    
    file_extension = file.name.lower().split('.')[-1]
    
    try:
        # 处理Excel文件
        if file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(file)
            # 获取基本信息
            info = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'column_names': list(df.columns),
                'data_types': df.dtypes.to_dict(),
                'preview': df.head().to_string(),
                'description': df.describe().to_string(),
                'missing_values': df.isnull().sum().to_dict()
            }
            return {
                'type': 'excel',
                'data': info,
                'raw_df': df
            }
            
        # 处理CSV文件
        elif file_extension == 'csv':
            # 尝试不同的编码方式读取CSV
            encodings = ['utf-8', 'gbk', 'gb2312', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(io.StringIO(file.getvalue().decode(encoding)))
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    continue
            
            if df is not None:
                info = {
                    'total_rows': len(df),
                    'total_columns': len(df.columns),
                    'column_names': list(df.columns),
                    'data_types': df.dtypes.to_dict(),
                    'preview': df.head().to_string(),
                    'description': df.describe().to_string(),
                    'missing_values': df.isnull().sum().to_dict()
                }
                return {
                    'type': 'csv',
                    'data': info,
                    'raw_df': df
                }
            else:
                st.error("无法读取CSV文件，请检查文件编码格式。")
                return None
                
        # 处理代码文件 - 添加html相关文件类型
        elif file_extension in ['py', 'c', 'cpp', 'h', 'hpp', 'm', 'swift', 'java', 'js', 'ts','html', 'htm', 'css', 'scss', 'less', 'jsx', 'tsx', 'vue', 'php']:  # 添加web文件类型
            code_content = file.getvalue().decode('utf-8')
            return code_content
            
        elif file_extension == 'pdf':
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.getvalue()))
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            return text_content
            
        elif file_extension in ['doc', 'docx']:
            doc = docx.Document(io.BytesIO(file.getvalue()))
            text_content = ""
            for para in doc.paragraphs:
                text_content += para.text + "\n"
            return text_content
            
        elif file_extension in ['png', 'jpg', 'jpeg']:
            # 压缩图片
            compressed_image = compress_image(file.getvalue())
            return base64.b64encode(compressed_image).decode('utf-8')
            
        else:
            return None
    except Exception as e:
        st.error(f"处理文件时出错: {str(e)}")
        return None

# 创建聊天表单
with st.form(key="chat_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([9, 0.6, 0.6])
    
    with col1:
        user_input = st.text_input(
            "输入问题:", 
            key="user_input", 
            label_visibility="collapsed", 
            placeholder="有什么我可以帮你的吗？"
        )
    
    with col2:
        chat_submit_button = st.form_submit_button(
            "**✈️**",
            help="发送消息"
        )
    
    with col3:
        clear_button = st.form_submit_button(
            "🔄",
            help="开始新会话"
        )
    
    uploaded_file = st.file_uploader(
        "上传文件（小于50MB）", 
        type=["png", "jpg", "jpeg", "pdf", "doc", "docx", "py", "c", "cpp", "h", "hpp", "m", "swift", "java", "js", "ts",
              "html", "htm", "css", "scss", "less", "jsx", "tsx", "vue", "php", "xlsx", "xls", "csv"],  # 添加Excel和CSV支持
        key="file_uploader",
        help="支持的文件类型：图片(PNG/JPG)、文档(PDF/DOC/DOCX)、代码文件(PY/C/CPP/H/M等)、网页文件(HTML/CSS/JS等)、表格文件（xlsx/xls/csv）"
    )
    st.markdown('<style>div[data-testid="stFileUploader"] {margin-bottom: -15px;}</style>', unsafe_allow_html=True)

# 处理聊天表单提交
if chat_submit_button:
    if api_key_to_use and (user_input or uploaded_file):
        current_session = st.session_state.sessions[st.session_state.current_session_id]
        if len(current_session['chat_history']) == 0 and user_input:
            title = user_input[:20] + ('...' if len(user_input) > 20 else '')
            current_session['title'] = title

        if user_input:
            st.session_state.sessions[st.session_state.current_session_id]['chat_history'].append(f"你: {user_input}")
            st.session_state.sessions[st.session_state.current_session_id]['chat_context'].append({"role": "user", "content": user_input})
        
        if uploaded_file:
            file_extension = uploaded_file.name.lower().split('.')[-1]
            
            # 处理Excel和CSV文件
            if file_extension in ['xlsx', 'xls', 'csv']:
                data_content = process_document(uploaded_file)
                if data_content and isinstance(data_content, dict):
                    info = data_content['data']
                    
                    # 构建提示信息
                    prompt = f"""请分析以下{file_extension.upper()}文件数据：

基本信息：
- 总行数：{info['total_rows']}
- 总列数：{info['total_columns']}
- 列名：{', '.join(info['column_names'])}

数据预览：
{info['preview']}

数据描述：
{info['description']}

缺失值统计：
{json.dumps(info['missing_values'], indent=2)}
"""
                    if user_input:
                        prompt += f"\n用户的具体问题是：{user_input}"
                    else:
                        prompt += """
请对数据进行以下分析：
1. 数据概览和基本统计信息
2. 数据质量评估（包括缺失值、异常值等）
3. 主要特征之间的关系
4. 数据的潜在问题和改进建议
"""
                    
                    # 保存到会话历史
                    st.session_state.sessions[st.session_state.current_session_id]['chat_history'].append({
                        'type': 'data_analysis',
                        'filename': uploaded_file.name,
                        'file_type': file_extension,
                        'data_info': {
                            'total_rows': info['total_rows'],
                            'total_columns': info['total_columns'],
                            'column_names': info['column_names'],
                            'preview': info['preview'][:1000],  # 限制预览数据大小
                            'description': info['description']
                        },
                        'user_input': user_input if user_input else ''
                    })
                    
                    st.session_state.sessions[st.session_state.current_session_id]['chat_context'].append({
                        "role": "user", 
                        "content": prompt
                    })
                    
                    # 立即保存会话到数据库
                    db.save_user_sessions(st.session_state.user_id, st.session_state.sessions)
                    
            elif file_extension in ['png', 'jpg', 'jpeg']:
                image_base64 = process_document(uploaded_file)
                image_url = f"data:image/jpeg;base64,{image_base64}"
                # 修改存储方式，保存文件名和base64数据
                st.session_state.sessions[st.session_state.current_session_id]['chat_history'].append({
                    'type': 'image',
                    'filename': uploaded_file.name,
                    'data': image_base64
                })
                st.session_state.sessions[st.session_state.current_session_id]['chat_context'].append({
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_input if user_input else "请分析这张图片"},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                })
            else:
                document_content = process_document(uploaded_file)
                if document_content:
                    prompt = f"""请分析以下文档内容：\n\n{document_content}\n\n"""
                    if user_input:
                        prompt += f"用户的具体问题是：{user_input}"
                    else:
                        prompt += "请总结文档的主要内容，并提供关键信息分析。"
                    
                    # 修改存储方式，保存文件名和内容
                    st.session_state.sessions[st.session_state.current_session_id]['chat_history'].append({
                        'type': 'document',
                        'filename': uploaded_file.name,
                        'content': document_content,
                        'user_input': user_input if user_input else ''
                    })
                    st.session_state.sessions[st.session_state.current_session_id]['chat_context'].append({
                        "role": "user", 
                        "content": prompt
                    })
        
        # 调用API
        with st.spinner('🤖 Cookie正在思考中...'):
            ai_response = stream_api_call(st.session_state.sessions[st.session_state.current_session_id]['chat_context'])
        
        # 更新聊天历史和上下文
        processed_response = post_process_latex(ai_response)
        st.session_state.sessions[st.session_state.current_session_id]['chat_history'].append(f"AI: {processed_response}")
        st.session_state.sessions[st.session_state.current_session_id]['chat_context'].append({"role": "assistant", "content": ai_response})
        
        # 保存会话数据
        db.save_user_sessions(st.session_state.user_id, st.session_state.sessions)
        
        # 重新加载页面以显示新消息
        st.rerun()
    else:
        st.warning("请输入问题或上传文件。")

# 处理清空聊天按钮
if clear_button:
    new_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 打印当前会话数量
    st.write(f"当前会话数量: {len(st.session_state.sessions)}")
    
    # 添加新会话
    st.session_state.sessions[new_session_id] = {
        'chat_history': [],
        'chat_context': [],
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'title': '新会话',
        'is_favorite': False
    }
    
    # 打印更新后的会话数量
    st.write(f"添加新会话后数量: {len(st.session_state.sessions)}")
    
    st.session_state.current_session_id = new_session_id
    db.save_user_sessions(st.session_state.user_id, st.session_state.sessions)
    st.rerun()

# 添加声明
st.markdown(
    """
    <div style="background-color: #E6F3FF; padding: 10px; border-radius: 5px; color: #003366;">
    ⚠️ <strong>温馨提示：</strong> 由于系统维护和休眠机制，应用超过7天未使用，数据可能会被擦除，请及时保存重要数据。
    </div>
    """,
    unsafe_allow_html=True
)
# 在API设置部分之后，主要内容之前的会话管理部分改为
with st.sidebar:
    st.markdown("## 会话管理")
    
    # 添加分类标签
    tab1, tab2 = st.tabs(["📑 全部会话", "⭐ 收藏夹"])
    
    with tab1:
        # 获取所有会话
        if not st.session_state.sessions:
            st.info("暂无会话记录")
        else:
            # 按日期对会话进行分组
            sessions_by_date = {}
            for session_id, session_data in st.session_state.sessions.items():
                date = datetime.strptime(session_data['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                if date not in sessions_by_date:
                    sessions_by_date[date] = []
                sessions_by_date[date].append((session_id, session_data))
            
            # 按日期倒序显示会话
            for date in sorted(sessions_by_date.keys(), reverse=True):
                # 将日期转换为更友好的格式
                today = datetime.now().strftime("%Y-%m-%d")
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                
                if date == today:
                    display_date = "今天"
                elif date == yesterday:
                    display_date = "昨天"
                else:
                    display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%m月%d日")
                
                st.markdown(f"#### {display_date}")
                
                # 获取该日期的会话并按时间倒序排序
                daily_sessions = sorted(
                    sessions_by_date[date],
                    key=lambda x: x[1]['timestamp'],
                    reverse=True
                )
                
                # 显示该日期的所有会话
                for session_id, session_data in daily_sessions:
                    col1, col2, col3 = st.columns([3, 0.5, 0.5])
                    
                    with col1:
                        # 创建一个按钮，显示会话标题
                        is_current = session_id == st.session_state.current_session_id
                        if st.button(
                            f"{'🟢 ' if is_current else ''}{session_data.get('title', '新会话')}",
                            key=f"session_btn_{session_id}",
                            use_container_width=True,
                            type="secondary" if is_current else "secondary"
                        ):
                            st.session_state.current_session_id = session_id
                            st.rerun()
                    
                    with col2:
                        # 添加收藏/取消收藏按钮
                        is_favorite = session_data.get('is_favorite', False)
                        if st.button(
                            "⭐" if is_favorite else "☆",
                            key=f"favorite_btn_{session_id}",
                            help="取消收藏" if is_favorite else "收藏会话"
                        ):
                            st.session_state.sessions[session_id]['is_favorite'] = not is_favorite
                            # 保存会话数据
                            db.save_user_sessions(st.session_state.user_id, st.session_state.sessions)
                            st.rerun()
                    
                    with col3:
                        # 删除按钮
                        if len(st.session_state.sessions) > 1:
                            if st.button(
                                "🗑️",
                                key=f"delete_btn_{session_id}",
                                help="删除此会话"
                            ):
                                del st.session_state.sessions[session_id]
                                if session_id == st.session_state.current_session_id:
                                    remaining_sessions = sorted(
                                        st.session_state.sessions.items(),
                                        key=lambda x: x[1]['timestamp'],
                                        reverse=True
                                    )
                                    st.session_state.current_session_id = remaining_sessions[0][0]
                                db.save_user_sessions(st.session_state.user_id, st.session_state.sessions)
                                st.rerun()               
    
    with tab2:
        # 获取收藏的会话
        favorite_sessions = {
            session_id: session_data 
            for session_id, session_data in st.session_state.sessions.items() 
            if session_data.get('is_favorite', False)
        }
        
        if not favorite_sessions:
            st.info("暂无收藏会话")
        else:
            # 按时间倒序显示收藏的会话
            sorted_favorites = sorted(
                favorite_sessions.items(),
                key=lambda x: x[1]['timestamp'],
                reverse=True
            )
            
            for session_id, session_data in sorted_favorites:
                col1, col2, col3 = st.columns([3, 0.5, 0.5])
                
                with col1:
                    is_current = session_id == st.session_state.current_session_id
                    if st.button(
                        f"{'🟢 ' if is_current else ''}{session_data.get('title', '新会话')}",
                        key=f"fav_session_btn_{session_id}",
                        use_container_width=True,
                        type="secondary" if is_current else "secondary"
                    ):
                        st.session_state.current_session_id = session_id
                        st.rerun()
                
                with col2:
                    # 取消收藏按钮
                    if st.button(
                        "⭐",
                        key=f"unfavorite_btn_{session_id}",
                        help="取消收藏"
                    ):
                        st.session_state.sessions[session_id]['is_favorite'] = False
                        db.save_user_sessions(st.session_state.user_id, st.session_state.sessions)
                        st.rerun()
                
                with col3:
                    # 删除按钮
                    if len(st.session_state.sessions) > 1:
                        if st.button(
                            "🗑️",
                            key=f"fav_delete_btn_{session_id}",
                            help="删除此会话"
                        ):
                            del st.session_state.sessions[session_id]
                            if session_id == st.session_state.current_session_id:
                                remaining_sessions = sorted(
                                    st.session_state.sessions.items(),
                                    key=lambda x: x[1]['timestamp'],
                                    reverse=True
                                )
                                st.session_state.current_session_id = remaining_sessions[0][0]
                            db.save_user_sessions(st.session_state.user_id, st.session_state.sessions)
                            st.rerun()

# 在主要内容区域添加管理员面板
if hasattr(st.session_state, 'show_admin_panel') and st.session_state.show_admin_panel and st.session_state.is_admin:
    st.markdown("# 👥 用户管理")
    
    # 添加搜索框
    search_query = st.text_input("🔍 搜索用户", placeholder="输入用户名进行搜索...")
    
    # 获取所有用户
    users = db.get_all_users()
    
    # 如果有搜索查询，过滤用户列表
    if search_query:
        users = [user for user in users if search_query.lower() in user[1].lower()]
    
    # 显示搜索结果数量
    if search_query:
        st.markdown(f"找到 **{len(users)}** 个匹配的用户")
    
    # 创建用户表格样式
    st.markdown("""
    <style>
    .user-table {
        width: 100%;
        margin-top: 20px;
    }
    .user-table th, .user-table td {
        padding: 10px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    .user-table tr:hover {
        background-color: #f5f5f5;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 如果没有搜索结果，显示提示信息
    if search_query and not users:
        st.info(f"未找到包含 '{search_query}' 的用户")
    
    # 显示用户列表
    st.markdown("### 用户列表")
    
    # 创建表格列
    cols = st.columns([2, 2, 1.5, 2, 1.5, 1.5])
    cols[0].markdown("**用户ID**")
    cols[1].markdown("**用户名**")
    cols[2].markdown("**管理员**")
    cols[3].markdown("**注册时间**")
    cols[4].markdown("**权限操作**")
    cols[5].markdown("**删除**")
    
    # 显示用户数据
    for user in users:
        user_id, username, is_admin, created_at = user
        cols = st.columns([2, 2, 1.5, 2, 1.5, 1.5])
        
        cols[0].text(user_id)
        cols[1].text(username)
        cols[2].text("是" if is_admin else "否")
        cols[3].text(created_at)
        
        # 权限操作按钮
        if username != "admin":  # 防止修改默认管理员
            if cols[4].button(
                "取消管理员" if is_admin else "设为管理员",
                key=f"admin_{user_id}",
                type="secondary"
            ):
                success, message = db.toggle_admin_status(user_id)
                if success:
                    st.success(f"用户 {username} 的管理员状态已更新")
                    st.rerun()
                else:
                    st.error(message)
        
        # 删除按钮
        if username != "admin" and user_id != st.session_state.user_id:  # 防止删除默认管理员和当前用户
            if cols[5].button("删除", key=f"delete_{user_id}", type="secondary"):
                success, message = db.delete_user(user_id)
                if success:
                    st.success(f"用户 {username} 已删除")
                    st.rerun()
                else:
                    st.error(message)
    
    # 添加返回按钮
    if st.button("返回主界面", type="primary"):
        st.session_state.show_admin_panel = False
        st.rerun()

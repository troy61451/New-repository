import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import json
import hashlib
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from textblob import TextBlob 
from snownlp import SnowNLP 

# ==========================================
# 0. 云端用户数据管理 (JSONBin)
# ==========================================

# ✅ 已填入你的云端密钥
BIN_ID = "69290568d0ea881f4004c691"
BIN_API_KEY = "$2a$10$CnDfqWlL.llsLOaGhr6gBOaiGdAaeyZmpmJxO384DTFPZrWEgeWja"

class DataManager:
    def __init__(self):
        self.base_url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
        self.headers = {
            "X-Master-Key": BIN_API_KEY,
            "Content-Type": "application/json"
        }

    # 从云端读取数据
    def _load_all_data(self):
        try:
            # 加 latest 是为了获取最新版本
            response = requests.get(self.base_url + "/latest", headers=self.headers)
            if response.status_code == 200:
                # JSONBin v3 的数据在 record 字段里
                return response.json().get("record", {})
            else:
                return {}
        except: return {}

    # 保存数据到云端
    def _save_all_data(self, data):
        try:
            requests.put(self.base_url, headers=self.headers, json=data)
        except Exception as e:
            print(f"Save Error: {e}")

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    # 注册
    def register(self, username, password):
        data = self._load_all_data()
        if username in data:
            return False, "用户已存在"
        
        data[username] = {
            "password": self._hash_password(password),
            "watchlist": {} 
        }
        self._save_all_data(data)
        return True, "注册成功，请登录"

    # 登录
    def login(self, username, password):
        data = self._load_all_data()
        if username not in data:
            return False, None
        
        if data[username]["password"] == self._hash_password(password):
            return True, data[username].get("watchlist", {})
        return False, None

    # 实时同步自选股
    def save_user_watchlist(self, username, watchlist):
        data = self._load_all_data()
        if username in data:
            data[username]["watchlist"] = watchlist
            self._save_all_data(data)

data_manager = DataManager()

# ==========================================
# 1. 基础配置 & 状态管理
# ==========================================
st.set_page_config(layout="wide", page_title="全能操盘手系统", page_icon="📈")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'my_watchlist' not in st.session_state: st.session_state.my_watchlist = {} 
if 'custom_assets' not in st.session_state: st.session_state.custom_assets = {}

# 登录页
def render_login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 全能操盘手 - 云端版</h1>", unsafe_allow_html=True)
    st.info("☁️ 数据已接入云端，手机/电脑/iPad 均可实时同步。")
    
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
    with tab1:
        with st.form("login"):
            user = st.text_input("用户名")
            pwd = st.text_input("密码", type="password")
            if st.form_submit_button("登录", type="primary"):
                with st.spinner("正在连接云端数据库..."):
                    success, user_watchlist = data_manager.login(user, pwd)
                
                if success:
                    st.session_state.logged_in = True
                    st.session_state.current_user = user
                    st.session_state.my_watchlist = user_watchlist
                    st.success("登录成功！")
                    st.rerun()
                else: st.error("账号或密码错误，或者该账号未注册")
    with tab2:
        with st.form("reg"):
            new_user = st.text_input("新用户名"); new_pwd = st.text_input("新密码", type="password")
            if st.form_submit_button("注册账号"):
                if new_user and new_pwd:
                    with st.spinner("正在写入云端..."):
                        ok, msg = data_manager.register(new_user, new_pwd)
                    if ok: st.success(msg)
                    else: st.error(msg)
                else: st.error("请填写完整")

# 资产池
DEFAULT_ASSETS_GLOBAL = {
    "纳指ETF(美成长)": "513100.SS", "标普500(美大盘)": "513500.SS",
    "日经ETF(日本)": "513520.SS", "德国ETF(欧洲)": "513030.SS",
    "黄金ETF(避险)": "518880.SS", "红利ETF(防守)": "510880.SS",
    "沪深300(A核心)": "510300.SS", "创业板(A成长)": "159915.SZ"
}
ASSETS_CN = {
    "半导体ETF": "512480.SS", "芯片ETF": "159995.SZ",
    "光伏ETF": "515790.SS",   "新能车": "515030.SS",
    "军工ETF": "512660.SS",   "证券ETF": "512880.SS",
    "酒ETF": "512690.SS",     "医药ETF": "512010.SS",
    "银行ETF": "512800.SS",   "房地产": "512200.SS",
    "家电ETF": "159996.SZ",   "煤炭ETF": "515220.SS",
    "有色ETF": "512400.SS",   "传媒ETF": "512980.SS"
}
ASSETS_GLOBAL = {**DEFAULT_ASSETS_GLOBAL, **st.session_state.custom_assets}

# 名称配置
NAME_STRATEGY_TAB = "⚔️ 策略看板"
NAME_NEWS_TAB = "📰 舆情雷达"
NAME_WATCHLIST_TAB = "⭐ 我的自选"
SUB_NAME_GLOBAL = "🌍 全球核心"
SUB_NAME_CN = "🇨🇳 行业龙头"
SUB_NAME_500 = "🔥 中证500"
SUB_NAME_BACKTEST = "🛠️ 历史回测"

# ==========================================
# 2. 核心功能函数
# ==========================================

def smart_format_code(raw_code):
    code = raw_code.strip().upper()
    if "." in code: return code 
    if code.isdigit():
        if len(code) == 6: 
            if code.startswith(('60', '68', '51', '58')): return f"{code}.SS"
            else: return f"{code}.SZ"
        elif len(code) <= 5: return f"{int(code):04d}.HK"
    return code 

def fetch_stock_name(symbol):
    try:
        if symbol.endswith(".SS") or symbol.endswith(".SZ"):
            market = "sh" if symbol.endswith(".SS") else "sz"
            code = symbol.replace(".SS", "").replace(".SZ", "")
            r = requests.get(f"http://hq.sinajs.cn/list={market}{code}", timeout=2)
            if "=\"" in r.text:
                content = r.text.split("=\"")[1]
                if len(content) > 1: return content.split(",")[0]
        if symbol.endswith(".HK"):
            code = symbol.replace(".HK", "")
            r = requests.get(f"http://hq.sinajs.cn/list=hk{code}", timeout=2)
            if "=\"" in r.text:
                content = r.text.split("=\"")[1]
                if len(content) > 1: return content.split(",")[1]
        t = yf.Ticker(symbol)
        return t.info.get('shortName') or t.info.get('longName') or symbol
    except: return symbol

@st.cache_data(ttl=3600)
def get_market_temperature():
    tickers = list(ASSETS_CN.values())
    try:
        data = yf.download(tickers, period="30d", progress=False, threads=False)['Close']
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        if isinstance(data, pd.Series): data = data.to_frame(name=tickers[0])
        bull_count = 0; total_count = 0
        for code in tickers:
            try:
                if code not in data.columns: continue
                s = data[code].dropna()
                if len(s) < 20: continue
                if s.iloc[-1] > s.rolling(20).mean().iloc[-1]: bull_count += 1
                total_count += 1
            except: pass
        if total_count == 0: return 50
        return (bull_count / total_count) * 100
    except: return 50

def get_google_news(query, lang='zh-CN'):
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl=CN&ceid=CN:{lang}"
    try:
        response = requests.get(rss_url, timeout=5)
        root = ET.fromstring(response.content)
        news_items = []; count = 0
        for item in root.findall

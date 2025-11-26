import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(layout="wide", page_title="全能量化决策系统", page_icon="⚔️")

# 全球核心资产池
ASSETS_GLOBAL = {
    "纳指ETF(美成长)": "513100.SS", "标普500(美大盘)": "513500.SS",
    "日经ETF(日本)": "513520.SS", "德国ETF(欧洲)": "513030.SS",
    "黄金ETF(避险)": "518880.SS", "红利ETF(防守)": "510880.SS",
    "沪深300(A核心)": "510300.SS", "创业板(A成长)": "159915.SZ"
}

# A股核心行业池
ASSETS_CN = {
    "半导体ETF": "512480.SS", "芯片ETF": "159995.SZ",
    "光伏ETF": "515790.SS",   "新能车": "515030.SS",
    "军工ETF": "512660.SS",   "证券ETF": "512880.SS",
    "酒ETF": "512690.SS",     "医药ETF": "512010.SS",
    "银行ETF": "512800.SS",   "房地产": "512200.SS",
    "家电ETF": "159996.SZ",   "煤炭ETF": "515220.SS",
    "有色ETF": "512400.SS",   "传媒ETF": "512980.SS"
}

# ==========================================
# 2. 侧边栏：策略总控
# ==========================================
with st.sidebar:
    st.title("🎛️ 策略控制台")
    st.markdown("---")
    
    # 策略选择器
    strategy_mode = st.radio(
        "🎯 请选择策略模式:",
        (
            "🚀 动量轮动 (谁涨买谁)", 
            "🛡️ 超跌反弹 (谁跌买谁)",
            "⚔️ 双均线趋势 (金叉买入)"
        )
    )
    
    st.info(f"当前模式：**{strategy_mode}**")
    
    if st.button

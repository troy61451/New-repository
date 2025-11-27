import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

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
# 侧边栏
# ==========================================
with st.sidebar:
    st.title("🎛️ 策略控制台")
    st.markdown("---")
    strategy_mode = st.radio(
        "🎯 实时计算模式:",
        ("🚀 动量轮动 (谁涨买谁)", "🛡️ 超跌反弹 (谁跌买谁)", "⚔️ 双均线趋势 (金叉买入)")
    )
    st.info(f"当前模式：**{strategy_mode}**")
    if st.button("🔄 强制刷新数据"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 数据引擎 (实时)
# ==========================================
@st.cache_data(ttl=3600) 
def get_momentum_data(asset_dict):
    tickers = list(asset_dict.values())
    try:
        data = yf.download(tickers, period="6mo", progress=False)
        if 'Close' in data: df_close = data['Close']
        else: df_close = data
        results = []
        for name, code in asset_dict.items():
            try:
                series = df_close[code].dropna()
                if len(series) < 21: continue
                mom = (series.iloc[-1] - series.iloc[-21]) / series.iloc[-21] * 100
                results.append({"name": name, "code": code, "price": series.iloc[-1], "value": mom})
            except: pass
        return pd.DataFrame(results)
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_ma_data(asset_dict):
    tickers = list(asset_dict.values())
    try:
        data = yf.download(tickers, period="1y", progress=False)
        if 'Close' in data: df_close = data['Close']
        else: df_close = data
        results = []
        for name, code in asset_dict.items():
            try:
                series = df_close[code].dropna()
                if len(series) < 61: continue
                ma20 = series.rolling(20).mean().iloc[-1]
                ma60 = series.rolling(60).mean().iloc[-1]
                gap = (ma20 - ma60) / ma60 * 100
                results.append({"name": name, "code": code, "price": series.iloc[-1], "ma20": ma20, "ma60": ma60, "value": gap})
            except: pass
        return pd.DataFrame(results)
    except: return pd.DataFrame()

# ==========================================
# 读取中证500 CSV
# ==========================================
@st.cache_data
def load_csi500_rank():
    try:
        return pd.read_csv("csi500_rank.csv")
    except: return pd.DataFrame()

# ==========================================
# 页面渲染
# ==========================================
st.title(f"📊 量化决策系统")
tab1, tab2, tab3 = st.tabs(["🌍 全球宏观", "🇨🇳 A股行业", "🔥 中证500龙头"])

# --- 通用页面 ---
def render_page(asset_dict):
    if "双均线" in strategy_mode:
        with st.spinner('正在计算均线...'): df = get_ma_data(asset_dict)
    else:
        with st.spinner('正在计算动量...'): df = get_momentum_data(asset_dict)
    
    if df.empty: st.warning("暂无数据"); return
    
    ascending = True if "超跌" in strategy_mode else False
    df = df.sort_values(by="value", ascending=ascending).reset_index(drop=True)
    df.index += 1
    top = df.iloc[0]
    
    c1, c2, c3 = st.columns(3)
    if "双均线" in strategy_mode:
        if top['ma20'] > top['ma60']: c1.success(f"🚀 {top['name']}"); c1.caption("金叉")
        else: c1.error("🛑 空仓"); c1.caption("死叉")
        c2.metric("MA20", f"{top['ma20']:.2f}"); c3.metric("MA60", f"{top['ma60']:.2f}")
    elif "超跌" in strategy_mode:
        c1.success(f"🛡️ 抄底: {top['name']}"); c2.metric("价格", f"{top['price']:.2f}"); c3.metric("跌幅", f"{top['value']:.2f}%")
    else:
        if top['value']<0: c1.error("🛑 空仓"); c1.caption("普跌")
        else: c1.success(f"🚀 买入: {top['name']}")
        c2.metric("价格", f"{top['price']:.2f}"); c3.metric("涨幅", f"{top['value']:.2f}%")
    
    st.markdown("---")
    st.subheader(f"📈 {top['name']} 走势")
    try:
        k_df = yf.download(top['code'], period="1y", progress=False)
        if isinstance(k_df.columns, pd.MultiIndex): k_df.columns = k_df.columns.get_level_values(0)
        k_df['MA20'] = k_df['Close'].rolling(20).mean()
        fig = go.Figure(data=[go.Candlestick(x=k_df.index, open=k_df['Open'], high=k_df['High'], low=k_df['Low'], close=k_df['Close'])])
        fig.add_trace(go.Scatter(x=k_df.index, y=k_df['MA20'], mode='lines', line=dict(color='orange')))
        fig.update_layout(height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except: pass
    st.dataframe(df, use_container_width=True)

# --- 中证500页面 ---
def render_csi500():
    df = load_csi500_rank()
    if df.empty: st.warning("后台数据正在生成中..."); return

    top = df.iloc[0]
    # 🔥 显示冠军名称 + 代码
    st.success(f"🚀 冠军: **{top['名称']}** ({top['代码']})")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("20日涨幅", f"{top['20日涨幅']}%", "领跑")
    c2.metric("当前价格", f"¥{top['当前价']}")
    c3.metric("更新时间", "每日收盘")
    
    st.markdown("---")
    
    # K线选择器 (显示名称)
    # 把 "300390.SZ" 变成 "300390.SZ | 通达动力" 方便选择
    select_options = [f"{row['代码']} | {row['名称']}" for index, row in df.head(20).iterrows()]
    selected_str = st.selectbox("查看K线:", select_options)
    
    if selected_str:
        code = selected_str.split(" | ")[0]
        name = selected_str.split(" | ")[1]
        with st.spinner(f"加载 {name} K线..."):
            try:
                k_df = yf.download(code, period="6mo", progress=False)
                if isinstance(k_df.columns, pd.MultiIndex): k_df.columns = k_df.columns.get_level_values(0)
                fig = go.Figure(data=[go.Candlestick(x=k_df.index, open=k_df['Open'], high=k_df['High'], low=k_df['Low'], close=k_df['Close'])])
                fig.update_layout(height=450, title=f"{name} ({code})", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            except: st.error("K线加载失败")

    st.markdown("---")
    st.subheader("📋 强势股名单")
    # 调整列顺序，名称放前面
    st.dataframe(df[['代码', '名称', '当前价', '20日涨幅']], use_container_width=True)

with tab1: render_page(ASSETS_GLOBAL)
with tab2: render_page(ASSETS_CN)
with tab3: render_csi500()

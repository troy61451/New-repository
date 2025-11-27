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
    
    # 策略选择器 (只对前两个Tab有效)
    strategy_mode = st.radio(
        "🎯 实时计算模式:",
        (
            "🚀 动量轮动 (谁涨买谁)", 
            "🛡️ 超跌反弹 (谁跌买谁)",
            "⚔️ 双均线趋势 (金叉买入)"
        )
    )
    
    st.info(f"当前模式：**{strategy_mode}**")
    st.caption("注：'中证500'页面使用独立数据源(后台每日更新)")
    
    if st.button("🔄 强制刷新数据"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 3. 数据计算引擎 (实时)
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
                curr = series.iloc[-1]
                mom = (curr - series.iloc[-21]) / series.iloc[-21] * 100
                results.append({"name": name, "code": code, "price": curr, "value": mom})
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
                curr = series.iloc[-1]
                ma20 = series.rolling(20).mean().iloc[-1]
                ma60 = series.rolling(60).mean().iloc[-1]
                gap = (ma20 - ma60) / ma60 * 100
                results.append({"name": name, "code": code, "price": curr, "ma20": ma20, "ma60": ma60, "value": gap})
            except: pass
        return pd.DataFrame(results)
    except: return pd.DataFrame()

# ==========================================
# 4. 新增：读取中证500 CSV
# ==========================================
@st.cache_data
def load_csi500_rank():
    try:
        # 直接读取 GitHub Actions 生成的文件
        # 注意：这里读取的是 GitHub 仓库里的相对路径文件
        df = pd.read_csv("csi500_rank.csv")
        return df
    except Exception:
        return pd.DataFrame()

# ==========================================
# 5. 页面渲染逻辑
# ==========================================
st.title(f"📊 量化决策系统")

# 创建三个标签页
tab1, tab2, tab3 = st.tabs(["🌍 全球宏观", "🇨🇳 A股行业", "🔥 中证500龙头"])

# --- 渲染通用页面 (Tab 1 & 2) ---
def render_page(asset_dict):
    if "双均线" in strategy_mode:
        with st.spinner('正在计算均线...'):
            df = get_ma_data(asset_dict)
    else:
        with st.spinner('正在计算动量...'):
            df = get_momentum_data(asset_dict)
    
    if df.empty:
        st.warning("暂无数据")
        return

    is_ascending = True if "超跌" in strategy_mode else False
    df = df.sort_values(by="value", ascending=is_ascending).reset_index(drop=True)
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
        fig = go.Figure(data=[go.Candlestick(x=k_df.index, open=k_df['Open'], high=k_df['High'], low=k_df['Low'], close=k_df['Close'], name='K线')])
        fig.add_trace(go.Scatter(x=k_df.index, y=k_df['MA20'], mode='lines', line=dict(color='orange', width=1)))
        fig.update_layout(height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except: pass
    st.dataframe(df, use_container_width=True)

# --- 渲染中证500页面 (Tab 3) ---
def render_csi500():
    df = load_csi500_rank()
    
    if df.empty:
        st.info("💡 后台正在努力计算中... (每天下午更新)")
        st.warning("暂未找到 ranking 文件，请确保 GitHub Action 运行成功。")
        return

    # 1. 冠军展示
    top = df.iloc[0]
    st.success(f"🚀 今日中证500 冠军: **{top['代码']}**")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("20日涨幅", f"{top['20日涨幅']}%", "领跑全场")
    col2.metric("当前价格", f"¥{top['当前价']}")
    col3.metric("数据时间", "每日收盘后更新")
    
    st.markdown("---")
    
    # 2. 交互式 K线查看器
    st.subheader("🔍 龙头股 K线透视")
    # 让用户选择想看哪只股票（默认选第一名）
    selected_code = st.selectbox("选择股票查看详情:", df['代码'].head(20).tolist())
    
    if selected_code:
        with st.spinner(f"正在加载 {selected_code} K线..."):
            try:
                k_df = yf.download(selected_code, period="6mo", progress=False)
                if isinstance(k_df.columns, pd.MultiIndex): k_df.columns = k_df.columns.get_level_values(0)
                
                fig = go.Figure(data=[go.Candlestick(x=k_df.index, open=k_df['Open'], high=k_df['High'], low=k_df['Low'], close=k_df['Close'])])
                fig.update_layout(height=450, title=f"{selected_code} 日线图", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"K线加载失败: {e}")

    # 3. 完整表格
    st.markdown("---")
    st.subheader("📋 Top 50 强势股名单")
    st.dataframe(df, use_container_width=True)

# 渲染所有标签页
with tab1:
    render_page(ASSETS_GLOBAL)
with tab2:
    render_page(ASSETS_CN)
with tab3:
    render_csi500()

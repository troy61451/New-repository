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
    
    # --- 注意：之前报错就是这里少了冒号 ---
    if st.button("🔄 强制刷新数据"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 3. 数据计算引擎
# ==========================================

# 引擎 A: 计算涨跌幅
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
                prev = series.iloc[-21]
                mom = (curr - prev) / prev * 100
                
                results.append({"name": name, "code": code, "price": curr, "value": mom})
            except: pass
        return pd.DataFrame(results)
    except: return pd.DataFrame()

# 引擎 B: 计算均线金叉
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
                
                results.append({
                    "name": name, "code": code, "price": curr, 
                    "ma20": ma20, "ma60": ma60, "value": gap
                })
            except: pass
        return pd.DataFrame(results)
    except: return pd.DataFrame()

# ==========================================
# 4. 页面渲染逻辑
# ==========================================
st.title(f"📊 量化决策系统 - {strategy_mode.split(' ')[1]}")

tab1, tab2 = st.tabs(["🌍 全球宏观", "🇨🇳 A股行业"])

def render_page(asset_dict, title):
    if "双均线" in strategy_mode:
        with st.spinner('正在计算 MA20/MA60 均线关系...'):
            df = get_ma_data(asset_dict)
    else:
        with st.spinner('正在分析 20日 资金流向...'):
            df = get_momentum_data(asset_dict)
    
    if df.empty:
        st.warning("暂无数据，请稍后刷新")
        return

    # 排序
    is_ascending = True if "超跌" in strategy_mode else False
    df = df.sort_values(by="value", ascending=is_ascending).reset_index(drop=True)
    df.index += 1
    
    top = df.iloc[0]
    
    # 信号区
    c1, c2, c3 = st.columns(3)
    
    if "双均线" in strategy_mode:
        if top['ma20'] > top['ma60']:
            c1.success(f"🚀 建议持有: {top['name']}")
            c1.caption("金叉 (MA20 > MA60)")
        else:
            c1.error("🛑 建议空仓")
            c1.caption("全市场均为死叉")
        c2.metric("MA20", f"{top['ma20']:.2f}")
        c3.metric("MA60", f"{top['ma60']:.2f}", delta=f"开口 {top['value']:.2f}%")
        
    elif "超跌" in strategy_mode:
        c1.success(f"🛡️ 建议抄底: {top['name']}")
        c1.caption(f"跌幅最深 ({top['value']:.2f}%)")
        c2.metric("当前价格", f"{top['price']:.3f}")
        c3.metric("超跌幅度", f"{top['value']:.2f}%")
        
    else:
        if top['value'] < 0:
            c1.error("🛑 建议空仓 (Cash)")
            c1.caption("市场普跌")
        else:
            c1.success(f"🚀 建议买入: {top['name']}")
            c1.caption("领涨抗跌")
        c2.metric("当前价格", f"{top['price']:.3f}")
        c3.metric("动量强度", f"{top['value']:.2f}%")

    st.markdown("---")
    
    # 画图
    st.subheader(f"📈 {top['name']} 趋势验证")
    try:
        k_df = yf.download(top['code'], period="1y", progress=False)
        if isinstance(k_df.columns, pd.MultiIndex): k_df.columns = k_df.columns.get_level_values(0)
        
        k_df['MA20'] = k_df['Close'].rolling(20).mean()
        k_df['MA60'] = k_df['Close'].rolling(60).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=k_df.index, open=k_df['Open'], high=k_df['High'], low=k_df['Low'], close=k_df['Close'], name='K线'))
        fig.add_trace(go.Scatter(x=k_df.index, y=k_df['MA20'], mode='lines', name='MA20', line=dict(color='#f1c40f', width=1.5)))
        fig.add_trace(go.Scatter(x=k_df.index, y=k_df['MA60'], mode='lines', name='MA60', line=dict(color='#3498db', width=1.5)))
        
        fig.update_layout(height=450, xaxis_rangeslider_visible=False, title=top['name'])
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.error("K线数据加载失败")

    # 表格
    st.subheader("📋 详细排名表")
    st.dataframe(df, use_container_width=True)

with tab1:
    render_page(ASSETS_GLOBAL, "全球资产")
with tab2:
    render_page(ASSETS_CN, "A股行业")

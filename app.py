import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots # 🔥 新增：用来画子图(K线+成交量)
from datetime import datetime

# ==========================================
# 1. 页面基础配置 (改为宽屏模式)
# ==========================================
st.set_page_config(layout="wide", page_title="全能量化决策系统", page_icon="📈")

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
# 2. 侧边栏
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
# 3. 核心绘图函数 (🔥 专业暗黑版)
# ==========================================
def plot_pro_chart(ticker, name):
    try:
        # 下载数据 (包含成交量 Volume)
        df = yf.download(ticker, period="1y", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 计算均线
        df['MA5'] = df['Close'].rolling(5).mean()  # 短线
        df['MA20'] = df['Close'].rolling(20).mean() # 生命线
        df['MA60'] = df['Close'].rolling(60).mean() # 趋势线

        # 1. 创建子图 (2行1列：上面K线，下面成交量)
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            subplot_titles=(f"{name} ({ticker})", "成交量"),
            row_heights=[0.7, 0.3] # K线占70%，成交量占30%
        )

        # 2. 画 K线 (红涨绿跌)
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name="K线",
            increasing_line_color='#fd3030', # 中国红
            decreasing_line_color='#00f0f0'  # 甚至可以用青色，或者绿色 #25cdcd
        ), row=1, col=1)

        # 3. 画均线 (鲜艳颜色)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], mode='lines', name='MA5', line=dict(color='white', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='MA20', line=dict(color='#f1c40f', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='MA60', line=dict(color='#bd00ff', width=1.5)), row=1, col=1)

        # 4. 画成交量 (颜色跟随涨跌)
        # 如果收盘价 > 开盘价，由于是红柱，成交量也红；反之绿
        colors = ['#fd3030' if row['Open'] < row['Close'] else '#00f0f0' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'],
            name='成交量',
            marker_color=colors
        ), row=2, col=1)

        # 5. 设置暗黑主题 (Dark Mode)
        fig.update_layout(
            template='plotly_dark', # 🔥 关键：切换到暗黑模板
            xaxis_rangeslider_visible=False, # 隐藏底部滑块
            height=600, # 图表高度
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor='black', # 背景全黑
            plot_bgcolor='#111111', # 绘图区深灰
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # 去掉一些杂乱的网格线
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333333')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333333')

        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"图表加载失败: {e}")

# ==========================================
# 4. 数据计算引擎
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
# 5. 读取中证500
# ==========================================
@st.cache_data
def load_csi500_rank():
    try: return pd.read_csv("csi500_rank.csv")
    except: return pd.DataFrame()

# ==========================================
# 6. 页面渲染
# ==========================================
st.title(f"📊 量化决策系统")
tab1, tab2, tab3 = st.tabs(["🌍 全球宏观", "🇨🇳 A股行业", "🔥 中证500龙头"])

def render_page(asset_dict):
    if "双均线" in strategy_mode:
        with st.spinner('计算均线...'): df = get_ma_data(asset_dict)
    else:
        with st.spinner('计算动量...'): df = get_momentum_data(asset_dict)
    
    if df.empty: st.warning("暂无数据"); return
    
    ascending = True if "超跌" in strategy_mode else False
    df = df.sort_values(by="value", ascending=ascending).reset_index(drop=True)
    df.index += 1
    top = df.iloc[0]
    
    c1, c2, c3 = st.columns(3)
    # 简单的信号展示
    if "双均线" in strategy_mode:
        if top['ma20'] > top['ma60']: c1.success(f"🚀 {top['name']}"); c1.caption("金叉")
        else: c1.error("🛑 空仓"); c1.caption("死叉")
    elif "超跌" in strategy_mode:
        c1.success(f"🛡️ 抄底: {top['name']}")
    else:
        if top['value']<0: c1.error("🛑 空仓"); c1.caption("普跌")
        else: c1.success(f"🚀 买入: {top['name']}")
        
    c2.metric("价格", f"{top['price']:.2f}")
    c3.metric("强度", f"{top['value']:.2f}%")
    
    st.markdown("---")
    # 🔥 调用新的专业绘图函数
    st.subheader(f"📈 {top['name']} 走势分析")
    plot_pro_chart(top['code'], top['name'])
    
    st.dataframe(df, use_container_width=True)

def render_csi500():
    df = load_csi500_rank()
    if df.empty: st.warning("后台数据正在生成中..."); return
    top = df.iloc[0]
    st.success(f"🚀 冠军: **{top['名称']}** ({top['代码']})")
    c1, c2, c3 = st.columns(3)
    c1.metric("20日涨幅", f"{top['20日涨幅']}%")
    c2.metric("当前价格", f"¥{top['当前价']}")
    c3.metric("更新时间", "每日收盘")
    st.markdown("---")
    
    # K线选择器
    select_options = [f"{row['代码']} | {row['名称']}" for index, row in df.head(20).iterrows()]
    selected_str = st.selectbox("查看K线:", select_options)
    
    if selected_str:
        code = selected_str.split(" | ")[0]
        name = selected_str.split(" | ")[1]
        st.subheader(f"📈 {name} 走势分析")
        # 🔥 调用新的专业绘图函数
        plot_pro_chart(code, name)

    st.markdown("---")
    st.subheader("📋 强势股名单")
    st.dataframe(df[['代码', '名称', '当前价', '20日涨幅']], use_container_width=True)

with tab1: render_page(ASSETS_GLOBAL)
with tab2: render_page(ASSETS_CN)
with tab3: render_csi500()

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ==========================================
# 1. 页面配置 (宽屏 + 暗黑图表)
# ==========================================
st.set_page_config(layout="wide", page_title="全能操盘手系统", page_icon="📈")

# 资产池定义
ASSETS_GLOBAL = {
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

# ==========================================
# 2. 侧边栏
# ==========================================
with st.sidebar:
    st.title("🎛️ 操盘控制台")
    st.markdown("---")
    strategy_mode = st.radio(
        "🎯 模式选择:",
        ("🚀 动量轮动", "🛡️ 超跌反弹", "⚔️ 双均线金叉")
    )
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 3. 核心绘图引擎 (1:1 复刻专业版)
# ==========================================
def plot_pro_chart(ticker, name):
    try:
        # 1. 下载更长的数据 (2年) 以便计算MACD
        df = yf.download(ticker, period="2y", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 2. 计算技术指标
        # 均线
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        
        # MACD (核心算法)
        # EMA12, EMA26
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        # DIF (快线)
        df['DIF'] = ema12 - ema26
        # DEA (慢线)
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        # MACD柱子 (乘以2符合国内习惯)
        df['MACD'] = (df['DIF'] - df['DEA']) * 2

        # 3. 创建三栏子图 (K线 / 成交量 / MACD)
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.02, 
            row_heights=[0.6, 0.2, 0.2], # 高度比例
            subplot_titles=(f"{name} ({ticker})", "", "") # 只显示顶部标题
        )

        # --- 第一栏：K线 + 均线 ---
        # K线
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="K线", increasing_line_color='#fd3030', decreasing_line_color='#00f0f0'
        ), row=1, col=1)
        
        # 均线 (MA5白, MA10黄, MA20紫)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='white', width=1), name='MA5'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='#ffd700', width=1), name='MA10'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#ff00ff', width=1), name='MA20'), row=1, col=1)

        # --- 第二栏：成交量 ---
        vol_colors = ['#fd3030' if row['Open'] < row['Close'] else '#00f0f0' for i, row in df.iterrows()]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'], marker_color=vol_colors, name='成交量', showlegend=False
        ), row=2, col=1)

        # --- 第三栏：MACD ---
        # 柱状图 (红绿柱)
        macd_colors = ['#fd3030' if val >= 0 else '#00f0f0' for val in df['MACD']]
        fig.add_trace(go.Bar(
            x=df.index, y=df['MACD'], marker_color=macd_colors, name='MACD柱', showlegend=False
        ), row=3, col=1)
        # DIF线 (白)
        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='white', width=1), name='DIF'), row=3, col=1)
        # DEA线 (黄)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='#ffd700', width=1), name='DEA'), row=3, col=1)

        # --- 4. 深度美化 (关键步骤) ---
        fig.update_layout(
            template='plotly_dark', # 暗黑模式
            height=700,             # 总高度增加
            xaxis_rangeslider_visible=False,
            paper_bgcolor='#000000', # 纯黑背景
            plot_bgcolor='#0e0e0e',  # 绘图区深灰
            margin=dict(l=5, r=5, t=30, b=5),
            hovermode='x unified',   # 十字光标效果
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0)
        )
        
        # 增加时间切换按钮 (1月, 3月, 6月, 1年)
        fig.update_xaxes(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1月", step="month", stepmode="backward"),
                    dict(count=3, label="3月", step="month", stepmode="backward"),
                    dict(count=6, label="半年", step="month", stepmode="backward"),
                    dict(count=1, label="1年", step="year", stepmode="backward"),
                    dict(step="all", label="全部")
                ]),
                bgcolor="#333", activecolor="#555", font=dict(color="white")
            ),
            row=1, col=1
        )

        # 隐藏子图的Y轴刻度线，让画面更干净
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#222')
        fig.update_xaxes(showgrid=False, rangebreaks=[dict(bounds=["sat", "mon"])]) # 隐藏周末

        st.plotly_chart(fig, use_container

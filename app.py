import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide", page_title="量化决策系统", page_icon="📈")

# ==========================================
# 1. 资产池定义
# ==========================================
# 全球核心资产
ASSETS_GLOBAL = {
    "纳指ETF(美成长)": "513100.SS", "标普500(美大盘)": "513500.SS",
    "日经ETF(日本)": "513520.SS", "德国ETF(欧洲)": "513030.SS",
    "黄金ETF(避险)": "518880.SS", "红利ETF(防守)": "510880.SS",
    "沪深300(A核心)": "510300.SS", "创业板(A成长)": "159915.SZ"
}

# A股核心行业 (抓主线)
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
# 2. 核心计算函数
# ==========================================
@st.cache_data(ttl=3600) 
def get_momentum_data(asset_dict):
    tickers = list(asset_dict.values())
    try:
        data = yf.download(tickers, period="6mo", progress=False)
        if 'Close' in data:
            df_close = data['Close']
        else:
            df_close = data
        
        results = []
        for name, code in asset_dict.items():
            try:
                # 提取并清理数据
                series = df_close[code].dropna()
                if len(series) < 21: continue
                
                curr = series.iloc[-1]
                prev = series.iloc[-21]
                mom = (curr - prev) / prev * 100
                
                results.append({"name": name, "code": code, "price": curr, "momentum": mom})
            except:
                pass
        return pd.DataFrame(results)
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# 3. 界面逻辑
# ==========================================
st.title("🚀 量化决策系统 (全球+A股)")

tab1, tab2 = st.tabs(["🌍 全球宏观轮动", "🇨🇳 A股行业轮动"])

def render_page(asset_dict, title):
    with st.spinner(f'正在分析 {title} 资金流向...'):
        df = get_momentum_data(asset_dict)
    
    if not df.empty:
        df = df.sort_values(by="momentum", ascending=False).reset_index(drop=True)
        df.index += 1
        
        top = df.iloc[0]
        is_crash = top['momentum'] < 0
        
        # 信号区
        c1, c2, c3 = st.columns(3)
        if is_crash:
            c1.error("🛑 建议空仓/现金")
            c1.caption("市场普跌，无赚钱效应")
        else:
            c1.success(f"🚀 建议买入：{top['name']}")
            c1.caption(f"领涨板块 (20日涨幅: {top['momentum']:.2f}%)")
            
        c2.metric("最强标的", top['name'], f"{top['momentum']:.2f}%")
        c3.metric("当前价格", f"¥{top['price']:.3f}")
        
        st.markdown("---")
        
        # K线图
        if not is_crash:
            st.subheader(f"📈 {top['name']} 趋势确认")
            k_df = yf.download(top['code'], period="6mo", progress=False)
            if isinstance(k_df.columns, pd.MultiIndex): k_df.columns = k_df.columns.get_level_values(0)
            
            fig = go.Figure(data=[go.Candlestick(
                x=k_df.index, open=k_df['Open'], high=k_df['High'], low=k_df['Low'], close=k_df['Close']
            )])
            fig.update_layout(height=400, xaxis_rangeslider_visible=False, title=top['name'])
            st.plotly_chart(fig, use_container_width=True)
        
        # 排行榜
        st.subheader("📋 强度排行榜")
        st.dataframe(df.style.format({"momentum": "{:.2f}%", "price": "{:.3f}"}), use_container_width=True)

with tab1:
    render_page(ASSETS_GLOBAL, "全球资产")

with tab2:
    render_page(ASSETS_CN, "A股行业")

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(layout="wide", page_title="全球宏观对冲系统", page_icon="🌍")

# 全球核心资产池 (代码适配 Yahoo)
ASSETS = {
    "纳指ETF(美成长)": "513100.SS",
    "标普500(美大盘)": "513500.SS",
    "日经ETF(日本)": "513520.SS",
    "德国ETF(欧洲)": "513030.SS",
    "沪深300(A核心)": "510300.SS",
    "创业板(A成长)": "159915.SZ",
    "红利ETF(A防守)": "510880.SS",
    "黄金ETF(避险)": "518880.SS"
}

st.title("🌍 全球核心资产轮动 App (云端版)")

# ==========================================
# 2. 核心策略逻辑 (含风控)
# ==========================================
@st.cache_data(ttl=3600) # 数据缓存1小时，避免频繁请求
def get_strategy_data():
    tickers = list(ASSETS.values())
    # 下载过去半年的数据
    data = yf.download(tickers, period="6mo", progress=False)
    
    if 'Close' in data:
        df_close = data['Close']
    else:
        df_close = data

    results = []
    for name, code in ASSETS.items():
        try:
            # 提取单只股票
            series = df_close[code].dropna()
            if len(series) < 21: continue

            curr = series.iloc[-1]
            prev = series.iloc[-21] # 20天前
            
            # 动量公式
            mom = (curr - prev) / prev * 100
            
            results.append({
                "name": name, "code": code,
                "price": curr, "momentum": mom
            })
        except:
            pass
    
    return pd.DataFrame(results)

# ==========================================
# 3. 侧边栏与手动刷新
# ==========================================
with st.sidebar:
    st.header("⚙️ 策略控制")
    # 添加一个手动刷新按钮
    if st.button("🔄 强制刷新数据"):
        st.cache_data.clear()
        st.rerun()
    
    st.info("""
    **🛡️ 风控机制已启动**
    
    逻辑：
    1. 计算所有资产20日涨幅。
    2. 如果最强资产涨幅 > 0，买入持有。
    3. 如果最强资产涨幅 < 0，**强制空仓**。
    """)

# ==========================================
# 4. 主界面展示
# ==========================================
with st.spinner('正在连接全球交易所获取最新行情...'):
    df = get_strategy_data()

if not df.empty:
    # 按动量排序
    df = df.sort_values(by="momentum", ascending=False).reset_index(drop=True)
    df.index = df.index + 1 # 排名从1开始

    # --- 🏆 最终决策区 ---
    top_asset = df.iloc[0]
    
    # 🛑 风控判断 🛑
    is_crash_mode = top_asset['momentum'] < 0
    
    st.subheader("🤖 交易指令")
    
    col1, col2, col3 = st.columns(3)
    
    if is_crash_mode:
        # 触发风控：建议空仓
        with col1:
            st.error("🛑 建议空仓 (CASH)")
            st.caption("原因：全球资产全线下跌")
        with col2:
            st.metric("最强资产表现", f"{top_asset['name']}", f"{top_asset['momentum']:.2f}% (仍为负)")
        with col3:
            st.metric("操作", "卖出所有，持有现金")
            
    else:
        # 正常行情：建议买入
        with col1:
            st.success(f"🚀 建议买入：{top_asset['name']}")
            st.caption(f"代码: {top_asset['code']}")
        with col2:
            st.metric("20日动量", f"{top_asset['momentum']:.2f}%", "领跑全球")
        with col3:
            st.metric("当前价格", f"¥{top_asset['price']:.3f}")

    st.markdown("---")

    # --- 📊 资产排行榜 ---
    st.subheader("📋 全球资产风云榜")
    
    # 美化表格
    display_df = df.copy()
    display_df['20日涨幅'] = display_df['momentum'].apply(lambda x: f"{x:.2f}%")
    display_df['价格'] = display_df['price'].apply(lambda x: f"¥{x:.3f}")
    
    # 高亮显示正收益和负收益
    def highlight_momentum(val):
        color = 'red' if float(val.strip('%')) > 0 else 'green'
        return f'color: {color}'

    st.dataframe(
        display_df[['name', 'code', '价格', '20日涨幅']].style.map(highlight_momentum, subset=['20日涨幅']),
        use_container_width=True
    )
    
    # --- 📈 冠军K线图 ---
    st.subheader(f"📈 {top_asset['name']} 走势确认")
    if not is_crash_mode:
        k_data = yf.download(top_asset['code'], period="6mo", progress=False)
        if isinstance(k_data.columns, pd.MultiIndex): k_data.columns = k_data.columns.get_level_values(0)
        
        fig = go.Figure(data=[go.Candlestick(
            x=k_data.index, open=k_data['Open'], high=k_data['High'], low=k_data['Low'], close=k_data['Close']
        )])
        fig.update_layout(height=400, xaxis_rangeslider_visible=False, title=f"{top_asset['name']} (MA20支撑检查)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("当前建议空仓，无需查看K线。休息一下吧！☕")

else:
    st.error("数据获取失败，请点击左侧刷新按钮重试。")

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ==========================================
# 1. 页面配置
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
        "🎯 实时模式:",
        ("🚀 动量轮动", "🛡️ 超跌反弹", "⚔️ 双均线金叉")
    )
    st.markdown("---")
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 3. 核心功能函数
# ==========================================

# --- A. 专业绘图引擎 ---
def plot_pro_chart(ticker, name):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 指标计算
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        
        # MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = ema12 - ema26
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2

        # 三栏画布
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02, 
            row_heights=[0.6, 0.2, 0.2], subplot_titles=(f"{name} ({ticker})", "", "")
        )

        # K线 + 均线
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K线", increasing_line_color='#fd3030', decreasing_line_color='#00f0f0'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='white', width=1), name='MA5'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='#ffd700', width=1), name='MA10'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#ff00ff', width=1), name='MA20'), row=1, col=1)

        # 成交量
        vol_colors = ['#fd3030' if row['Open'] < row['Close'] else '#00f0f0' for i, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name='成交量', showlegend=False), row=2, col=1)

        # MACD
        macd_colors = ['#fd3030' if val >= 0 else '#00f0f0' for val in df['MACD']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD'], marker_color=macd_colors, name='MACD柱', showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='white', width=1), name='DIF'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='#ffd700', width=1), name='DEA'), row=3, col=1)

        # 布局美化
        fig.update_layout(template='plotly_dark', height=700, xaxis_rangeslider_visible=False, paper_bgcolor='#000000', plot_bgcolor='#0e0e0e', margin=dict(l=5, r=5, t=30, b=5), hovermode='x unified', legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0))
        fig.update_xaxes(rangeselector=dict(buttons=list([dict(count=1, label="1月", step="month", stepmode="backward"), dict(count=6, label="半年", step="month", stepmode="backward"), dict(step="all", label="全部")]), bgcolor="#333", activecolor="#555", font=dict(color="white")), row=1, col=1)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#222'); fig.update_xaxes(showgrid=False, rangebreaks=[dict(bounds=["sat", "mon"])])

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e: st.error(f"图表加载出错: {e}")

# --- B. 实时数据获取 ---
@st.cache_data(ttl=3600) 
def get_momentum_data(asset_dict):
    tickers = list(asset_dict.values())
    try:
        data = yf.download(tickers, period="6mo", progress=False)
        if 'Close' in data: df = data['Close']
        else: df = data
        res = []
        for n, c in asset_dict.items():
            try:
                s = df[c].dropna()
                if len(s)<21: continue
                mom = (s.iloc[-1]-s.iloc[-21])/s.iloc[-21]*100
                res.append({"name":n, "code":c, "price":s.iloc[-1], "value":mom})
            except: pass
        return pd.DataFrame(res)
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_ma_data(asset_dict):
    tickers = list(asset_dict.values())
    try:
        data = yf.download(tickers, period="1y", progress=False)
        if 'Close' in data: df = data['Close']
        else: df = data
        res = []
        for n, c in asset_dict.items():
            try:
                s = df[c].dropna()
                if len(s)<61: continue
                m20 = s.rolling(20).mean().iloc[-1]
                m60 = s.rolling(60).mean().iloc[-1]
                gap = (m20-m60)/m60*100
                res.append({"name":n, "code":c, "price":s.iloc[-1], "ma20":m20, "ma60":m60, "value":gap})
            except: pass
        return pd.DataFrame(res)
    except: return pd.DataFrame()

@st.cache_data
def load_csi500_rank():
    try: return pd.read_csv("csi500_rank.csv")
    except: return pd.DataFrame()

# ==========================================
# 4. 回测引擎 (新增功能) 🛠️
# ==========================================
def run_backtest(pool_name, start_date, end_date):
    # 1. 确定资产池
    assets = ASSETS_GLOBAL if pool_name == "全球宏观" else ASSETS_CN
    tickers = list(assets.values())
    
    with st.spinner(f"正在下载 {len(tickers)} 只资产的历史数据，进行回测..."):
        try:
            # 下载历史数据
            data = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close']
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            
            # 2. 计算每日收益率
            daily_ret = data.pct_change().dropna()
            
            # 3. 策略逻辑：每月(20交易日)轮动一次
            # 计算20日动量
            momentum = data.pct_change(20).shift(1) # 昨天收盘的动量，决定今天的持仓
            
            strategy_ret = []
            dates = []
            
            # 模拟交易循环
            # 从第21天开始
            for date, row in daily_ret.iterrows():
                if date not in momentum.index: continue
                
                # 获取当天的动量排名
                mom_row = momentum.loc[date]
                
                # 选出最强的1只
                best_code = mom_row.idxmax()
                
                # 如果所有资产动量都小于0，空仓(收益为0)？还是硬抗？
                # 这里为了简单，假设硬抗最强的
                # 实际收益 = 选中资产当天的收益
                day_pnl = row[best_code]
                
                strategy_ret.append(day_pnl)
                dates.append(date)
            
            # 4. 计算净值曲线
            equity = [1.0]
            for r in strategy_ret:
                equity.append(equity[-1] * (1 + r))
            
            # 构造DataFrame
            backtest_df = pd.DataFrame({"日期": dates, "策略净值": equity[1:]}).set_index("日期")
            
            # 5. 绘图
            st.success(f"✅ 回测完成！区间: {start_date} 至 {end_date}")
            
            total_ret = (equity[-1] - 1) * 100
            
            c1, c2 = st.columns(2)
            c1.metric("策略总收益", f"{total_ret:.2f}%")
            c1.caption("策略逻辑：每日持有过去20天涨幅第一的资产")
            
            # 画资金曲线
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df["策略净值"], mode='lines', name='策略净值', line=dict(color='#fd3030', width=2)))
            fig.update_layout(template='plotly_dark', title="资金曲线 (Equity Curve)", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"回测失败: {e}")

# ==========================================
# 5. 页面渲染
# ==========================================
st.title("📊 全能操盘手系统")
tab1, tab2, tab3, tab4 = st.tabs(["🌍 全球", "🇨🇳 行业", "🔥 中证500", "🛠️ 历史回测"])

# Tab 1 & 2 渲染
def render_common(assets):
    if "双均线" in strategy_mode:
        with st.spinner("计算均线..."): df = get_ma_data(assets)
    else:
        with st.spinner("计算动量..."): df = get_momentum_data(assets)
    if df.empty: st.warning("暂无数据"); return
    
    asc = True if "超跌" in strategy_mode else False
    df = df.sort_values("value", ascending=asc).reset_index(drop=True)
    df.index+=1
    top = df.iloc[0]

    c1,c2,c3 = st.columns(3)
    if "双均线" in strategy_mode:
        if top['ma20']>top['ma60']: c1.success(f"🚀 {top['name']}"); c1.caption("金叉")
        else: c1.error("🛑 空仓"); c1.caption("死叉")
    elif "超跌" in strategy_mode: c1.success(f"🛡️ 抄底: {top['name']}")
    else:
        if top['value']<0: c1.error("🛑 空仓"); c1.caption("普跌")
        else: c1.success(f"🚀 买入: {top['name']}")
    c2.metric("价格", f"{top['price']:.2f}")
    c3.metric("强度", f"{top['value']:.2f}%")
    st.markdown("---")
    st.subheader(f"📈 {top['name']} 专业走势")
    plot_pro_chart(top['code'], top['name'])
    st.dataframe(df, use_container_width=True)

# Tab 3 渲染
def render_500():
    df = load_csi500_rank()
    if df.empty: st.warning("后台生成中..."); return
    top = df.iloc[0]
    st.success(f"🚀 冠军: **{top['名称']}** ({top['代码']})")
    c1,c2,c3 = st.columns(3)
    c1.metric("20日涨幅", f"{top['20日涨幅']}%")
    c2.metric("当前价", f"¥{top['当前价']}")
    c3.metric("来源", "后台优选")
    st.markdown("---")
    opts = [f"{r['代码']} | {r['名称']}" for i,r in df.head(20).iterrows()]
    sel = st.selectbox("选择股票:", opts)
    if sel:
        code = sel.split(" | ")[0]
        name = sel.split(" | ")[1]
        st.subheader(f"📈 {name} 专业走势")
        plot_pro_chart(code, name)
    st.markdown("---")
    st.dataframe(df, use_container_width=True)

# Tab 4 回测渲染 (新功能)
def render_backtest():
    st.header("⏳ 策略时光机")
    st.info("验证：如果我过去几年坚持轮动，能赚多少钱？")
    
    c1, c2, c3 = st.columns(3)
    pool = c1.selectbox("选择资产池", ["全球宏观", "A股行业"])
    start = c2.date_input("开始日期", value=datetime(2022, 1, 1))
    end = c3.date_input("结束日期", value=datetime.today())
    
    if st.button("🚀 开始回测", type="primary"):
        run_backtest(pool, start, end)

with tab1: render_common(ASSETS_GLOBAL)
with tab2: render_common(ASSETS_CN)
with tab3: render_500()
with tab4: render_backtest()

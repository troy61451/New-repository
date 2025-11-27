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

# 初始化 Session State
if 'custom_assets' not in st.session_state:
    st.session_state.custom_assets = {}

# 默认资产池
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

# 动态合并
ASSETS_GLOBAL = {**DEFAULT_ASSETS_GLOBAL, **st.session_state.custom_assets}

# ==========================================
# 2. 辅助功能函数
# ==========================================
@st.cache_data(ttl=3600)
def get_market_temperature():
    tickers = list(ASSETS_CN.values())
    try:
        data = yf.download(tickers, period="30d", progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        bull_count = 0
        total_count = len(tickers)
        for code in tickers:
            try:
                s = data[code].dropna()
                if len(s) < 20: continue
                if s.iloc[-1] > s.rolling(20).mean().iloc[-1]: bull_count += 1
            except: pass
        return (bull_count / total_count) * 100
    except: return 0

# ==========================================
# 3. 侧边栏
# ==========================================
with st.sidebar:
    st.title("🎛️ 操盘控制台")
    st.caption(f"📅 日期: {datetime.now().strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # 温度计
    temp = get_market_temperature()
    st.subheader("🌡️ A股情绪温度")
    st.progress(temp / 100)
    if temp > 80: st.error(f"🔥 过热 ({temp:.0f}%)")
    elif temp < 20: st.info(f"🧊 冰点 ({temp:.0f}%)")
    else: st.warning(f"🌤️ 震荡 ({temp:.0f}%)")
    
    st.markdown("---")
    
    # 添加自定义资产
    with st.expander("➕ 添加自定义行情", expanded=False):
        st.caption("例如: 巴西ETF | EWZ")
        new_name = st.text_input("资产名称", placeholder="巴西ETF")
        new_code = st.text_input("资产代码", placeholder="EWZ")
        
        if st.button("确认添加"):
            if new_name and new_code:
                safe_code = new_code.strip().upper()
                st.session_state.custom_assets[new_name] = safe_code
                st.success(f"已添加: {new_name}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("请填写名称和代码")
                
    if st.session_state.custom_assets:
        st.caption("✅ 已添加:")
        for k, v in st.session_state.custom_assets.items():
            st.text(f"{k}: {v}")
        if st.button("🗑️ 清空自定义"):
            st.session_state.custom_assets = {}
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    strategy_mode = st.radio("🎯 策略模式:", ("🚀 动量轮动", "🛡️ 超跌反弹", "⚔️ 双均线金叉"))
    st.markdown("---")
    if st.button("🔄 刷新最新数据", type="primary"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 4. 核心绘图 & 数据函数
# ==========================================
def plot_pro_chart(ticker, name):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = ema12 - ema26
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.6, 0.2, 0.2], subplot_titles=(f"{name} ({ticker})", "", ""))
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K线", increasing_line_color='#fd3030', decreasing_line_color='#00f0f0'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='white', width=1), name='MA5'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='#ffd700', width=1), name='MA10'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#ff00ff', width=1), name='MA20'), row=1, col=1)
        
        vol_colors = ['#fd3030' if r['Open'] < r['Close'] else '#00f0f0' for i, r in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name='成交量', showlegend=False), row=2, col=1)
        
        macd_colors = ['#fd3030' if v >= 0 else '#00f0f0' for v in df['MACD']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD'], marker_color=macd_colors, name='MACD柱', showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='white', width=1), name='DIF'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='#ffd700', width=1), name='DEA'), row=3, col=1)

        fig.update_layout(template='plotly_dark', height=700, xaxis_rangeslider_visible=False, paper_bgcolor='#000000', plot_bgcolor='#0e0e0e', margin=dict(l=5, r=5, t=30, b=5), hovermode='x unified', legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0))
        fig.update_xaxes(rangeselector=dict(buttons=list([dict(count=1, label="1月", step="month", stepmode="backward"), dict(count=6, label="半年", step="month", stepmode="backward"), dict(step="all", label="全部")]), bgcolor="#333", activecolor="#555", font=dict(color="white")), row=1, col=1)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#222'); fig.update_xaxes(showgrid=False, rangebreaks=[dict(bounds=["sat", "mon"])])
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e: st.error(f"图表加载出错: {e}")

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
# 5. 回测引擎
# ==========================================
def run_backtest(pool_name, start_date, end_date):
    if pool_name == "全球宏观": assets = ASSETS_GLOBAL 
    else: assets = ASSETS_CN
    tickers = list(assets.values())
    
    with st.spinner(f"正在回测 {pool_name} ({len(tickers)}只)..."):
        try:
            data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)['Close']
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            data = data.replace(0, pd.NA).ffill().dropna(how='all')
            if data.empty: st.error("数据不足"); return
            
            daily_ret = data.pct_change().fillna(0)
            momentum = data.pct_change(20).shift(1)
            
            strategy_ret = []
            dates = []
            
            for date, row in daily_ret.iterrows():
                if date not in momentum.index: continue
                mom_row = momentum.loc[date]
                if mom_row.isna().all(): continue
                best_code = mom_row.idxmax()
                if pd.isna(best_code): continue
                strategy_ret.append(row[best_code])
                dates.append(date)
            
            if not strategy_ret: st.warning("区间太短"); return

            equity = [1.0]
            for r in strategy_ret: equity.append(equity[-1] * (1 + r))
            
            backtest_df = pd.DataFrame({"日期": dates, "策略净值": equity[1:]}).set_index("日期")
            total_ret = (equity[-1] - 1) * 100
            
            st.success(f"✅ 回测完成")
            st.metric("策略总收益", f"{total_ret:.2f}%")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df["策略净值"], mode='lines', name='账户净值', line=dict(color='#fd3030', width=2)))
            fig.update_layout(template='plotly_dark', title="资金曲线", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e: st.error(f"出错: {e}")

# ==========================================
# 6. 页面渲染 (🔥 新增：下拉选择框)
# ==========================================
st.title("📊 全能操盘手系统")
tab1, tab2, tab3, tab4 = st.tabs(["🌍 全球", "🇨🇳 行业", "🔥 中证500", "🛠️ 历史回测"])

def render_common(assets, tab_key):
    # 1. 获取数据
    if "双均线" in strategy_mode:
        with st.spinner("计算均线..."): df = get_ma_data(assets)
    else:
        with st.spinner("计算动量..."): df = get_momentum_data(assets)
    if df.empty: st.warning("暂无数据"); return
    
    # 2. 排序
    asc = True if "超跌" in strategy_mode else False
    df = df.sort_values("value", ascending=asc).reset_index(drop=True)
    df.index += 1 # 排名从1开始
    
    # 3. 🔥 交互升级：添加选择框 (默认选择第1名)
    # 构造选项列表: "1. 黄金ETF | 518880.SS"
    select_options = [f"{i} . {row['name']} | {row['code']}" for i, row in df.iterrows()]
    selected_option = st.selectbox("👉 选择资产查看详情:", select_options, key=f"sel_{tab_key}")
    
    # 解析用户的选择
    selected_index = select_options.index(selected_option) # 获取选中了第几个
    target_row = df.iloc[selected_index] # 提取那一行的数据
    
    # 4. 展示选中资产的数据 (不再只展示 Top 1)
    c1, c2, c3 = st.columns(3)
    if "双均线" in strategy_mode:
        if target_row['ma20'] > target_row['ma60']: 
            c1.success(f"🚀 {target_row['name']}")
            c1.caption("金叉 (持有)")
        else: 
            c1.error(f"🛑 {target_row['name']}")
            c1.caption("死叉 (观望)")
    elif "超跌" in strategy_mode: 
        c1.success(f"🛡️ {target_row['name']}")
    else:
        if target_row['value'] < 0: 
            c1.error(f"🛑 {target_row['name']}")
            c1.caption("趋势向下")
        else: 
            c1.success(f"🚀 {target_row['name']}")
            c1.caption("趋势向上")
            
    c2.metric("当前价格", f"{target_row['price']:.2f}")
    c3.metric("强度/涨幅", f"{target_row['value']:.2f}%")
    
    st.markdown("---")
    
    # 5. 画选中资产的图
    st.subheader(f"📈 {target_row['name']} 专业走势")
    plot_pro_chart(target_row['code'], target_row['name'])
    
    # 6. 表格
    st.markdown("---")
    st.subheader("📋 详细排名")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载数据 (CSV)", csv, "rank_data.csv", "text/csv", key=f"btn_{tab_key}")
    st.dataframe(df, use_container_width=True)

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
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载排名 (CSV)", csv, "csi500_rank.csv", "text/csv", key="btn_500")
    st.dataframe(df, use_container_width=True)

def render_backtest():
    st.header("⏳ 策略时光机")
    st.info("验证：使用【复权价格】(auto_adjust) 回测，精确处理分红拆股。")
    c1, c2, c3 = st.columns(3)
    pool = c1.selectbox("选择资产池", ["全球宏观", "A股行业"])
    start = c2.date_input("开始日期", value=datetime(2022, 1, 1))
    end = c3.date_input("结束日期", value=datetime.today())
    if st.button("🚀 开始回测", type="primary"):
        run_backtest(pool, start, end)

with tab1: render_common(ASSETS_GLOBAL, "global")
with tab2: render_common(ASSETS_CN, "cn")
with tab3: render_500()
with tab4: render_backtest()

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
import xml.etree.ElementTree as ET # 原生库，解析RSS XML
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from textblob import TextBlob 
from snownlp import SnowNLP 

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(layout="wide", page_title="全能操盘手系统", page_icon="📈")

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

ASSETS_GLOBAL = {**DEFAULT_ASSETS_GLOBAL, **st.session_state.custom_assets}

# ==========================================
# 2. 辅助函数
# ==========================================
@st.cache_data(ttl=3600)
def get_market_temperature():
    tickers = list(ASSETS_CN.values())
    try:
        data = yf.download(tickers, period="30d", progress=False, threads=False)['Close']
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        if isinstance(data, pd.Series): data = data.to_frame(name=tickers[0])
        bull_count = 0
        total_count = 0
        for code in tickers:
            try:
                if code not in data.columns: continue
                s = data[code].dropna()
                if len(s) < 20: continue
                if s.iloc[-1] > s.rolling(20).mean().iloc[-1]: bull_count += 1
                total_count += 1
            except: pass
        if total_count == 0: return 50
        return (bull_count / total_count) * 100
    except: return 50

# 🔥 新增：Google News RSS 解析引擎
def get_google_news(query, lang='zh-CN'):
    # 构造 RSS 链接
    rss_url = f"https://news.google.com/rss/search?q={query}&hl={lang}&gl=CN&ceid=CN:{lang}"
    
    try:
        response = requests.get(rss_url, timeout=5)
        root = ET.fromstring(response.content)
        
        news_items = []
        total_score = 0
        count = 0
        
        # 解析 XML (取前 10 条)
        for item in root.findall('./channel/item')[:10]:
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            
            # 情感分析
            try:
                # 判断是否包含中文
                if any(u'\u4e00' <= c <= u'\u9fff' for c in title):
                    s = SnowNLP(title)
                    score = (s.sentiments - 0.5) * 2 # 归一化到 -1~1
                else:
                    blob = TextBlob(title)
                    score = blob.sentiment.polarity
            except:
                score = 0
            
            total_score += score
            count += 1
            
            # 格式化时间 (简化显示)
            try:
                dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                time_str = dt.strftime('%m-%d %H:%M')
            except:
                time_str = pub_date

            news_items.append({
                "title": title,
                "link": link,
                "time": time_str,
                "score": score,
                "source": "Google News"
            })
            
        avg_score = total_score / count if count > 0 else 0
        return news_items, avg_score
    except Exception as e:
        print(f"Google RSS Error: {e}")
        return [], 0

# 混合新闻引擎 (Yahoo + Google)
def get_news_and_sentiment(ticker, name):
    is_cn_stock = ticker.endswith('.SS') or ticker.endswith('.SZ')
    
    # 1. 尝试获取新闻
    if is_cn_stock:
        # A股：优先用 Google News 搜中文名 (比如 "半导体ETF")
        # 去掉名称里的括号备注，提高搜索准确度
        search_term = name.split('(')[0] 
        news_items, avg = get_google_news(search_term, 'zh-CN')
        source_type = "Google (A股)"
    else:
        # 美股：优先 Yahoo，如果失败则 Google 兜底
        try:
            # 尝试 Yahoo
            news_list = yf.Ticker(ticker).news
            if news_list:
                news_items = []
                total = 0
                for item in news_list:
                    title = item.get('title', '')
                    blob = TextBlob(title)
                    score = blob.sentiment.polarity
                    total += score
                    pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                    news_items.append({
                        "title": title,
                        "link": item.get('link', ''),
                        "time": pub_time.strftime('%Y-%m-%d %H:%M'),
                        "score": score,
                        "source": item.get('publisher', 'Yahoo')
                    })
                avg = total / len(news_items)
                source_type = "Yahoo Finance"
            else:
                raise Exception("Yahoo empty")
        except:
            # Yahoo 失败，用 Google 搜代码 (如 "EWZ ETF")
            news_items, avg = get_google_news(f"{ticker} stock", 'en-US')
            source_type = "Google (Global)"

    # 2. 生成跳转链接 (A股专用)
    links = {}
    if is_cn_stock:
        pure_code = ticker.split('.')[0]
        market = "SH" if ticker.endswith('.SS') else "SZ"
        links = {
            "xueqiu": f"https://xueqiu.com/S/{market}{pure_code}",
            "eastmoney": f"http://quote.eastmoney.com/{market.lower()}{pure_code}.html"
        }
        
    return news_items, avg, source_type, links

# ==========================================
# 3. 侧边栏
# ==========================================
with st.sidebar:
    st.title("🎛️ 操盘控制台")
    st.caption(f"📅 {datetime.now().strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    temp = get_market_temperature()
    st.subheader("🌡️ 市场温度")
    st.progress(temp / 100)
    if temp > 80: st.error(f"🔥 过热 ({temp:.0f}%)")
    elif temp < 20: st.info(f"🧊 冰点 ({temp:.0f}%)")
    else: st.warning(f"🌤️ 震荡 ({temp:.0f}%)")
    
    st.markdown("---")
    
    with st.expander("➕ 添加自定义行情", expanded=False):
        new_name = st.text_input("资产名称", placeholder="巴西ETF")
        new_code = st.text_input("资产代码", placeholder="EWZ")
        if st.button("确认添加"):
            if new_name and new_code:
                st.session_state.custom_assets[new_name] = new_code.strip().upper()
                st.cache_data.clear()
                st.rerun()
                
    if st.session_state.custom_assets:
        with st.expander("🗑️ 管理已添加资产"):
            assets_list = list(st.session_state.custom_assets.keys())
            to_delete = st.multiselect("选择删除:", assets_list)
            if st.button("❌ 删除选中"):
                for name in to_delete: del st.session_state.custom_assets[name]
                st.cache_data.clear()
                st.rerun()

    st.markdown("---")
    strategy_mode = st.radio("🎯 策略模式:", ("🚀 动量轮动", "🛡️ 超跌反弹", "⚔️ 双均线金叉", "🌊 RSI震荡", "🛠️ 自定义均线"))
    
    if "自定义" in strategy_mode:
        c1, c2 = st.columns(2)
        with c1: custom_short = st.number_input("短期", 1, 100, 5)
        with c2: custom_long = st.number_input("长期", 2, 300, 30)

    st.markdown("---")
    if st.button("🔄 刷新数据 (修复)", type="primary"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 4. 数据计算引擎
# ==========================================
def plot_pro_chart(ticker, name):
    try:
        df = yf.download(ticker, period="2y", progress=False, threads=False)
        if df.empty: st.warning("暂无K线数据"); return
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        
        if "自定义" in strategy_mode:
            df[f'MA{custom_short}'] = df['Close'].rolling(custom_short).mean()
            df[f'MA{custom_long}'] = df['Close'].rolling(custom_long).mean()

        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = ema12 - ema26
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.6, 0.2, 0.2], subplot_titles=(f"{name} ({ticker})", "", ""))
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K线", increasing_line_color='#fd3030', decreasing_line_color='#00f0f0'), row=1, col=1)
        
        if "自定义" in strategy_mode:
            fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{custom_short}'], line=dict(color='yellow', width=1.5), name=f'MA{custom_short}'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{custom_long}'], line=dict(color='cyan', width=1.5), name=f'MA{custom_long}'), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='white', width=1), name='MA5'), row=1, col=1)
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
    except: st.error("K线图加载失败，请刷新")

@st.cache_data(ttl=3600) 
def fetch_and_calculate(asset_dict, mode, **kwargs):
    tickers = list(asset_dict.values())
    try:
        data = yf.download(tickers, period="2y", progress=False, threads=False)
        if data.empty: return pd.DataFrame()
        if 'Close' in data: df_close = data['Close']
        else: df_close = data
        if isinstance(df_close, pd.Series): df_close = df_close.to_frame(name=tickers[0])

        results = []
        for name, code in asset_dict.items():
            try:
                if code not in df_close.columns: continue
                s = df_close[code].dropna()
                required_len = kwargs.get('long_w', 61)
                if len(s) < required_len: continue
                curr_price = s.iloc[-1]
                
                if mode == "MOM":
                    val = (curr_price - s.iloc[-21]) / s.iloc[-21] * 100
                    results.append({"name":name, "code":code, "price":curr_price, "value":val})
                elif mode == "MA":
                    ma20 = s.rolling(20).mean().iloc[-1]; ma60 = s.rolling(60).mean().iloc[-1]
                    gap = (ma20 - ma60) / ma60 * 100
                    results.append({"name":name, "code":code, "price":curr_price, "ma20":ma20, "ma60":ma60, "value":gap})
                elif mode == "RSI":
                    delta = s.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rs = gain / loss; rsi = 100 - (100 / (1 + rs))
                    results.append({"name":name, "code":code, "price":curr_price, "value":rsi.iloc[-1]})
                elif mode == "CUSTOM":
                    sw, lw = kwargs['short_w'], kwargs['long_w']
                    ms = s.rolling(sw).mean().iloc[-1]; ml = s.rolling(lw).mean().iloc[-1]
                    gap = (ms - ml) / ml * 100
                    results.append({"name":name, "code":code, "price":curr_price, "short":ms, "long":ml, "value":gap})
            except: pass
        return pd.DataFrame(results)
    except: return pd.DataFrame()

@st.cache_data
def load_csi500_rank():
    try: return pd.read_csv("csi500_rank.csv")
    except: return pd.DataFrame()

def run_backtest(pool_name, start_date, end_date):
    if pool_name == "全球宏观": assets = ASSETS_GLOBAL 
    else: assets = ASSETS_CN
    tickers = list(assets.values())
    with st.spinner(f"正在回测..."):
        try:
            data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False, threads=False)['Close']
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            if isinstance(data, pd.Series): data = data.to_frame(name=tickers[0])
            data = data.replace(0, pd.NA).ffill().dropna(how='all')
            if data.empty: st.error("无数据"); return
            daily_ret = data.pct_change().fillna(0)
            momentum = data.pct_change(20).shift(1)
            strategy_ret = []; dates = []
            for date, row in daily_ret.iterrows():
                if date not in momentum.index: continue
                mom_row = momentum.loc[date]
                if mom_row.isna().all(): continue
                best_code = mom_row.idxmax()
                if pd.isna(best_code): continue
                if best_code in row: strategy_ret.append(row[best_code]); dates.append(date)
            if not strategy_ret: st.warning("区间太短"); return
            equity = [1.0]
            for r in strategy_ret: equity.append(equity[-1] * (1 + r))
            backtest_df = pd.DataFrame({"日期": dates, "策略净值": equity[1:]}).set_index("日期")
            st.success("✅ 回测完成")
            st.metric("总收益", f"{(equity[-1]-1)*100:.2f}%")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df["策略净值"], mode='lines', line=dict(color='#fd3030')))
            fig.update_layout(template='plotly_dark', title="资金曲线", height=450)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e: st.error(f"出错: {e}")

# ==========================================
# 5. 渲染页面
# ==========================================
st.title("📊 全能操盘手系统")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🌍 全球", "🇨🇳 行业", "🔥 中证500", "🛠️ 历史回测", "📰 舆情雷达"])

def render_common(assets, tab_key):
    if "自定义" in strategy_mode:
        with st.spinner("计算中..."): df = fetch_and_calculate(assets, "CUSTOM", short_w=custom_short, long_w=custom_long); asc=False
    elif "双均线" in strategy_mode:
        with st.spinner("计算均线..."): df = fetch_and_calculate(assets, "MA", long_w=60); asc=False
    elif "RSI" in strategy_mode:
        with st.spinner("计算RSI..."): df = fetch_and_calculate(assets, "RSI"); asc=True
    else:
        with st.spinner("计算动量..."): df = fetch_and_calculate(assets, "MOM"); asc=True if "超跌" in strategy_mode else False

    if df.empty: st.warning("暂无数据，请重试"); return
    df = df.sort_values("value", ascending=asc).reset_index(drop=True)
    df.index += 1
    
    select_options = [f"{i} . {row['name']} | {row['code']}" for i, row in df.iterrows()]
    selected_option = st.selectbox("👉 选择资产查看详情:", select_options, key=f"sel_{tab_key}")
    selected_index = select_options.index(selected_option)
    target_row = df.iloc[selected_index]
    
    c1, c2, c3 = st.columns(3)
    c1.metric(target_row['name'], target_row['code'])
    c2.metric("当前价", f"{target_row['price']:.2f}")
    c3.metric("指标值", f"{target_row['value']:.2f}")
    st.markdown("---")
    st.subheader(f"📈 {target_row['name']} 走势")
    plot_pro_chart(target_row['code'], target_row['name'])
    st.markdown("---")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载数据", csv, "data.csv", "text/csv", key=f"btn_{tab_key}")
    st.dataframe(df, use_container_width=True)

def render_500():
    df = load_csi500_rank()
    if df.empty: st.warning("后台生成中..."); return
    top = df.iloc[0]
    st.success(f"🚀 冠军: **{top['名称']}** ({top['代码']})")
    c1,c2,c3 = st.columns(3)
    c1.metric("涨幅", f"{top['20日涨幅']}%"); c2.metric("价格", f"{top['当前价']}"); c3.metric("来源", "后台")
    st.markdown("---")
    opts = [f"{r['代码']} | {r['名称']}" for i,r in df.head(20).iterrows()]
    sel = st.selectbox("选择股票:", opts)
    if sel:
        code = sel.split(" | ")[0]
        name = sel.split(" | ")[1]
        plot_pro_chart(code, name)
    st.markdown("---")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载排名", csv, "csi500.csv", "text/csv", key="btn_500")
    st.dataframe(df, use_container_width=True)

# 🔥 修复版舆情雷达 (混合源 + Google 兜底)
def render_news():
    st.header("📰 双语舆情雷达")
    st.info("💡 混合模式：Google News (聚合全网) + 雪球/东财直达")
    
    all_options = {**ASSETS_GLOBAL, **ASSETS_CN}
    asset_list = [f"{k} | {v}" for k,v in all_options.items()]
    selected_asset = st.selectbox("🔍 选择资产:", asset_list)
    
    if selected_asset:
        name = selected_asset.split(" | ")[0]
        code = selected_asset.split(" | ")[1]
        
        if st.button("📡 扫描舆情", type="primary"):
            with st.spinner("正在聚合全网新闻..."):
                news_items, avg, source_type, links = get_news_and_sentiment(code, name)
                
                if links:
                    st.success(f"✅ {name} 社区讨论区已定位")
                    col1, col2 = st.columns(2)
                    with col1: st.link_button("❄️ 跳转雪球 (推荐)", links['xueqiu'])
                    with col2: st.link_button("🇨🇳 跳转东方财富", links['eastmoney'])
                    st.markdown("---")

                if not news_items:
                    st.warning(f"⚠️ {source_type} 暂未收录最新报道")
                else:
                    st.caption(f"数据来源: {source_type}")
                    c1, c2 = st.columns(2)
                    c1.metric("新闻条数", len(news_items))
                    emoji = "😐"
                    if avg > 0.1: emoji = "😄 (利好)"
                    elif avg < -0.1: emoji = "😨 (利空)"
                    c2.metric("情感得分", f"{avg:.2f}", emoji)
                    
                    st.markdown("---")
                    for n in news_items:
                        color = "gray"
                        if n['score'] > 0.1: color = "green"
                        if n['score'] < -0.1: color = "red"
                        with st.expander(f":{color}[{n['title']}]"):
                            st.write(f"时间: {n['time']} | 来源: {n['source']}")
                            st.write(f"情感: {n['score']:.2f}")
                            st.markdown(f"[阅读原文]({n['link']})")

with tab1: render_common(ASSETS_GLOBAL, "global")
with tab2: render_common(ASSETS_CN, "cn")
with tab3: render_500()
with tab4: render_backtest()
with tab5: render_news()

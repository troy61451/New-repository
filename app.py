import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import json
import os
import hashlib
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from textblob import TextBlob 
from snownlp import SnowNLP 

# ==========================================
# 0. 用户认证系统 (🔥 新增核心模块)
# ==========================================
USER_DB_FILE = "users.json"

class UserManager:
    def __init__(self):
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        if not os.path.exists(USER_DB_FILE):
            with open(USER_DB_FILE, 'w') as f:
                json.dump({}, f)

    def _load_users(self):
        try:
            with open(USER_DB_FILE, 'r') as f:
                return json.load(f)
        except: return {}

    def _save_users(self, users):
        with open(USER_DB_FILE, 'w') as f:
            json.dump(users, f)

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username, password):
        users = self._load_users()
        if username in users:
            return False, "用户已存在"
        users[username] = self._hash_password(password)
        self._save_users(users)
        return True, "注册成功，请登录"

    def login(self, username, password):
        users = self._load_users()
        if username not in users:
            return False
        if users[username] == self._hash_password(password):
            return True
        return False

# ==========================================
# 1. 基础配置 & 状态管理
# ==========================================
st.set_page_config(layout="wide", page_title="全能操盘手系统", page_icon="📈")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# ==========================================
# 2. 登录/注册 页面逻辑
# ==========================================
def render_login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 全能操盘手 - 安全入口</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册新用户"])
    
    manager = UserManager()

    with tab1: # 登录页
        with st.form("login_form"):
            user = st.text_input("用户名")
            pwd = st.text_input("密码", type="password")
            submit = st.form_submit_button("立即登录", type="primary")
            
            if submit:
                if manager.login(user, pwd):
                    st.session_state.logged_in = True
                    st.session_state.current_user = user
                    st.success("登录成功！跳转中...")
                    st.rerun()
                else:
                    st.error("用户名或密码错误")

    with tab2: # 注册页
        with st.form("register_form"):
            new_user = st.text_input("设置用户名")
            new_pwd = st.text_input("设置密码", type="password")
            confirm_pwd = st.text_input("确认密码", type="password")
            submit_reg = st.form_submit_button("注册")
            
            if submit_reg:
                if new_pwd != confirm_pwd:
                    st.error("两次输入的密码不一致")
                elif not new_user or not new_pwd:
                    st.error("用户名和密码不能为空")
                else:
                    success, msg = manager.register(new_user, new_pwd)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

# ==========================================
# 3. 核心功能函数 (保留之前的逻辑)
# ==========================================
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = {
        "贵州茅台": "600519.SS",
        "腾讯控股": "0700.HK",
        "英伟达": "NVDA"
    }
if 'custom_assets' not in st.session_state:
    st.session_state.custom_assets = {}

# 资产池定义
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

def smart_format_code(raw_code):
    code = raw_code.strip().upper()
    if "." in code: return code 
    if code.isdigit():
        if len(code) == 6: 
            if code.startswith(('60', '68', '51', '58')): return f"{code}.SS"
            else: return f"{code}.SZ"
        elif len(code) <= 5: return f"{int(code):04d}.HK"
    return code 

def fetch_stock_name(symbol):
    try:
        if symbol.endswith(".SS") or symbol.endswith(".SZ"):
            market = "sh" if symbol.endswith(".SS") else "sz"
            code = symbol.replace(".SS", "").replace(".SZ", "")
            r = requests.get(f"http://hq.sinajs.cn/list={market}{code}", timeout=2)
            if "=\"" in r.text:
                content = r.text.split("=\"")[1]
                if len(content) > 1: return content.split(",")[0]
        if symbol.endswith(".HK"):
            code = symbol.replace(".HK", "")
            r = requests.get(f"http://hq.sinajs.cn/list=hk{code}", timeout=2)
            if "=\"" in r.text:
                content = r.text.split("=\"")[1]
                if len(content) > 1: return content.split(",")[1]
        t = yf.Ticker(symbol)
        return t.info.get('shortName') or t.info.get('longName') or symbol
    except: return symbol

@st.cache_data(ttl=3600)
def get_market_temperature():
    tickers = list(ASSETS_CN.values())
    try:
        data = yf.download(tickers, period="30d", progress=False, threads=False)['Close']
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        if isinstance(data, pd.Series): data = data.to_frame(name=tickers[0])
        bull_count = 0; total_count = 0
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

def get_google_news(query, lang='zh-CN'):
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl=CN&ceid=CN:{lang}"
    try:
        response = requests.get(rss_url, timeout=5)
        root = ET.fromstring(response.content)
        news_items = []; total_score = 0; count = 0
        for item in root.findall('./channel/item')[:10]:
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            try:
                if any(u'\u4e00' <= c <= u'\u9fff' for c in title):
                    s = SnowNLP(title); score = (s.sentiments - 0.5) * 2 
                else:
                    blob = TextBlob(title); score = blob.sentiment.polarity
            except: score = 0
            total_score += score; count += 1
            try: dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z'); time_str = dt.strftime('%m-%d %H:%M')
            except: time_str = pub_date
            news_items.append({"title": title, "link": link, "time": time_str, "score": score, "source": "Google News"})
        avg_score = total_score / count if count > 0 else 0
        return news_items, avg_score
    except: return [], 0

def get_news_and_sentiment(ticker, name):
    is_cn_stock = ticker.endswith('.SS') or ticker.endswith('.SZ')
    clean_name = name.split('(')[0].replace("ETF", "")
    if is_cn_stock:
        news_items, avg = get_google_news(clean_name, 'zh-CN'); source_type = "Google (A股)"
    else:
        try:
            news_list = yf.Ticker(ticker).news
            if news_list:
                news_items = []; total = 0
                for item in news_list:
                    title = item.get('title', ''); blob = TextBlob(title); score = blob.sentiment.polarity; total += score
                    pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                    news_items.append({"title": title, "link": item.get('link', ''), "time": pub_time.strftime('%Y-%m-%d %H:%M'), "score": score, "source": item.get('publisher', 'Yahoo')})
                avg = total / len(news_items); source_type = "Yahoo Finance"
            else: raise Exception("Yahoo empty")
        except:
            news_items, avg = get_google_news(f"{ticker} stock", 'en-US'); source_type = "Google (Global)"
    links = {}
    if is_cn_stock:
        pure_code = ticker.split('.')[0]
        em_market = "SH" if ticker.endswith('.SS') else "SZ"
        encoded_name = urllib.parse.quote(clean_name)
        links = {
            "xueqiu": f"https://xueqiu.com/S/{em_market}{pure_code}",
            "eastmoney": f"http://quote.eastmoney.com/{em_market.lower()}{pure_code}.html",
            "cls": f"https://www.cls.cn/searchPage?keyword={encoded_name}",
            "10jqka": f"http://www.iwencai.com/unifiedwap/result?w={pure_code}"
        }
    return news_items, avg, source_type, links

def plot_pro_chart(ticker, name, strategy_mode, custom_short=5, custom_long=20):
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
        
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{ticker}_{datetime.now().microsecond}")
    except: st.error("K线图加载失败，请刷新")

@st.cache_data(ttl=3600) 
def fetch_and_calculate(asset_dict, strategy_mode, custom_short, custom_long):
    tickers = list(asset_dict.values())
    try:
        data = yf.download(tickers, period="2y", progress=False, threads=False)
        if data.empty: return pd.DataFrame()
        if 'Close' in data: df_close = data['Close']
        else: df_close = data
        if 'Volume' in data: df_vol = data['Volume']
        else: df_vol = pd.DataFrame()

        if isinstance(df_close, pd.Series): df_close = df_close.to_frame(name=tickers[0])
        if isinstance(df_vol, pd.Series): df_vol = df_vol.to_frame(name=tickers[0])

        results = []
        for name, code in asset_dict.items():
            try:
                if code not in df_close.columns: continue
                s = df_close[code].dropna()
                required_len = max(61, custom_long + 1)
                if len(s) < required_len: continue
                curr_price = s.iloc[-1]; prev_price = s.iloc[-2]
                daily_pct = (curr_price - prev_price) / prev_price
                curr_vol = 0
                if not df_vol.empty and code in df_vol.columns: curr_vol = df_vol[code].iloc[-1]

                val_mom = (curr_price - s.iloc[-21]) / s.iloc[-21] * 100
                ma20 = s.rolling(20).mean().iloc[-1]; ma60 = s.rolling(60).mean().iloc[-1]
                val_ma = (ma20 - ma60) / ma60 * 100
                delta = s.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss; val_rsi = 100 - (100 / (1 + rs)).iloc[-1]
                ms = s.rolling(custom_short).mean().iloc[-1]; ml = s.rolling(custom_long).mean().iloc[-1]
                val_custom = (ms - ml) / ml * 100

                sort_val = val_mom 
                if "RSI" in strategy_mode: sort_val = val_rsi
                elif "双均线" in strategy_mode: sort_val = val_ma
                elif "自定义" in strategy_mode: sort_val = val_custom

                results.append({
                    "name": name, "code": code, "price": curr_price, "daily_pct": daily_pct, "volume": curr_vol,
                    "val_mom": val_mom, "val_ma": val_ma, "val_rsi": val_rsi, "val_custom": val_custom,
                    "value": sort_val 
                })
            except: pass
        return pd.DataFrame(results)
    except: return pd.DataFrame()

@st.cache_data
def load_csi500_rank():
    try: return pd.read_csv("csi500_rank.csv")
    except: return pd.DataFrame()

def run_backtest_logic(pool_name, start_date, end_date):
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

def render_clickable_list(df, tab_key, strategy_mode):
    state_key = f"selected_code_{tab_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = df.iloc[0]['code'] if not df.empty else None

    cols = st.columns([1.5, 1.2, 1, 1.2, 1.2, 1.5])
    headers = ["📌 名称", "代码", "现价", "今日涨跌", "成交量", "📊 多维策略"]
    for col, h in zip(cols, headers): col.markdown(f"**{h}**")
    st.markdown("---")

    target_row = None
    for i, row in df.iterrows():
        c = st.columns([1.5, 1.2, 1, 1.2, 1.2, 1.5])
        btn_type = "primary" if st.session_state[state_key] == row['code'] else "secondary"
        if st.session_state[state_key] == row['code']: target_row = row 
            
        if c[0].button(row['name'], key=f"btn_{tab_key}_{row['code']}", type=btn_type, use_container_width=True):
            st.session_state[state_key] = row['code']
            st.rerun() 
            
        c[1].caption(row['code'])
        c[2].write(f"{row['price']:.2f}")
        pct = row['daily_pct'] * 100
        color = "red" if pct >= 0 else "green"
        c[3].markdown(f":{color}[{pct:.2f}%]")
        
        vol = row['volume']
        if vol > 100000000: vol_str = f"{vol/100000000:.2f}亿"
        elif vol > 10000: vol_str = f"{vol/10000:.0f}万"
        else: vol_str = str(vol)
        c[4].caption(vol_str)
        
        options = [f"🚀 动量: {row['val_mom']:.2f}%", f"🌊 RSI: {row['val_rsi']:.2f}", f"⚔️ 双均线: {row['val_ma']:.2f}%", f"🛠️ 自定义: {row['val_custom']:.2f}%"]
        idx = 0
        if "RSI" in strategy_mode: idx = 1
        elif "双均线" in strategy_mode: idx = 2
        elif "自定义" in strategy_mode: idx = 3
        c[5].selectbox("策略", options, index=idx, key=f"sel_sig_{tab_key}_{row['code']}", label_visibility="collapsed")
    
    st.markdown("---")
    return target_row

# ==========================================
# 6. 主程序应用逻辑 (封装在 main_app 中)
# ==========================================
def main_app():
    # 侧边栏逻辑
    with st.sidebar:
        st.title("🎛️ 操盘控制台")
        st.caption(f"当前用户: {st.session_state.current_user}")
        
        if st.button("🚪 退出登录"):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.rerun()
            
        st.markdown("---")
        temp = get_market_temperature()
        st.subheader("🌡️ 市场温度")
        st.progress(temp / 100)
        if temp > 80: st.error(f"🔥 过热 ({temp:.0f}%)")
        elif temp < 20: st.info(f"🧊 冰点 ({temp:.0f}%)")
        else: st.warning(f"🌤️ 震荡 ({temp:.0f}%)")
        st.markdown("---")
        
        strategy_mode = st.radio("🎯 策略模式:", ("🚀 动量轮动", "🛡️ 超跌反弹", "⚔️ 双均线金叉", "🌊 RSI震荡", "🛠️ 自定义均线"))
        
        custom_short = 5; custom_long = 20
        if "自定义" in strategy_mode:
            c1, c2 = st.columns(2)
            with c1: custom_short = st.number_input("短期", 1, 100, 5)
            with c2: custom_long = st.number_input("长期", 2, 300, 30)

        st.markdown("---")
        if st.button("🔄 刷新数据", type="primary"):
            st.cache_data.clear()
            st.rerun()

    # 主界面逻辑
    st.title("📊 全能操盘手系统")
    
    # 渲染函数定义
    def render_common_wrapper(assets, tab_key):
        with st.spinner("计算中..."): df = fetch_and_calculate(assets, strategy_mode, custom_short=custom_short, custom_long=custom_long); asc=True if ("RSI" in strategy_mode) or ("超跌" in strategy_mode) else False
        if df.empty: st.warning("暂无数据"); return
        df = df.sort_values("value", ascending=asc).reset_index(drop=True)
        target_row = render_clickable_list(df, tab_key, strategy_mode)
        if target_row is not None:
            st.subheader(f"📈 {target_row['name']} ({target_row['code']}) 走势")
            plot_pro_chart(target_row['code'], target_row['name'], strategy_mode, custom_short, custom_long)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下载列表", csv, "data.csv", "text/csv", key=f"dl_{tab_key}")

    # Tabs
    main_tabs = st.tabs(["⚔️ 策略看板", "📰 舆情雷达", "⭐ 我的自选"])

    with main_tabs[0]:
        sub_tabs = st.tabs(["🌍 全球核心", "🇨🇳 行业龙头", "🔥 中证500", "🛠️ 历史回测"])
        with sub_tabs[0]: render_common_wrapper(ASSETS_GLOBAL, "global")
        with sub_tabs[1]: render_common_wrapper(ASSETS_CN, "cn")
        with sub_tabs[2]: render_500(strategy_mode, custom_short, custom_long)
        with sub_tabs[3]: render_backtest()

    with main_tabs[1]:
        render_news()

    with main_tabs[2]:
        render_watchlist_manager(strategy_mode, custom_short, custom_long)

# ==========================================
# 7. 程序入口 (控制登录状态)
# ==========================================
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        render_login_page()

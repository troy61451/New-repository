import akshare as ak
import yfinance as yf
import pandas as pd
import requests
import os

# 从环境变量获取 Token
TOKEN = os.environ.get("PUSH_TOKEN")

def get_csi500_data():
    print("正在获取中证500成分股名单...")
    try:
        # 1. 获取名单和名称
        df = ak.index_stock_cons_weight_csindex(symbol="000905")
        # df 里面有 ['成分券代码', '成分券名称']
        
        # 2. 创建一个字典映射: {'300390.SZ': '通达动力'}
        stock_map = {}
        for _, row in df.iterrows():
            raw_code = row['成分券代码']
            name = row['成分券名称']
            
            # 转换成 Yahoo 格式
            if raw_code.startswith('6'):
                full_code = raw_code + ".SS"
            else:
                full_code = raw_code + ".SZ"
            
            stock_map[full_code] = name
            
        print(f"成功获取 {len(stock_map)} 只股票信息。")
        return stock_map
    except Exception as e:
        print(f"获取名单失败: {e}")
        return {}

def calculate_momentum():
    # 获取 {代码: 名称} 的字典
    stock_map = get_csi500_data()
    stocks = list(stock_map.keys())
    
    if not stocks: return None, "名单为空"

    print("开始批量下载行情数据...")
    results = []
    
    try:
        # 批量下载
        data = yf.download(stocks, period="1mo", progress=False)
        
        if 'Close' in data: df_close = data['Close']
        else: df_close = data

        print("数据下载完成，开始计算...")
        
        for code in stocks:
            try:
                if code not in df_close.columns: continue
                
                series = df_close[code].dropna()
                if len(series) < 21: continue
                
                curr = series.iloc[-1]
                prev = series.iloc[-21]
                mom = (curr - prev) / prev * 100
                
                results.append({
                    "代码": code,
                    "名称": stock_map.get(code, "未知"), # 🔥 这里加上了名称
                    "当前价": round(curr, 2),
                    "20日涨幅": round(mom, 2)
                })
            except: pass
                
    except Exception as e:
        print(f"计算过程出错: {e}")
        return None, str(e)

    df_res = pd.DataFrame(results)
    if df_res.empty: return None, "无数据"
    
    # 排序取前 50
    df_top = df_res.sort_values(by="20日涨幅", ascending=False).head(50)
    
    # 把“名称”列放到“代码”后面，好看一点
    cols = ['代码', '名称', '当前价', '20日涨幅']
    df_top = df_top[cols]
    
    # 保存 CSV
    df_top.to_csv("csi500_rank.csv", index=False)
    print("✅ 排名已保存")
    
    # 微信推送内容 (带名称)
    top_stock = df_top.iloc[0]
    title = f"【量化】今日龙一: {top_stock['名称']}"
    body = f"🚀 **冠军**: {top_stock['名称']} ({top_stock['代码']})\n📈 **涨幅**: {top_stock['20日涨幅']}%\n💰 **价格**: {top_stock['当前价']}\n\n"
    body += "Top 5 排名:\n"
    for i in range(5):
        row = df_top.iloc[i]
        body += f"{i+1}. {row['名称']}: {row['20日涨幅']}%\n"
        
    return title, body

def send_wechat(title, content):
    if not TOKEN: return
    requests.post("http://www.pushplus.plus/send", json={
        "token": TOKEN, "title": title, "content": content, "template": "markdown"
    })

if __name__ == "__main__":
    t, c = calculate_momentum()
    if t: send_wechat(t, c)

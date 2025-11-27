import akshare as ak
import yfinance as yf
import pandas as pd
import requests
import os
import time

# 从环境变量获取 Token
TOKEN = os.environ.get("PUSH_TOKEN")

def get_csi500_list():
    print("正在获取中证500成分股名单...")
    try:
        # 获取中证500 (000905) 的成分股
        df = ak.index_stock_cons_weight_csindex(symbol="000905")
        stock_list = []
        for code in df['成分券代码']:
            # 转换为 Yahoo 格式: 6开头.SS, 其他.SZ
            if code.startswith('6'):
                stock_list.append(code + ".SS")
            else:
                stock_list.append(code + ".SZ")
        print(f"成功获取 {len(stock_list)} 只股票。")
        return stock_list
    except Exception as e:
        print(f"获取名单失败: {e}")
        return []

def calculate_momentum():
    stocks = get_csi500_list()
    if not stocks: return None, "名单为空"

    print("开始批量下载行情数据 (这可能需要几十秒)...")
    results = []
    
    # 批量下载，一次性下载所有股票最近1个月的数据
    # yfinance 会自动处理多线程
    try:
        data = yf.download(stocks, period="1mo", progress=False)
        
        # 处理数据结构 (兼容不同版本的 yfinance)
        if 'Close' in data:
            df_close = data['Close']
        else:
            df_close = data

        print("数据下载完成，开始计算排名...")
        
        for code in stocks:
            try:
                # 提取单只股票
                if code not in df_close.columns: continue
                
                series = df_close[code].dropna()
                if len(series) < 21: continue
                
                curr = series.iloc[-1]     # 最新价
                prev = series.iloc[-21]    # 20天前价格
                
                # 核心指标：20日涨幅
                mom = (curr - prev) / prev * 100
                
                # 增加辅助指标：RSI 或 均线乖离 (这里先只存涨幅，以后可以加)
                
                results.append({
                    "代码": code,
                    "当前价": round(curr, 2),
                    "20日涨幅": round(mom, 2)
                })
            except:
                pass
                
    except Exception as e:
        print(f"计算过程出错: {e}")
        return None, str(e)

    # 生成结果
    df_res = pd.DataFrame(results)
    if df_res.empty:
        return None, "没有计算出有效数据"
    
    # 按涨幅排序，取前 50 名 (这就够了，App不用展示500个)
    df_top = df_res.sort_values(by="20日涨幅", ascending=False).head(50)
    
    # ⚠️ 保存到本地 CSV 文件
    df_top.to_csv("csi500_rank.csv", index=False)
    print("✅ 排名已保存为 csi500_rank.csv")
    
    # 准备微信推送文案
    top_stock = df_top.iloc[0]
    title = f"【中证500】今日龙一: {top_stock['代码']}"
    body = f"🚀 **冠军**: {top_stock['代码']}\n📈 **涨幅**: {top_stock['20日涨幅']}%\n💰 **价格**: {top_stock['当前价']}\n\n"
    body += "Top 5 排名:\n"
    for i in range(5):
        row = df_top.iloc[i]
        body += f"{i+1}. {row['代码']}: {row['20日涨幅']}%\n"
        
    return title, body

def send_wechat(title, content):
    if not TOKEN:
        print("无 Token，跳过发送")
        return
    try:
        requests.post("http://www.pushplus.plus/send", json={
            "token": TOKEN, "title": title, "content": content, "template": "markdown"
        })
        print("微信推送成功")
    except:
        print("推送失败")

if __name__ == "__main__":
    t, c = calculate_momentum()
    if t:
        send_wechat(t, c)

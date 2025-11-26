import yfinance as yf
import requests
import os

# =================配置区=================
# 这里填你刚才复制的 PushPlus Token
# 但为了安全，我们最好从环境变量读取（后面教你设），或者你现在直接填在这里也行
# 格式： TOKEN = "你的tokenxxxxxx"
TOKEN = os.environ.get("PUSH_TOKEN") 

# A股核心行业池 (和App保持一致)
ASSETS = {
    "半导体": "512480.SS", "芯片": "159995.SZ",
    "光伏": "515790.SS",   "新能车": "515030.SS",
    "军工": "512660.SS",   "证券": "512880.SS",
    "白酒": "512690.SS",   "医药": "512010.SS",
    "纳指": "513100.SS",   "黄金": "518880.SS"
}

def get_signal():
    print("开始分析...")
    best_name = "空仓"
    best_mom = -999
    msg = ""

    # 下载数据
    tickers = list(ASSETS.values())
    data = yf.download(tickers, period="30d", progress=False)['Close']
    
    ranking = []

    for name, code in ASSETS.items():
        try:
            series = data[code].dropna()
            if len(series) < 21: continue
            
            curr = series.iloc[-1]
            prev = series.iloc[-21]
            mom = (curr - prev) / prev * 100
            
            ranking.append((name, mom))
        except:
            pass
    
    # 排序
    ranking.sort(key=lambda x: x[1], reverse=True)
    
    if not ranking:
        return "数据获取失败", "请检查代码"

    top_name, top_mom = ranking[0]
    
    # 构建消息内容
    title = f"【量化日报】今日建议: {top_name}"
    
    if top_mom < 0:
        title = "【量化日报】警告: 建议空仓"
        body = f"市场最强板块 {top_name} 跌幅 {top_mom:.2f}%，全线下跌，建议持有现金。"
    else:
        body = f"🚀 **今日冠军**: {top_name}\n📈 **20日涨幅**: {top_mom:.2f}%\n\n📋 **前三名**:\n"
        for i in range(min(3, len(ranking))):
            n, m = ranking[i]
            body += f"{i+1}. {n}: {m:.2f}%\n"
            
    return title, body

def send_wechat(title, content):
    if not TOKEN:
        print("没有设置 Token，无法发送")
        return
    
    url = "http://www.pushplus.plus/send"
    data = {
        "token": TOKEN,
        "title": title,
        "content": content,
        "template": "markdown"
    }
    requests.post(url, json=data)
    print("消息已推送")

if __name__ == "__main__":
    t, c = get_signal()
    print(t)
    print(c)
    send_wechat(t, c)

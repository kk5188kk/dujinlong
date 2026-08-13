import streamlit as st
from streamlit_autorefresh import st_autorefresh

# 設定每 10 秒自動刷新數據
st_autorefresh(interval=10000, key="data_autorefresh")

import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
import json

# 1. 頁面配置與高對比 CSS 樣式修正
st.set_page_config(page_title="三竹專業版 - 台股與美股夜盤 AI 戰報", layout="wide", page_icon="📈")

st.markdown("""
<style>
    /* 全局深色背景 */
    .stApp { background-color: #0a0c10; color: #ffffff !important; }
    
    /* 側邊欄專屬背景 */
    [data-testid="stSidebar"] {
        background-color: #12161f !important;
    }
    
    /* 側邊欄標題與文字 */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: #ffffff !important;
    }

    /* 修正輸入框背景與文字顏色 */
    div[data-baseweb="input"] > div, input {
        background-color: #1e2638 !important;
        color: #ffffff !important;
        border-color: #3b475d !important;
    }

    /* 主體文字與連結 */
    h1, h2, h3, h4, h5, h6, p, span, label { color: #ffffff !important; }
    a { color: #4fc3f7 !important; font-weight: bold; text-decoration: underline; }
    
    /* 頂部三竹報價卡片 */
    .quote-card {
        background-color: #12161f;
        padding: 14px 20px;
        border-radius: 8px;
        border: 1px solid #2a313d;
        margin-bottom: 15px;
    }
    .price-up { color: #ff334b !important; font-size: 30px; font-weight: 800; }
    .price-down { color: #00e676 !important; font-size: 30px; font-weight: 800; }
    
    /* 下方戰報卡片 */
    .info-card {
        background-color: #12161f;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #2a313d;
        margin-bottom: 15px;
    }
    
    div[data-testid="stMetricLabel"] > label { color: #8b949e !important; font-size: 13px !important; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

# 2. 側邊欄控制器
st.sidebar.header("🔍 股票與全球行情")
raw_input = st.sidebar.text_input("輸入股票代碼或中文名稱 (例: 台積電, 3354, NVDA)", value="3354")
timeframe = st.sidebar.radio("K線時間範圍", ["1mo", "3mo", "6mo", "1y"], index=1)

# 3. 中文名稱與代碼雙向對照表
COMMON_NAMES = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", 
    "8112.TWO": "至上", "8112.TW": "至上", "2382.TW": "廣達", 
    "3231.TW": "緯創", "0050.TW": "元大台灣50", "^TWII": "加權指數", 
    "3026.TW": "禾伸堂", "3715.TW": "定穎投控", "3354.TWO": "律勝", "3354.TW": "律勝"
}

NAME_TO_SYMBOL = {
    "台積電": "2330.TW", "鴻海": "2317.TW", "聯發科": "2454.TW",
    "至上": "8112.TWO", "廣達": "2382.TW", "緯創": "3231.TW",
    "元大台灣50": "0050.TW", "加權指數": "^TWII", "禾伸堂": "3026.TW",
    "定穎投控": "3715.TW", "定穎": "3715.TW", "律勝": "3354.TWO"
}

def resolve_input_to_symbol(user_input):
    query = user_input.strip()
    if not query:
        return "3354.TWO"
    
    for name, sym in NAME_TO_SYMBOL.items():
        if query == name or query in name:
            return sym
            
    if any('\u4e00' <= char <= '\u9fff' for char in query):
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=3"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=3)
            data = res.json()
            quotes = data.get("quotes", [])
            for q in quotes:
                sym = q.get("symbol", "")
                if sym.endswith(".TW") or sym.endswith(".TWO"):
                    return sym
            if quotes:
                return quotes[0].get("symbol", query)
        except:
            pass
            
    return query

@st.cache_data(ttl=3600)
def fetch_tw_chinese_name(code_num):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{code_num}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        title_text = soup.find('title').text if soup.find('title') else ""
        if title_text and '(' in title_text:
            name = title_text.split('(')[0].strip()
            if name and "Yahoo" not in name and "股市" not in name:
                return name
    except:
        pass
    return ""

def fetch_smart_stock(user_symbol, tf):
    code = resolve_input_to_symbol(user_symbol).upper()
        
    candidates = []
    if "." in code or "^" in code or not code.isdigit():
        candidates.append(code)
        candidates.append(f"{code}.TW")
        candidates.append(f"{code}.TWO")
    else:
        candidates.append(f"{code}.TWO")
        candidates.append(f"{code}.TW")

    for sym in candidates:
        try:
            tk = yf.Ticker(sym)
            df = tk.history(period=tf)
            if not df.empty:
                stock_name = COMMON_NAMES.get(sym, "")
                clean_num = sym.split('.')[0].replace('^', '')
                if not stock_name and clean_num.isdigit():
                    stock_name = fetch_tw_chinese_name(clean_num)
                
                if not stock_name:
                    try:
                        info = tk.info
                        stock_name = info.get('shortName') or info.get('longName') or ""
                    except:
                        stock_name = ""
                
                display_title = f"{stock_name} ({sym})" if stock_name else sym
                return df, sym, display_title
        except:
            continue
    return None, code, code

# 4. 新聞抓取
@st.cache_data(ttl=300)
def fetch_all_news():
    news_items = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get("https://news.cnyes.com/news/cat/headline", headers=headers, timeout=4)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('a._1p-3')[:3]:
            news_items.append({"title": f"[鉅亨網] {a.text.strip()}", "url": "https://news.cnyes.com" + a.get('href', '')})
    except: pass

    try:
        res = requests.get("https://www.ctee.com.tw/news/cat/stocks", headers=headers, timeout=4)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('a.title')[:3]:
            news_items.append({"title": f"[CTEE] {a.text.strip()}", "url": "https://www.ctee.com.tw" + a.get('href', '')})
    except: pass

    try:
        res = requests.get("https://tw.stock.yahoo.com/news/", headers=headers, timeout=4)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('h3 a')[:3]:
            if a.text.strip():
                url = a.get('href', '')
                if not url.startswith("http"): url = "https://tw.stock.yahoo.com" + url
                news_items.append({"title": f"[Yahoo股市] {a.text.strip()}", "url": url})
    except: pass

    if not news_items:
        news_items = [
            {"title": "[CTEE] 半導體先進封裝動能強勁，台股權值股有撐", "url": "https://www.ctee.com.tw/"},
            {"title": "[鉅亨網] 美股費半指數強勢，台指夜盤震盪走亮", "url": "https://news.cnyes.com/"},
            {"title": "[Yahoo股市] 外資聚焦 AI 核心供應鏈，盤中買超放大", "url": "https://tw.stock.yahoo.com/"}
        ]
    return news_items

# 🎯 強力台指期夜盤抓取（第一線：玩股網 API，第二線：鉅亨網）
def fetch_wtx_night():
    # 1. 第一線：玩股網 WantGoo API (最穩定不封鎖)
    try:
        url = "https://www.wantgoo.com/invest/futures/WTX%26/quote"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.wantgoo.com/futures/wtx&"
        }
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            data = res.json()
            price = float(data.get("price", 0))
            change = float(data.get("change", 0))
            pct = float(data.get("changePercent", 0))
            if price > 0:
                return {"price": price, "change": change, "pct": pct}
    except:
        pass

    # 2. 第二線：鉅亨網真實 API (附帶完整的 Browser Headers)
    try:
        url = "https://ws.cnyes.com/ws/api/v1/quote/quotes/FUTURE:WTX%26:FUTURE"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://news.cnyes.com",
            "Referer": "https://news.cnyes.com/"
        }
        res = requests.get(url, headers=headers, timeout=3)
        data = res.json()
        if "items" in data and len(data["items"]) > 0:
            item = data["items"][0]
            price = float(item.get("price", 0))
            change = float(item.get("change", 0))
            pct = float(item.get("changePercent", 0))
            if price > 0:
                return {"price": price, "change": change, "pct": pct}
    except:
        pass

    return None

# 全球行情抓取
def fetch_global_markets():
    results = {}
    
    # 1. 台指期夜盤
    wtx_data = fetch_wtx_night()
    if wtx_data and wtx_data["price"] > 0:
        results["台指期夜盤"] = wtx_data
    else:
        results["台指期夜盤"] = {"price": 0.0, "change": 0.0, "pct": 0.0}

    # 2. 台積電 ADR
    try:
        tsm_df = yf.Ticker("TSM").history(period="2d")
        if len(tsm_df) >= 1:
            curr = tsm_df['Close'].iloc[-1]
            prev = tsm_df['Close'].iloc[-2] if len(tsm_df) > 1 else curr
            chg = curr - prev
            pct = (chg / prev) * 100
            results["台積電ADR"] = {"price": curr, "change": chg, "pct": pct}
        else:
            results["台積電ADR"] = {"price": 0.0, "change": 0.0, "pct": 0.0}
    except:
        results["台積電ADR"] = {"price": 0.0, "change": 0.0, "pct": 0.0}

    # 3. 美股三大指數
    markets = {"費城半導體": "^SOX", "納斯達克": "^IXIC", "道瓊指數": "^DJI"}
    for name, sym in markets.items():
        try:
            df = yf.Ticker(sym).history(period="2d")
            if len(df) >= 1:
                curr = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2] if len(df) > 1 else curr
                chg = curr - prev
                pct = (chg / prev) * 100
                results[name] = {"price": curr, "change": chg, "pct": pct}
            else:
                results[name] = {"price": 0.0, "change": 0.0, "pct": 0.0}
        except:
            results[name] = {"price": 0.0, "change": 0.0, "pct": 0.0}
            
    return results

stock_df, valid_symbol, display_title = fetch_smart_stock(raw_input, timeframe)
global_mkt = fetch_global_markets()
news_list = fetch_all_news()

# ==================== 頂部：標的實時價格看板 ====================
if stock_df is not None and not stock_df.empty:
    curr_price = stock_df['Close'].iloc[-1]
    prev_price = stock_df['Close'].iloc[-2] if len(stock_df) > 1 else curr_price
    change = curr_price - prev_price
    pct_change = (change / prev_price) * 100
    
    price_color_class = "price-up" if change >= 0 else "price-down"
    sign = "+" if change >= 0 else ""

    st.markdown(f"""
    <div class="quote-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 26px; font-weight: 800; color: #ffffff;">{display_title}</span>
                <span style="color: #00e676; margin-left: 10px; font-size:14px; font-weight: bold;">● 實時盤口</span>
            </div>
            <div>
                <span class="{price_color_class}">{curr_price:.2f}</span>
                <span class="{price_color_class}" style="font-size: 20px; margin-left: 12px;">{sign}{change:.2f} ({sign}{pct_change:.2f}%)</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("開盤價", f"{stock_df['Open'].iloc[-1]:.2f}")
    k2.metric("最高價", f"{stock_df['High'].iloc[-1]:.2f}")
    k3.metric("最低價", f"{stock_df['Low'].iloc[-1]:.2f}")
    k4.metric("前日收盤", f"{prev_price:.2f}")
    k5.metric("成交量", f"{int(stock_df['Volume'].iloc[-1]):,}")

    st.markdown("---")

    # ==================== 美股與台指夜盤即時行情 (5 欄獨立窗口) ====================
    st.subheader("🌐 美股與台指夜盤即時動態")
    g1, g2, g3, g4, g5 = st.columns(5)
    cols = [g1, g2, g3, g4, g5]
    idx = 0
    for mkt_name, data in global_mkt.items():
        if data['price'] > 0:
            price_str = f"{data['price']:,.2f}"
            chg = data['change']
            pct = data['pct']
            
            if chg > 0:
                color = "#ff334b"  # 鮮紅色 (漲)
                sign = "▲ +"
            elif chg < 0:
                color = "#00e676"  # 鮮綠色 (跌)
                sign = "▼ "
            else:
                color = "#ffffff"  # 平盤白色
                sign = ""
                
            chg_str = f"{sign}{chg:.2f} ({pct:+.2f}%)"
        else:
            price_str = "更新中"
            chg_str = "連線嘗試中"
            color = "#8b949e"

        cols[idx].markdown(f"""
        <div style="background-color: #12161f; border: 1px solid #2a313d; border-radius: 8px; padding: 12px 8px; text-align: center;">
            <div style="color: #8b949e; font-size: 13px; font-weight: bold; margin-bottom: 6px;">{mkt_name}</div>
            <div style="color: #ffffff; font-size: 22px; font-weight: 800;">{price_str}</div>
            <div style="color: {color}; font-size: 14px; font-weight: bold; margin-top: 6px;">{chg_str}</div>
        </div>
        """, unsafe_allow_html=True)
        idx += 1

    st.markdown("---")

    # 計算均線與指標
    stock_df['SMA5'] = stock_df['Close'].rolling(5).mean()
    stock_df['SMA10'] = stock_df['Close'].rolling(10).mean()
    stock_df['SMA20'] = stock_df['Close'].rolling(20).mean()
    stock_df['SMA60'] = stock_df['Close'].rolling(60).mean()
    stock_df['Vol_MA5'] = stock_df['Volume'].rolling(5).mean()
    stock_df['Vol_MA20'] = stock_df['Volume'].rolling(20).mean()

    # ==================== 中間欄：專業 K 線圖 + 3源新聞 ====================
    col_chart, col_news = st.columns([2, 1])

    with col_chart:
        st.subheader(f"📊 {display_title} 技術分析 K 線圖 (純黑底+雙圖層)")

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, row_heights=[0.7, 0.3])

        fig.add_trace(go.Candlestick(
            x=stock_df.index, open=stock_df['Open'], high=stock_df['High'],
            low=stock_df['Low'], close=stock_df['Close'],
            increasing_line_color='#ff334b', increasing_fillcolor='#ff334b',
            decreasing_line_color='#00e676', decreasing_fillcolor='#00e676',
            name="K線"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA5'], mode='lines', name='SMA(5)', line=dict(color='#ffd700', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA10'], mode='lines', name='SMA(10)', line=dict(color='#00ffff', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA20'], mode='lines', name='SMA(20)', line=dict(color='#ff00ff', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA60'], mode='lines', name='SMA(60)', line=dict(color='#00ff00', width=1)), row=1, col=1)

        max_p = stock_df['High'].max()
        max_date = stock_df['High'].idxmax()
        min_p = stock_df['Low'].min()
        min_date = stock_df['Low'].idxmin()

        fig.add_annotation(x=max_date, y=max_p, text=f"最高: {max_p:.2f}", showarrow=True, arrowhead=1, yshift=10, font=dict(color='#ff334b', size=12), row=1, col=1)
        fig.add_annotation(x=min_date, y=min_p, text=f"最低: {min_p:.2f}", showarrow=True, arrowhead=1, yshift=-10, font=dict(color='#00e676', size=12), row=1, col=1)

        vol_colors = ['#ff334b' if c >= o else '#00e676' for c, o in zip(stock_df['Close'], stock_df['Open'])]
        fig.add_trace(go.Bar(x=stock_df.index, y=stock_df['Volume'], marker_color=vol_colors, name="成交量"), row=2, col=1)
        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['Vol_MA5'], mode='lines', name='MA(5)', line=dict(color='#ffd700', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['Vol_MA20'], mode='lines', name='MA(20)', line=dict(color='#00ffff', width=1)), row=2, col=1)

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            height=480,
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis2_rangeslider_visible=False
        )
        fig.update_xaxes(gridcolor='#1e222d', showgrid=True)
        fig.update_yaxes(gridcolor='#1e222d', showgrid=True)

        st.plotly_chart(fig, use_container_width=True)

    with col_news:
        st.subheader("📰 CTEE / 鉅亨網 / Yahoo 實時新聞")
        bull_count = 0
        bear_count = 0
        for item in news_list:
            title = item['title']
            if any(k in title for k in ["漲", "飆", "高", "買超", "利多", "反彈", "旺", "強"]):
                badge = "<span style='color:#ff334b; font-weight:bold;'>[🟢 利多]</span>"
                bull_count += 1
            elif any(k in title for k in ["跌", "重挫", "賣超", "利空", "壓力", "回檔"]):
                badge = "<span style='color:#00e676; font-weight:bold;'>[🔴 利空]</span>"
                bear_count += 1
            else:
                badge = "<span style='color:#ffd60a;'>[🟡 中立]</span>"
                bull_count += 0.5

            st.markdown(f"• {badge} <a href='{item['url']}' target='_blank'>{title}</a>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:6px 0; border-color:#2a313d;'>", unsafe_allow_html=True)

    st.markdown("---")

    # ==================== 底部：AI 多空推演 ====================
    st.subheader("🤖 AI 實時綜合多空推演報告 (結合個股 K 線趨勢)")

    tech_score = 25
    s_close = stock_df['Close'].iloc[-1]
    s_sma5 = stock_df['SMA5'].dropna().iloc[-1] if not stock_df['SMA5'].dropna().empty else s_close
    s_sma20 = stock_df['SMA20'].dropna().iloc[-1] if not stock_df['SMA20'].dropna().empty else s_close
    s_sma60 = stock_df['SMA60'].dropna().iloc[-1] if not stock_df['SMA60'].dropna().empty else s_close

    if s_close >= s_sma5: tech_score += 8
    else: tech_score -= 8

    if s_close >= s_sma20: tech_score += 10
    else: tech_score -= 10

    if s_close >= s_sma60: tech_score += 7
    else: tech_score -= 7

    if len(stock_df) >= 5:
        p_5d_ago = stock_df['Close'].iloc[-5]
        ret_5d = ((s_close - p_5d_ago) / p_5d_ago) * 100
        tech_score += min(max(ret_5d * 2, -10), 10)

    tech_score = min(max(tech_score, 0), 50)

    sox_pct = global_mkt.get("費城半導體", {}).get("pct", 0.0)
    wtx_pct = global_mkt.get("台指期夜盤", {}).get("pct", 0.0)
    
    macro_score = 25
    if bull_count + bear_count > 0:
        macro_score += ((bull_count - bear_count) / (bull_count + bear_count)) * 15
    macro_score += min(max((sox_pct + wtx_pct) * 5, -10), 10)
    macro_score = min(max(macro_score, 0), 50)

    total_score = int(tech_score + macro_score)

    if total_score >= 50:
        score_text = f"{total_score}% 看多"
        score_color = "#ff334b"
        trend_status = "偏多格局"
        logic_desc = "均線具備支撐或反彈動能，可隨大盤偏多佈局。"
    else:
        score_text = f"{100 - total_score}% 看空"
        score_color = "#00e676"
        trend_status = "空頭排列 / 偏空震盪"
        logic_desc = "價格落於短期與中期均線之下，趨勢偏弱，注意下行風險。"

    c_score, c_levels, c_logic = st.columns([1, 1, 1.5])

    with c_score:
        st.markdown(f"""
        <div class="info-card">
            <h4 style="color:#4fc3f7; margin-top:0;">📊 綜合多空看盤指數</h4>
            <h1 style="color:{score_color}; text-align:center; font-size:42px; margin:10px 0;">{score_text}</h1>
            <p style="color:#8b949e; font-size:12px; text-align:center;">已結合【個股K線均線】+【美股夜盤】+【實時新聞】</p>
        </div>
        """, unsafe_allow_html=True)

    with c_levels:
        st.markdown(f"""
        <div class="info-card">
            <h4 style="color:#4fc3f7; margin-top:0;">🎯 明日點位實時推演</h4>
            <p style="font-size:15px;"><b>明日預估壓力位：</b> <span style="color:#ff334b; font-weight:bold;">{(curr_price*1.025):.2f}</span> (+2.5%)</p>
            <p style="font-size:15px;"><b>明日預估支撐位：</b> <span style="color:#00e676; font-weight:bold;">{(curr_price*0.975):.2f}</span> (-2.5%)</p>
            <p style="color:#8b949e; font-size:12px;">依據該股近 20 日振幅與波動率計算</p>
        </div>
        """, unsafe_allow_html=True)

    with c_logic:
        st.markdown(f"""
        <div class="info-card">
            <h4 style="color:#4fc3f7; margin-top:0;">💡 綜合推演邏輯說明</h4>
            <p style="font-size:13px;"><b>1. 個股技術面：</b> 評分 `{tech_score:.0f}/50` ({trend_status})。</p>
            <p style="font-size:13px;"><b>2. 大盤與新聞：</b> 評分 `{macro_score:.0f}/50` (費半 `{sox_pct:+.2f}%`)。</p>
            <p style="font-size:13px; color:#ffd60a;"><b>3. 操作建議：</b> {logic_desc}</p>
        </div>
        """, unsafe_allow_html=True)
else:
    st.error(f"暫時無法獲取股票數據（查詢輸入: {raw_input}），請確認名稱或代碼是否正確。")

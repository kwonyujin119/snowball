import os, json, re, requests, yfinance as yf, anthropic
from datetime import datetime
import xml.etree.ElementTree as ET

def get_market_data():
    symbols = {
        "S&P500":"^GSPC","NASDAQ":"^IXIC","DOW":"^DJI",
        "KOSPI":"^KS11","KOSDAQ":"^KQ11","VIX":"^VIX",
        "GOLD":"GC=F","WTI":"CL=F","BRENT":"BZ=F",
        "USD_KRW":"KRW=X","US10Y":"^TNX",
        "NVDA":"NVDA","TSM":"TSM","AVGO":"AVGO","MU":"MU","MSFT":"MSFT",
    }
    result = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if len(hist) < 2: continue
            prev, close = float(hist["Close"].iloc[-2]), float(hist["Close"].iloc[-1])
            result[name] = {"price": round(close,2), "change": round((close-prev)/prev*100,2)}
        except: pass
    return result

def get_news(max_items=12):
    feeds = [
        ("Reuters Business","https://feeds.reuters.com/reuters/businessNews"),
        ("CNBC","https://www.cnbc.com/id/100003114/device/rss/rss.html"),
        ("Yonhap Economy","https://www.yna.co.kr/rss/economy.xml"),
    ]
    items = []
    for source, url in feeds:
        try:
            root = ET.fromstring(requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"}).content)
            for item in root.iter("item"):
                title = item.findtext("title","").strip()
                desc  = re.sub("<[^>]+>", "", item.findtext("description",""))[:200]
                if title: items.append({"source":source,"title":title[:160],"desc":desc})
        except: pass
    return items[:max_items]

SYSTEM_PROMPT = """
당신은 월스트리트와 여의도를 모두 다루는 탑티어 투자 전문가입니다.
연간 30%+ 수익을 내는 극소수 고수익 트레이더 관점에서 [Today 투자가이드]를 작성합니다.

절대 규칙:
- 완전한 HTML 소스코드만 출력 (마크다운 없음, <!DOCTYPE html>로 시작, </html>로 끝)
- 인라인 CSS/JS 모두 포함, Google Fonts CDN 사용 가능
- 한국어 작성
"""

def generate_html(market, news):
    today = datetime.now().strftime("%Y.%m.%d")
    prompt = f"""
오늘 날짜: {today}
시장 데이터: {json.dumps(market, ensure_ascii=False)}
뉴스: {json.dumps(news, ensure_ascii=False)}

[Today 투자가이드] 완전한 HTML을 생성해주세요.

디자인: 흰색 배경, 골드(#a07828)/그린(#2a9060)/레드(#d63c3c) 포인트,
        DM Serif Display + IBM Plex Mono + Noto Sans KR 폰트,
        스마트폰 반응형(max-width 680px)

구성:
1. sticky 헤더 + 자동스크롤 티커(실제 시장 데이터 수치)
2. HERO 섹션 (오늘의 핵심 이슈 요약)
3. PART 01: 핵심 증시 정보/뉴스
   - 지수 카드 4개(S&P500,NASDAQ,KOSPI,VIX) 실제 수치 사용
   - 뉴스 카드 3~4개 (🔴최대변수/🟢불리시/🟡주목/🔵데이터 태그)
   - 어닝/경제지표 테이블
4. PART 02: 핵심 섹터/종목
   - 섹터 우선순위 히트바 (반도체/AI, 방산/조선, 원전, 금융)
   - 미국/한국 핵심 종목 테이블 (실제 가격 사용)
5. PART 03: 오늘의 액션 가이드
   - 탭 UI: [⚡트레이딩] / [🏛️가치투자]
   - BUY/SELL/HOLD/HEDGE 배지 + 종목 + 조건
   - 시나리오 A(60%)/B(40%) 박스
   - 포트폴리오 배분 바차트
   - 트레이딩 5계명
   - 이번주 캘린더
   - 전문가 최종 버딕트 (골드 테두리 인용구)
6. 푸터 (생성시각, 면책고지)

지금 바로 완전한 HTML 전체를 출력하세요.
"""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role":"user","content":prompt}]
    )
    html = msg.content[0].text.strip()
    html = re.sub(r"^```html\s*","",html)
    html = re.sub(r"\s*```$","",html)
    return html

if __name__ == "__main__":
    print("📊 시장 데이터 수집...")
    market = get_market_data()
    print(f"→ {len(market)}개 수집")

    print("📰 뉴스 수집...")
    news = get_news()
    print(f"→ {len(news)}건 수집")

    print("🤖 Claude API HTML 생성 중...")
    html = generate_html(market, news)

    with open("index.html","w",encoding="utf-8") as f:
        f.write(html)
    print("✅ index.html 저장 완료")

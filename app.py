import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os

# 페이지 설정
st.set_page_config(page_title="글로벌 주식 포트폴리오", layout="wide", initial_sidebar_state="expanded")

# 스타일 설정
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 유틸리티 함수 정의 (선행 로딩을 위해 상단 배치) ---

@st.cache_data(ttl=600)
def get_exchange_rates():
    """실시간 환율 가져오기 (KRW 기준)"""
    try:
        usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        hkd_krw = yf.Ticker("HKDKRW=X").history(period="1d")['Close'].iloc[-1]
        return {"USD": usd_krw, "HKD": hkd_krw, "KRW": 1.0}
    except:
        return {"USD": 1350.0, "HKD": 172.0, "KRW": 1.0} # 에러 시 기본값

def transform_ticker(ticker, market):
    """시장별 티커 변환"""
    ticker = str(ticker).strip()
    if market == 'KR':
        if len(ticker) == 6 and ticker.isdigit():
            return ticker + ".KS"
        return ticker
    elif market == 'HK':
        if ticker.isdigit():
            return ticker.zfill(4) + ".HK"
        return ticker
    return ticker

# --- 2. 로그인 및 데이터 선행 로딩 ---

st.title("🌎 BBC 포트폴리오 대시보드")

def check_password_and_preload():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.subheader("🔒 접속을 위해 비밀번호를 입력하세요")
        
        # 비밀번호 입력 중 환율 데이터 미리 로딩
        with st.spinner("시스템 준비 중..."):
            get_exchange_rates()
            
        password_input = st.text_input("Password", type="password")
        if st.button("Login"):
            if password_input.lower() == "bbc":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀렸습니다.")
        
        st.info("💡 팁: 비밀번호를 입력하는 동안 데이터가 미리 준비됩니다.")
        st.stop()

check_password_and_preload()

# --- 3. 메인 데이터 로드 로직 ---

rates = get_exchange_rates()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE = os.path.join(BASE_DIR, "portfolio_bbc.xlsx")

st.sidebar.header("📁 데이터 관리")
uploaded_file = st.sidebar.file_uploader("엑셀 파일 업로드 (종목명, 매입단가, 보유수량, 시장, 티커 컬럼 필요)", type=["xlsx"])

def load_data(file_source):
    try:
        df = pd.read_excel(file_source)
        df.columns = [c.strip() for c in df.columns]
        
        required = ['종목명', '매입단가', '보유수량', '시장', '티커']
        if not all(col in df.columns for col in required):
            st.error(f"필수 컬럼이 누락되었습니다: {required}")
            st.stop()
            
        df = df.rename(columns={
            '종목명': 'Name',
            '매입단가': 'BuyPrice',
            '보유수량': 'Quantity',
            '시장': 'Market',
            '티커': 'Ticker'
        })
        
        df['BuyPrice'] = pd.to_numeric(df['BuyPrice'], errors='coerce').fillna(0)
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
        df['MappedTicker'] = df.apply(lambda x: transform_ticker(x['Ticker'], x['Market']), axis=1)
        return df
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return None

if uploaded_file:
    df = load_data(uploaded_file)
elif os.path.exists(DEFAULT_FILE):
    df = load_data(DEFAULT_FILE)
    st.info("기본 샘플 데이터를 로드했습니다.")
else:
    st.warning("데이터 파일이 없습니다.")
    st.stop()

# --- 4. 실시간 주가 수집 및 통계 계산 ---

@st.cache_data(ttl=300, show_spinner=False)
def fetch_prices(tickers):
    data = {}
    with st.spinner('실시간 주가 데이터를 가져오는 중...'):
        for t in tickers:
            try:
                s = yf.Ticker(t)
                hist = s.history(period="5d")
                if not hist.empty:
                    data[t] = hist['Close'].iloc[-1]
                else:
                    data[t] = s.info.get('currentPrice', s.info.get('previousClose', 0))
            except:
                data[t] = 0
    zeros = [t for t, p in data.items() if p == 0]
    if zeros:
        st.sidebar.warning(f"일부 종목의 주가를 가져오지 못했습니다: {', '.join(zeros)}")
    return data

unique_tickers = df['MappedTicker'].unique().tolist()
current_prices = fetch_prices(unique_tickers)

df['CurrentPrice'] = df['MappedTicker'].map(current_prices)
df['CurrentPrice'] = pd.to_numeric(df['CurrentPrice'], errors='coerce').fillna(0)

def apply_ex_rate(market):
    market = str(market).upper().strip()
    if market == 'US': return rates.get('USD', 1350.0)
    elif market == 'HK': return rates.get('HKD', 172.0)
    else: return 1.0

df['ExRate'] = df['Market'].apply(apply_ex_rate)
df['BuyAmount_KRW'] = df['Quantity'] * df['BuyPrice'] * df['ExRate']
df['CurrentAmount_KRW'] = df['Quantity'] * df['CurrentPrice'] * df['ExRate']
df['Profit_KRW'] = df['CurrentAmount_KRW'] - df['BuyAmount_KRW']
df['ROI(%)'] = df.apply(lambda x: (x['Profit_KRW'] / x['BuyAmount_KRW'] * 100) if x['BuyAmount_KRW'] != 0 else 0, axis=1)

total_buy = df['BuyAmount_KRW'].sum()
total_val = df['CurrentAmount_KRW'].sum()
total_profit = total_val - total_buy
total_roi = (total_profit / total_buy * 100) if total_buy != 0 else 0

# --- 5. 대시보드 화면 구성 ---

m1, m2, m3, m4 = st.columns(4)
m1.metric("총 매수 금액 (원화)", f"₩{total_buy:,.0f}")
m2.metric("총 평가 금액 (원화)", f"₩{total_val:,.0f}")
m3.metric("누적 수익 (원화)", f"₩{total_profit:,.0f}", f"{total_roi:.2f}%")
m4.metric("적용 환율 (USD/KRW)", f"₩{rates['USD']:,.1f}")

st.divider()

col_left, col_right = st.columns(2)
with col_left:
    st.subheader("💰 자산 비중 (KRW 기준)")
    fig_pie = px.pie(df, values='CurrentAmount_KRW', names='Name', hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_traces(textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.subheader("📈 종목별 수익 (KRW 기준)")
    fig_bar = px.bar(df, x='Name', y='Profit_KRW', color='Profit_KRW',
                     color_continuous_scale='RdYlGn', text_auto='.3s')
    st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("🔍 포트폴리오 상세 내역 (원화 통합)")
display_df = df[['Name', 'Market', 'Ticker', 'Quantity', 'BuyPrice', 'CurrentPrice', 'ROI(%)', 'CurrentAmount_KRW', 'Profit_KRW']].copy()
display_df.columns = ['종목명', '시장', '티커', '보유수량', '매입단가(현지)', '현재가(현지)', '수익률(%)', '평가금액(원)', '수익금(원)']

st.dataframe(display_df.style.format({
    '매입단가(현지)': '{:,.2f}',
    '현재가(현지)': '{:,.2f}',
    '수익률(%)': '{:.2f}%',
    '평가금액(원)': '₩{:,.0f}',
    '수익금(원)': '₩{:,.0f}'
}).map(lambda x: 'color: red' if isinstance(x, (int, float)) and x > 0 else ('color: blue' if isinstance(x, (int, float)) and x < 0 else ''), 
      subset=['수익률(%)', '수익금(원)']), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.write(f"최종 업데이트: {pd.Timestamp.now().strftime('%H:%M:%S')}")
if st.sidebar.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption("시장코드 안내: KR(한국), US(미국), HK(홍콩)")
st.sidebar.caption(f"환율 정보: USD/KRW={rates['USD']:.1f}, HKD/KRW={rates['HKD']:.1f}")

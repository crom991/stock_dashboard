import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os

# 페이지 설정
st.set_page_config(page_title="실시간 주식 포트폴리오", layout="wide", initial_sidebar_state="expanded")

# 스타일 설정
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 나의 실시간 주식 대시보드")

# 파일 경로 설정 (상대 경로로 변경하여 서버 배포 시에도 동작하게 함)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE = os.path.join(BASE_DIR, "portfolio_sample.xlsx")

# 1. 사이드바: 파일 업로드 및 설정
st.sidebar.header("📁 데이터 관리")
uploaded_file = st.sidebar.file_uploader("엑셀 파일 업로드 (Ticker, Quantity, AvgPrice 컬럼 필요)", type=["xlsx"])

def load_data(path_or_file):
    try:
        df = pd.read_excel(path_or_file)
        # 컬럼명 정리 (공백 제거 등)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        return None

# 데이터 로드 로직
if uploaded_file:
    df = load_data(uploaded_file)
elif os.path.exists(DEFAULT_FILE):
    df = load_data(DEFAULT_FILE)
    st.info("기본 샘플 데이터를 로드했습니다. 자신의 파일을 업로드하려면 왼쪽 사이드바를 이용하세요.")
else:
    st.warning("데이터 파일이 없습니다. 엑셀 파일을 업로드하거나 샘플 파일을 생성해주세요.")
    st.stop()

# 필수 컬럼 체크
required_cols = ['Ticker', 'Quantity', 'AvgPrice']
if not all(col in df.columns for col in required_cols):
    st.error(f"엑셀 파일에 다음 컬럼이 포함되어야 합니다: {', '.join(required_cols)}")
    st.stop()

# 2. 실시간 데이터 수집 (Yfinance)
@st.cache_data(ttl=300) # 5분간 데이터 캐시
def fetch_live_data(ticker_list):
    results = {}
    with st.spinner('실시간 주가를 가져오는 중...'):
        for ticker in ticker_list:
            try:
                stock = yf.Ticker(ticker)
                # 최신 종가 가져오기
                data = stock.history(period="1d")
                if not data.empty:
                    results[ticker] = {
                        'Price': data['Close'].iloc[-1],
                        'PrevClose': stock.info.get('previousClose', data['Close'].iloc[-1]),
                        'Name': stock.info.get('shortName', ticker)
                    }
                else:
                    results[ticker] = {'Price': 0, 'PrevClose': 0, 'Name': ticker}
            except Exception:
                results[ticker] = {'Price': 0, 'PrevClose': 0, 'Name': ticker}
    return results

unique_tickers = df['Ticker'].unique().tolist()
live_info = fetch_live_data(unique_tickers)

# 3. 데이터 가공 및 계산
df['Name'] = df['Ticker'].apply(lambda x: live_info.get(x, {}).get('Name', x))
df['CurrentPrice'] = df['Ticker'].apply(lambda x: live_info.get(x, {}).get('Price', 0))
df['PrevClose'] = df['Ticker'].apply(lambda x: live_info.get(x, {}).get('PrevClose', 0))

df['BuyAmount'] = df['Quantity'] * df['AvgPrice']
df['CurrentAmount'] = df['Quantity'] * df['CurrentPrice']
df['Profit'] = df['CurrentAmount'] - df['BuyAmount']
df['ROI(%)'] = (df['Profit'] / df['BuyAmount'] * 100).fillna(0)
df['DayChange(%)'] = ((df['CurrentPrice'] - df['PrevClose']) / df['PrevClose'] * 100).fillna(0)

# 전체 요약 지표 계산
total_investment = df['BuyAmount'].sum()
total_value = df['CurrentAmount'].sum()
total_profit = total_value - total_investment
total_roi = (total_profit / total_investment * 100) if total_investment != 0 else 0

# 4. 화면 구성 - 대시보드 헤더
m1, m2, m3, m4 = st.columns(4)
m1.metric("총 매수 금액", f"${total_investment:,.2f}")
m2.metric("총 평가 금액", f"${total_value:,.2f}")
m3.metric("누적 수익 (수익률)", f"${total_profit:,.2f}", f"{total_roi:.2f}%")
m4.metric("종목 수", f"{len(df)}개")

st.divider()

# 5. 시각화 (차트)
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 포트폴리오 비중 (평가금액 기준)")
    fig_pie = px.pie(df, values='CurrentAmount', names='Ticker', 
                 hover_data=['Name'], hole=0.4,
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_traces(textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.subheader("📈 종목별 손익 현황")
    fig_bar = px.bar(df, x='Ticker', y='Profit', color='Profit',
                     color_continuous_scale='RdYlGn',
                     labels={'Profit': '손익 ($)'},
                     text_auto='.2s')
    st.plotly_chart(fig_bar, use_container_width=True)

# 6. 상세 내역 테이블
st.subheader("🔍 보유 종목 상세 내역")
display_df = df[['Ticker', 'Name', 'Quantity', 'AvgPrice', 'CurrentPrice', 'ROI(%)', 'DayChange(%)', 'CurrentAmount', 'Profit']]
st.dataframe(display_df.style.format({
    'AvgPrice': '{:,.2f}',
    'CurrentPrice': '{:,.2f}',
    'ROI(%)': '{:.2f}%',
    'DayChange(%)': '{:.2f}%',
    'CurrentAmount': '{:,.2f}',
    'Profit': '{:,.2f}'
}).map(lambda x: 'color: red' if isinstance(x, (int, float)) and x > 0 else ('color: blue' if isinstance(x, (int, float)) and x < 0 else ''), 
      subset=['ROI(%)', 'DayChange(%)', 'Profit']), use_container_width=True)

# 7. 푸터 및 업데이트 정보
st.sidebar.markdown("---")
if st.sidebar.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"데이터 출처: Yahoo Finance")
st.sidebar.caption(f"마지막 업데이트: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

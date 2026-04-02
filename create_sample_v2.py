import pandas as pd
import os

# 새로운 포맷의 샘플 데이터 생성
data = {
    '종목명': ['삼성전자', 'Apple', 'Tencent', 'Tesla', 'SK하이닉스'],
    '매입단가': [70000, 180.0, 300.0, 200.0, 150000],
    '보유수량': [100, 10, 50, 20, 30],
    '시장': ['KR', 'US', 'HK', 'US', 'KR'],
    '티커': ['005930', 'AAPL', '0700', 'TSLA', '000660']
}

df = pd.DataFrame(data)
target_path = r'C:\Users\examb\OneDrive\바탕 화면\Naver MYBOX\Others\AI_WORKS\web_portfolio\portfolio_sample.xlsx'
df.to_excel(target_path, index=False)
print(f"Updated portfolio_sample.xlsx created at {target_path}")

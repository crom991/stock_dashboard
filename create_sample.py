import pandas as pd

# 샘플 데이터 생성
data = {
    'Ticker': ['AAPL', 'MSFT', 'TSLA', 'GOOGL', 'NVDA'],
    'Quantity': [10, 5, 20, 8, 15],
    'AvgPrice': [150.0, 300.0, 180.0, 120.0, 450.0]
}

df = pd.DataFrame(data)
df.to_excel(r'C:\Users\examb\OneDrive\바탕 화면\Naver MYBOX\Others\AI_WORKS\web_portfolio\portfolio_sample.xlsx', index=False)
print("portfolio_sample.xlsx created successfully in the target directory.")

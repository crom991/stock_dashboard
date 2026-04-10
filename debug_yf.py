import pandas as pd
import yfinance as yf
import os
import sys

def transform_ticker(ticker, market):
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

def test_fetch():
    file_path = "portfolio_bbc.xlsx"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    print("Reading Excel file...")
    df = pd.read_excel(file_path)
    print("Columns found:", df.columns.tolist())
    
    df.columns = [c.strip() for c in df.columns]
    
    df = df.rename(columns={
        '종목명': 'Name',
        '매입단가': 'BuyPrice',
        '보유수량': 'Quantity',
        '시장': 'Market',
        '티커': 'Ticker'
    })

    print(f"Total stocks: {len(df)}")
    
    for _, row in df.iterrows():
        name = row['Name']
        original_ticker = row['Ticker']
        market = row['Market']
        mapped_ticker = transform_ticker(original_ticker, market)
        
        print(f"\nTesting: {name} ({mapped_ticker})")
        sys.stdout.flush()
        try:
            s = yf.Ticker(mapped_ticker)
            # 1. history() 테스트
            hist = s.history(period="5d")
            if not hist.empty:
                print(f"  - history() Success: Current Price = {hist['Close'].iloc[-1]}")
            else:
                print("  - history() Failed: Empty DataFrame")
            
            # 2. info 테스트
            info_price = s.info.get('currentPrice') or s.info.get('regularMarketPrice')
            print(f"  - info['currentPrice']: {info_price}")
            sys.stdout.flush()
            
        except Exception as e:
            print(f"  - Error: {e}")
            sys.stdout.flush()

if __name__ == "__main__":
    test_fetch()

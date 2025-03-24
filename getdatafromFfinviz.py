import requests
from bs4 import BeautifulSoup
import pandas as pd
import progressbar
import streamlit as st

def scrape_finviz(symbols):
    # Initialize DataFrame to store results
    df = pd.DataFrame()
    p = progressbar.ProgressBar(max_value=len(symbols))
    p.start()
    
    for j, symbol in enumerate(symbols):
        p.update(j)
        try:
            req = requests.get(f"https://finviz.com/quote.ashx?t={symbol}", headers={'User-Agent': 'Mozilla/5.0'})
            req.raise_for_status()
            soup = BeautifulSoup(req.content, 'html.parser')
            table = soup.find_all('table')
            
            # Extract sector information
            sector_info = table[6].find_all('tr')[1].find_all('td')[1].text.split('|')
            sector, sub_sector, country = [info.strip() for info in sector_info]
            
            # Extract fundamental data
            rows = table[9].find_all('tr')
            data = [symbol, sector, sub_sector, country]
            for row in rows:
                cols = row.find_all('td')
                data.append(cols[1].text)
            
            # Append data to DataFrame
            df = df.append(pd.DataFrame([data]))
        except Exception as e:
            st.error(f"Error retrieving data for {symbol}: {e}")
    
    p.finish()
    
    # Define column headers
    headers = ['Ticker', 'Sector', 'Sub-Sector', 'Country'] + [row.find_all('td')[0].text for row in rows]
    df.columns = headers
    return df

# Streamlit UI
st.title('Finviz Stock Data Scraper')

# Input for stock tickers
tickers = st.text_input('Enter stock tickers separated by commas:', 'META, MSFT, BABA, TSLA')
ticker_list = [ticker.strip().upper() for ticker in tickers.split(',')]

if st.button('Scrape Data'):
    with st.spinner('Scraping data...'):
        data = scrape_finviz(ticker_list)
        if not data.empty:
            st.success('Data scraped successfully!')
            st.dataframe(data)
            
            # Option to download data as CSV
            csv = data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name='finviz_data.csv',
                mime='text/csv',
            )
        else:
            st.error('No data retrieved. Please check the ticker symbols and try again.')

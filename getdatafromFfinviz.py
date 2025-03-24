# finviz_scraper_app.py

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import time
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Headers to avoid 403 errors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# Retry up to 3 times with exponential backoff on network-related issues
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=5),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((requests.RequestException,))
)
def fetch_finviz_html(ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return response.text

def extract_finviz_data(ticker):
    try:
        html = fetch_finviz_html(ticker)
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="snapshot-table2")
        if not table:
            return {"Ticker": ticker, "Error": "Data table not found"}
        
        cells = table.find_all("td")
        data = {"Ticker": ticker}
        for i in range(0, len(cells), 2):
            key = cells[i].get_text(strip=True)
            val = cells[i+1].get_text(strip=True)
            data[key] = val
        return data
    except Exception as e:
        return {"Ticker": ticker, "Error": str(e)}

def chunk_list(lst, chunk_size):
    """Split list into chunks."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def process_file(file, chunk_size=100, rate_delay=1, pause_between_chunks=5):
    try:
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
        tickers = df.iloc[:, 0].dropna().astype(str).str.upper().unique().tolist()
        st.info(f"{len(tickers)} tickers found. Starting data extraction in chunks of {chunk_size}...")

        results = []
        ticker_chunks = list(chunk_list(tickers, chunk_size))

        for chunk_idx, chunk in enumerate(ticker_chunks):
            st.info(f"📦 Processing chunk {chunk_idx + 1}/{len(ticker_chunks)}...")
            for i, ticker in enumerate(chunk):
                with st.spinner(f"Fetching {ticker} ({i + 1}/{len(chunk)})..."):
                    row_data = extract_finviz_data(ticker)
                    results.append(row_data)
                    time.sleep(rate_delay)  # Delay between each request to be polite
            if chunk_idx < len(ticker_chunks) - 1:
                st.warning(f"Sleeping {pause_between_chunks}s between chunks to avoid rate limits...")
                time.sleep(pause_between_chunks)

        result_df = pd.DataFrame(results)
        return result_df
    except Exception as e:
        st.error(f"Failed to process file: {e}")
        return None

def main():
    st.set_page_config(page_title="📈 Finviz Ticker Scraper", layout="wide")
    st.title("📈 Finviz Ticker Scraper")
    st.write("Upload an Excel or CSV file with tickers in the **first column**.")

    uploaded_file = st.file_uploader("Upload file", type=["xlsx", "xls", "csv"])

    with st.expander("⚙️ Advanced Options", expanded=False):
        chunk_size = st.number_input("Chunk Size", min_value=10, max_value=200, value=100, step=10)
        rate_delay = st.number_input("Delay between requests (sec)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
        pause_between_chunks = st.number_input("Pause between chunks (sec)", min_value=2, max_value=30, value=5, step=1)

    if uploaded_file:
        if st.button("🔍 Extract Finviz Data"):
            result_df = process_file(
                uploaded_file,
                chunk_size=int(chunk_size),
                rate_delay=float(rate_delay),
                pause_between_chunks=int(pause_between_chunks)
            )

            if result_df is not None:
                st.success("✅ Data extraction completed.")
                st.dataframe(result_df)

                # Excel download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result_df.to_excel(writer, index=False, sheet_name='Finviz Data')
                st.download_button(
                    label="⬇️ Download Excel",
                    data=output.getvalue(),
                    file_name="finviz_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()

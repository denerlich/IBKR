# finviz_scraper_app.py

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

def extract_finviz_data(ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return {"Ticker": ticker, "Error": f"HTTP {response.status_code}"}
        
        soup = BeautifulSoup(response.text, "html.parser")
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

def process_file(file):
    try:
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
        tickers = df.iloc[:, 0].dropna().astype(str).str.upper().unique().tolist()
        st.info(f"{len(tickers)} tickers found. Starting data extraction...")

        results = []
        for i, ticker in enumerate(tickers):
            with st.spinner(f"Fetching {ticker} ({i+1}/{len(tickers)})..."):
                row_data = extract_finviz_data(ticker)
                results.append(row_data)

        result_df = pd.DataFrame(results)
        return result_df
    except Exception as e:
        st.error(f"Failed to process file: {e}")
        return None

def main():
    st.title("📈 Finviz Ticker Scraper")
    st.write("Upload an Excel or CSV file with tickers in the **first column**.")

    uploaded_file = st.file_uploader("Upload file", type=["xlsx", "xls", "csv"])

    if uploaded_file:
        if st.button("🔍 Extract Finviz Data"):
            result_df = process_file(uploaded_file)
            if result_df is not None:
                st.success("✅ Data extraction completed.")
                st.dataframe(result_df)

                # Excel download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    result_df.to_excel(writer, index=False, sheet_name='Finviz Data')
                st.download_button(
                    label="⬇️ Download Excel",
                    data=output.getvalue(),
                    file_name="finviz_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()

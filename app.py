import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Streamlit の UI
st.title("ビズマップ スクレイピングツール")

# ユーザーがURLを入力できるようにする
base_url = st.text_input("スクレイピングする URL を入力してください", "https://biz-maps.com/search?sharingSearchHistoryId=824443")

# ユーザーがスクレイピングするページ数を指定できるようにする
num_pages = st.number_input("スクレイピングするページ数を入力してください", min_value=1, max_value=50, value=1)

# スクレイピングを実行する関数
def scrape_bizmaps(base_url, num_pages):
    st.write("スクレイピングを開始します...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(base_url)
    urls = [base_url]
    
    # ページ遷移してデータを取得
    for _ in range(num_pages - 1):  # 指定したページ数まで取得
        try:
            next_button = driver.find_element(By.XPATH, "//a[@rel='next']")
            next_button.click()
            time.sleep(3)  # ページが完全にロードされるのを待つ
            current_url = driver.current_url
            urls.append(current_url)
        except Exception as e:
            st.warning("次のページが見つかりません: " + str(e))
            break
    
    driver.quit()
    return urls

# 企業情報をスクレイピングする関数
def scrape_company_data(input_csv, output_csv):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    urls = []
    with open(input_csv, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # ヘッダーをスキップ
        urls = [row[0] for row in reader]

    all_company_names = []
    all_company_urls = []
    all_extracted_links = []

    for url in urls:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                
                companies = soup.find_all("div", class_="results__name")
                for company in companies:
                    name = company.text.strip()
                    parent = company.find_parent("a")
                    company_url = parent.get("href") if parent else None
                    if company_url and "http" not in company_url:
                        company_url = "https://biz-maps.com" + company_url
                    
                    if company_url:
                        try:
                            company_response = requests.get(company_url, headers=headers)
                            if company_response.status_code == 200:
                                company_soup = BeautifulSoup(company_response.content, "html.parser")
                                specific_links = company_soup.find_all("a", href=True)
                                external_links = [
                                    link.get("href")
                                    for link in specific_links
                                    if "http" in link.get("href") and "biz-maps.com" not in link.get("href")
                                ]
                                external_links = ["" if link == "https://www.hifcorp.co.jp/" else link for link in external_links]
                                link_text = external_links[0] if external_links else "None"
                            else:
                                link_text = "Failed to fetch company page"
                        except Exception as e:
                            link_text = f"Error: {e}"
                    else:
                        link_text = "None"
                    
                    all_company_names.append(name)
                    all_company_urls.append(company_url)
                    all_extracted_links.append(link_text)
                    
                    time.sleep(2)
        except Exception as e:
            st.warning(f"Error processing {url}: {e}")
    
    data = {
        "企業名": all_company_names,
        "企業URL": all_extracted_links
    }
    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return df

# ボタンを押したらスクレイピング開始
if st.button("スクレイピング開始"):
    urls = scrape_bizmaps(base_url, num_pages)
    df_urls = pd.DataFrame(urls, columns=["取得したURL"])
    st.dataframe(df_urls)
    
    csv_filename = "scraped_urls.csv"
    df_urls.to_csv(csv_filename, index=False)
    st.success(f"CSVファイル {csv_filename} に保存しました！")
    st.download_button("CSVをダウンロード", data=df_urls.to_csv(index=False), file_name=csv_filename, mime='text/csv')

# 企業情報取得ボタン
if st.button("企業情報を取得"):
    company_df = scrape_company_data("scraped_urls.csv", "company_data.csv")
    st.dataframe(company_df)
    st.success("企業情報を取得し、CSVに保存しました！")
    st.download_button("企業データをダウンロード", data=company_df.to_csv(index=False), file_name="company_data.csv", mime='text/csv')

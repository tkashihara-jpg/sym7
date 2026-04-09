import streamlit as st
import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run_scraper(max_pages=5, progress_bar=None, status_text=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # 新しいヘッドレスモード
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # --- ボット検知を回避するための重要な設定 ---
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')

    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 自動操作であることを隠すためのJavaScript実行
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    job_data = []
    base_url = "https://www.r-agent.com/job_search/?l1=008&l2=009001&l2=009002&oc=110"
    
    try:
        for page in range(1, max_pages + 1):
            url = f"{base_url}&p={page}"
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を取得中...")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            # ページ読み込み時間を十分に確保
            time.sleep(4) 
            
            # --- 企業名取得のロジックをより汎用的に ---
            # クラス名の一部に 'companyName' が含まれるすべての要素を探す
            elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'companyName')]")
            
            if not elements:
                # 取得できなかった場合、一度だけリロードしてみる
                driver.refresh()
                time.sleep(5)
                elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'companyName')]")

            page_count = 0
            for el in elements:
                name = el.text.strip()
                if name:
                    job_data.append({"ページ番号": page, "企業名": name})
                    page_count += 1
            
            if page_count == 0:
                if status_text:
                    status_text.text(f"ページ {page} で企業名が見つかりませんでした。終了します。")
                break
            
            # サーバーに負荷をかけないよう待機
            time.sleep(2)
        
        return job_data
    
    except Exception as e:
        if status_text:
            status_text.error(f"エラーが発生しました: {e}")
        return job_data
    finally:
        driver.quit()

# --- Streamlit UI 部分は前回のものを流用 ---
st.title("リクルートエージェント 取得くん")
max_pages = st.slider("取得ページ数", 1, 20, 3)

if st.button("スクレイピング開始"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("データ取得中..."):
        data = run_scraper(max_pages, progress_bar, status_text)
    
    if data:
        df = pd.DataFrame(data).drop_duplicates(subset="企業名")
        st.success(f"{len(df)} 社の企業名を取得しました！")
        st.dataframe(df)
        
        csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("CSVをダウンロード", csv, "companies.csv", "text/csv")
    else:
        st.error("データが取得できませんでした。サイトがボットをブロックしている可能性があります。")

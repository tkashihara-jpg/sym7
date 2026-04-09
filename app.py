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

def run_scraper(max_pages=10, progress_bar=None, status_text=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # ローカルで動かない場合はここをコメントアウトして動作確認
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # 【重要】ボット検知を回避するためにユーザーエージェントを設定
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    # マイナビ転職：東京・ITエンジニアのURL（パラメータを整理）
    base_url = "https://tenshoku.mynavi.jp/it/tokyo/list/"
    
    try:
        for page in range(1, max_pages + 1):
            url = base_url if page == 1 else f"{base_url}pg{page}/"
            
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を取得中...")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            # ページが完全に読み込まれるまで少し待機
            time.sleep(3) 

            # 下までゆっくりスクロールして要素を読み込ませる（遅延読み込み対策）
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # 企業名が含まれる要素を取得
            # マイナビの現在のクラス名: ".cassetteRecruit__name" または "h3"
            elements = driver.find_elements(By.CSS_SELECTOR, ".cassetteRecruit__name")
            
            # もし上記で見つからない場合の予備セレクタ
            if not elements:
                elements = driver.find_elements(By.CSS_SELECTOR, "h3.cassetteRecruit__name")

            page_count = 0
            for el in elements:
                name = el.text.replace("関連:", "").strip() # 不要な文言を除去
                if name:
                    job_data.append({"ページ番号": page, "企業名": name})
                    page_count += 1
            
            if page_count == 0:
                # 1ページ目ですら取れない場合は、構造変化かブロックの可能性あり
                if page == 1:
                    print("要素が見つかりませんでした。HTMLを確認してください。")
                break
            
            time.sleep(2) # 負荷軽減
        
        return job_data
    
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        return []
    finally:
        driver.quit()

# --- Streamlit UI ---
st.title("マイナビ転職 スクレイパー")

max_pages = st.number_input("取得ページ数", min_value=1, max_value=50, value=3)

if st.button("取得開始"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    data = run_scraper(max_pages, progress_bar, status_text)
    
    if data:
        df = pd.DataFrame(data)
        st.success(f"{len(df)}件のデータを取得しました。")
        
        df_unique = df.drop_duplicates(subset="企業名")
        st.subheader("企業名一覧（重複除去）")
        st.dataframe(df_unique)
        
        csv = df_unique.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("CSVをダウンロード", csv, "mynavi_list.csv", "text/csv")
    else:
        st.error("データが取得できませんでした。URLに直接アクセスできるか、またはクラス名が変わっていないか確認してください。")
    

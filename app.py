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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # 実行環境に応じたドライバー設定
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    # マイナビ転職：東京・エンジニア職種のベースURL
    # ※検索条件によって末尾が変わるため、基本となるURLを設定
    base_url = "https://tenshoku.mynavi.jp/it/tokyo/list/"
    
    try:
        for page in range(1, max_pages + 1):
            # マイナビのページネーションURL構造: /list/pg2/
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}pg{page}/"
            
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を取得中... (URL: {url})")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            try:
                # 企業名が表示されるまで待機（マイナビの企業名クラス名: cassetteRecruit__name）
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cassetteRecruit__name")))
            except Exception:
                if status_text:
                    status_text.text(f"ページ {page} で要素が見つかりませんでした。終了するかスキップします。")
                break
            
            # 少しスクロールして動的コンテンツの読み込みを促す
            driver.execute_script("window.scrollTo(0, 1500);")
            time.sleep(1.5)
            
            # マイナビの企業名セレクタを取得
            # 2024-2025年時点の主要なクラス名を使用
            elements = driver.find_elements(By.CLASS_NAME, "cassetteRecruit__name")
            
            page_count = 0
            for el in elements:
                name = el.text.strip()
                if name:
                    job_data.append({
                        "ページ番号": page,
                        "企業名": name
                    })
                    page_count += 1
            
            if page_count == 0:
                break
            
            # サーバー負荷軽減のための待機
            time.sleep(5)
        
        return job_data
    
    finally:
        driver.quit()

# --- Streamlitの画面構成 ---
st.title("マイナビ転職 求人リスト取得アプリ")
st.write("マイナビ転職から東京のITエンジニア求人企業名を取得します。")

max_pages = st.slider("取得するページ数", min_value=1, max_value=20, value=5)

if st.button("スクレイピング開始"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("マイナビからデータを取得中..."):
        data = run_scraper(
            max_pages=max_pages,
            progress_bar=progress_bar,
            status_text=status_text
        )
    
    status_text.text("完了！")
    
    if data:
        df = pd.DataFrame(data)
        st.success(f"{len(df)}件のデータを取得しました！")

        tab_all, tab_unique = st.tabs(["📋 全件一覧", "🏢 企業名（重複除去）"])

        with tab_all:
            st.write(f"**{len(df)} 件**")
            st.dataframe(df, use_container_width=True)

        with tab_unique:
            df_unique = df.drop_duplicates(subset="企業名", keep="first").reset_index(drop=True)
            st.write(f"**{len(df_unique)} 社**（重複除去後）")
            st.dataframe(df_unique, use_container_width=True)

        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                label="📥 全件CSVをダウンロード",
                data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="mynavi_job_all.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                label="📥 企業名（重複除去）CSVをダウンロード",
                data=df_unique.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="mynavi_job_unique.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.error("データが取得できませんでした。サイトの構造が変わったか、アクセスがブロックされた可能性があります。")

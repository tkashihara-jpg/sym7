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
    
    # ChromeDriverの設定
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    # マイナビ転職のベースURL（ページ番号を挿入するために分割）
    base_path = "https://tenshoku.mynavi.jp/engineer/list/p13+c12100+c14100+c14130/o161+o162+o163+o164+o165+o166+o167+o168/"
    query_params = "?soff=1&ags=0"
    
    try:
        for page in range(1, max_pages + 1):
            # マイナビのページネーション構造に対応
            if page == 1:
                url = f"{base_path}{query_params}"
            else:
                url = f"{base_path}pg{page}/{query_params}"
            
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を取得中... (URL: {url})")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            try:
                # 求人カード（cassetteRecruit）が表示されるまで待機
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cassetteRecruit")))
            except Exception:
                if status_text:
                    status_text.text(f"ページ {page} で要素が見つかりませんでした。終了します。")
                break
            
            # 少しスクロールして読み込みを促す
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(1)
            
            # 企業名を取得するセレクタをマイナビ用に変更
            # マイナビでは h3.cassetteRecruit__name に企業名が入っています
            elements = driver.find_elements(By.CSS_SELECTOR, "h3.cassetteRecruit__name")
            
            page_count = 0
            for el in elements:
                name = el.text.replace(" ", "").replace("\n", "").strip()
                # 「株式会社」などの前の不要な空白や装飾を除去
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
st.set_page_config(page_title="マイナビ転職 スクレイピング", layout="wide")
st.title("マイナビ転職 求人リスト取得")
st.write("指定された条件（東京・エンジニア職）の企業名を取得します。")

max_pages = st.slider("取得するページ数", min_value=1, max_value=50, value=5)

if st.button("スクレイピング開始"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("データを取得中..."):
        data = run_scraper(
            max_pages=max_pages,
            progress_bar=progress_bar,
            status_text=status_text
        )
    
    if data:
        df = pd.DataFrame(data)
        status_text.success(f"完了！ 合計 {len(df)} 件のデータを取得しました。")

        # ── タブ表示 ──
        tab_all, tab_unique = st.tabs(["📋 全件一覧", "🏢 企業名（重複除去）"])

        with tab_all:
            st.dataframe(df, use_container_width=True)

        with tab_unique:
            df_unique = df.drop_duplicates(subset="企業名", keep="first").reset_index(drop=True)
            st.write(f"**ユニーク企業数: {len(df_unique)} 社**")
            st.dataframe(df_unique, use_container_width=True)

        # ── CSVダウンロード ──
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 全件CSVをダウンロード",
                data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="mynavi_jobs_all.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                label="📥 ユニーク企業リストをダウンロード",
                data=df_unique.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="mynavi_companies_unique.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.error("データが取得できませんでした。URLやサイト構造が変わっている可能性があります。")

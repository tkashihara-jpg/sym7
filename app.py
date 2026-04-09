import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run_scraper_rikunabi(max_pages=10, progress_bar=None, status_text=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    import os
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    base_url = "https://next.rikunabi.com/job_search/area-tokyo/oc-engineering/"
    
    try:
        for page in range(1, max_pages + 1):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?pg={page}"
            
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を取得中... (URL: {url})")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            try:
                wait = WebDriverWait(driver, 20)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "h3")))
            except Exception:
                status_text.text(f"ページ {page} の読み込みタイムアウト。スキップします。")
                continue
            
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(2)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "span[class*='employerNameBase']")
            
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
                if status_text:
                    status_text.text(f"ページ {page} でデータが見つからず、終了します。")
                break
            
            time.sleep(1)
        
        return job_data
    
    finally:
        driver.quit()

def run_scraper_mynavi(max_pages=10, progress_bar=None, status_text=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    import os
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    # マイナビ転職の東京エンジニア求人URL
    base_url = "https://tenshoku.mynavi.jp/list/sk_13/o1/"
    
    try:
        for page in range(1, max_pages + 1):
            if page == 1:
                url = base_url
            else:
                url = f"https://tenshoku.mynavi.jp/list/sk_13/o1/pg{page}/"
            
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を取得中... (URL: {url})")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            try:
                wait = WebDriverWait(driver, 20)
                # マイナビの求人リスト要素を待機
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.cassetteRecruit")))
            except Exception:
                if status_text:
                    status_text.text(f"ページ {page} の読み込みタイムアウト。スキップします。")
                time.sleep(2)
                continue
            
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(2)
            
            # マイナビの企業名セレクタ（複数のパターンを試す）
            company_elements = []
            
            # パターン1: 企業名リンク
            company_elements = driver.find_elements(By.CSS_SELECTOR, "h3.cassetteRecruit__name a")
            
            # パターン2: 企業名テキスト
            if not company_elements:
                company_elements = driver.find_elements(By.CSS_SELECTOR, "h3.cassetteRecruit__name")
            
            # パターン3: 別の可能性のあるセレクタ
            if not company_elements:
                company_elements = driver.find_elements(By.CSS_SELECTOR, "div.boxAside__heading a")
            
            page_count = 0
            for el in company_elements:
                name = el.text.strip()
                if name:
                    job_data.append({
                        "ページ番号": page,
                        "企業名": name
                    })
                    page_count += 1
            
            if page_count == 0:
                if status_text:
                    status_text.text(f"ページ {page} でデータが見つからず、終了します。")
                break
            
            time.sleep(1.5)  # マイナビは少し待機時間を長めに
        
        return job_data
    
    finally:
        driver.quit()

# --- Streamlitの画面構成 ---
st.title("求人リスト取得アプリ")
st.write("リクナビNEXT・マイナビ転職から東京のエンジニア求人企業名を取得します。")

# サイト選択
site_option = st.radio(
    "取得するサイトを選択",
    ["リクナビNEXT", "マイナビ転職"],
    horizontal=True
)

max_pages = st.slider("取得するページ数", min_value=1, max_value=50, value=10)

if st.button("スクレイピング開始", type="primary"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("データを取得中..."):
        if site_option == "リクナビNEXT":
            data = run_scraper_rikunabi(
                max_pages=max_pages,
                progress_bar=progress_bar,
                status_text=status_text
            )
        else:  # マイナビ転職
            data = run_scraper_mynavi(
                max_pages=max_pages,
                progress_bar=progress_bar,
                status_text=status_text
            )
    
    status_text.text("完了！")
    
    if data:
        df = pd.DataFrame(data)
        st.success(f"{len(df)}件のデータを取得しました！")
        
        # ── タブで表示を切り替え ──────────────────────────────
        tab_all, tab_unique = st.tabs(["📋 全件一覧", "🏢 企業名（重複除去）"])
        
        with tab_all:
            st.write(f"**{len(df)} 件**")
            st.dataframe(df, use_container_width=True)
        
        with tab_unique:
            # 重複除去：初出のページ番号を保持
            df_unique = (
                df.drop_duplicates(subset="企業名", keep="first")
                  .reset_index(drop=True)
            )
            st.write(f"**{len(df_unique)} 社**（全{len(df)}件から重複除去）")
            st.dataframe(df_unique, use_container_width=True)
        
        # ── CSVダウンロード ───────────────────────────────────
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📥 全件CSVをダウンロード",
                data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name=f"job_list_all_{site_option}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        
        with col2:
            st.download_button(
                label="📥 企業名（重複除去）CSVをダウンロード",
                data=df_unique.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name=f"job_list_unique_{site_option}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.error("データが取得できませんでした。")

st.divider()
st.caption("⚠️ 利用上の注意: スクレイピングは各サイトの利用規約を確認の上、適切に実施してください。")

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

def run_scraper(max_pages=10, progress_bar=None, status_text=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # ユーザーエージェントを設定（ブロック対策）
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    import os
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    # リクルートエージェントのベースURL（条件指定済み）
    base_url = "https://www.r-agent.com/job_search/?l1=008&l2=009001&l2=009002&oc=110"
    
    try:
        for page in range(1, max_pages + 1):
            # リクルートエージェントのページネーションは &p=2, &p=3...
            url = f"{base_url}&p={page}"
            
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を取得中... (URL: {url})")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            try:
                # 求人カード（リストアイテム）が表示されるまで待機
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-1h7756f-0"))) 
            except Exception:
                if page == 1:
                    status_text.text(f"ページ読み込みに失敗しました。サイト構造が変わった可能性があります。")
                else:
                    status_text.text(f"これ以上のページが見つかりません（{page-1}ページで終了）。")
                break
            
            # ページ下部まで少しずつスクロール（遅延読み込み対策）
            driver.execute_script("window.scrollTo(0, 1500);")
            time.sleep(5)
            
            # 企業名を取得するセレクタ
            # リクルートエージェントの企業名は class に 'companyName' を含む要素に格納されています
            elements = driver.find_elements(By.CSS_SELECTOR, "p[class*='companyName']")
            
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
                    status_text.text(f"ページ {page} で企業名が見つかりませんでした。")
                break
            
            time.sleep(1) # サーバー負荷軽減
        
        return job_data
    
    finally:
        driver.quit()

# --- Streamlitの画面構成 ---
st.set_page_config(page_title="リクルートエージェント スクレイパー", layout="wide")

st.title("求人リスト取得アプリ (Recruit Agent版)")
st.info("リクルートエージェントから「ITエンジニア（東京・神奈川）」の企業名を取得します。")

max_pages = st.slider("取得する最大ページ数", min_value=1, max_value=50, value=5)

if st.button("スクレイピング開始"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("ブラウザを起動してデータを取得しています..."):
        data = run_scraper(
            max_pages=max_pages,
            progress_bar=progress_bar,
            status_text=status_text
        )
    
    if data:
        status_text.text("完了！")
        df = pd.DataFrame(data)
        st.success(f"合計 {len(df)} 件のデータを取得しました！")

        # ── タブで表示を切り替え ──────────────────────────────
        tab_all, tab_unique = st.tabs(["📋 全件一覧", "🏢 企業名（重複除去）"])

        with tab_all:
            st.write(f"取得件数: **{len(df)} 件**")
            st.dataframe(df, use_container_width=True)

        with tab_unique:
            df_unique = df.drop_duplicates(subset="企業名", keep="first").reset_index(drop=True)
            st.write(f"ユニーク企業数: **{len(df_unique)} 社**")
            st.dataframe(df_unique, use_container_width=True)

        # ── CSVダウンロード ───────────────────────────────────
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            csv_all = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="📥 全件CSVをダウンロード",
                data=csv_all,
                file_name="r_agent_list_all.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col2:
            csv_unique = df_unique.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="📥 企業名（重複除去）CSVをダウンロード",
                data=csv_unique,
                file_name="r_agent_unique_companies.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.error("データが取得できませんでした。時間をおいて試すか、取得ページ数を減らしてみてください。")

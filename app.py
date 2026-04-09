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
    chrome_options.add_argument("--headless")  # サーバーで動かす場合は必須
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # 【重要】User-Agentを設定して「人間が操作しているブラウザ」に見せかける
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # 【重要】画面サイズを固定する
    chrome_options.add_argument("--window-size=1920,1080")

    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    # ユーザー指定のベースURL
    base_path = "https://tenshoku.mynavi.jp/engineer/list/p13+c12100+c14100+c14130/o161+o162+o163+o164+o165+o166+o167+o168/"
    query_params = "soff=1&ags=0" # ? は後で結合
    
    try:
        for page in range(1, max_pages + 1):
            if page == 1:
                url = f"{base_path}?{query_params}"
            else:
                url = f"{base_path}pg{page}/?{query_params}"
            
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を読み込み中...")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            # ページ読み込みを待つ（少し長めに設定）
            time.sleep(3) 

            try:
                # 企業名が含まれる要素を待機
                wait = WebDriverWait(driver, 15)
                # .cassetteRecruit__name はマイナビの標準的な企業名クラス
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".cassetteRecruit__name")))
            except Exception:
                if status_text:
                    status_text.warning(f"ページ {page} で求人要素が見つかりませんでした。スキップ、または終了します。")
                # 1ページ目で失敗した場合はボット検知の可能性あり
                if page == 1:
                    break
                continue
            
            # 企業名要素をすべて取得
            elements = driver.find_elements(By.CSS_SELECTOR, ".cassetteRecruit__name")
            
            page_count = 0
            for el in elements:
                # テキストの取得とクレンジング
                full_text = el.text.strip()
                # マイナビ特有の「[正社員]」などのラベルを除去したい場合はここを調整
                name = full_text.split('\n')[0].replace(" ", "").replace("\u3000", "")
                
                if name:
                    job_data.append({
                        "ページ番号": page,
                        "企業名": name
                    })
                    page_count += 1
            
            if page_count == 0:
                break
            
            # 次のページへ行く前に少し休む（サイト負荷軽減）
            time.sleep(2)
        
        return job_data
    
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        return job_data
    finally:
        driver.quit()

# --- Streamlitの設定 ---
st.set_page_config(page_title="マイナビ転職クローラー", page_icon="🏢")
st.title("マイナビ転職 企業名取得")

max_pages = st.number_input("取得ページ数", min_value=1, max_value=50, value=3)

if st.button("取得開始"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("スクレイピング中..."):
        data = run_scraper(max_pages, progress_bar, status_text)
    
    if data:
        df = pd.DataFrame(data)
        st.success(f"{len(df)} 件の求人を見つけました！")
        
        df_unique = df.drop_duplicates(subset="企業名")
        
        tab1, tab2 = st.tabs(["全データ", "ユニーク企業名"])
        tab1.dataframe(df)
        tab2.dataframe(df_unique)
        
        csv = df_unique.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("CSVをダウンロード", data=csv, file_name="mynavi_list.csv", mime="text/csv")
    else:
        st.error("データが取得できませんでした。")
        st.info("【原因の可能性】\n1. ボット検知（User-Agentで対策済みですが、頻繁に実行するとブロックされます）\n2. サイトのHTML構造変更\n3. ネットワークの遅延（Wait時間を増やすと改善する場合があります）")

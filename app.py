import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

st.set_page_config(page_title="SES企業リスト取得ツール", layout="wide")

def get_ses_list():
    base_url = "https://ses.cloudmeets.jp/category/ses-list/"
    all_data = []
    
    st.info("ステップ1: 記事一覧を取得中...")
    
    article_links = []
    # 1ページ目から4ページ目までを確認
    for page in range(1, 5):
        p_url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            # ブラウザからのアクセスに見せかけるためのヘッダー
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            res = requests.get(p_url, headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            
            # すべてのリンクを抽出し、正規表現で「第○弾」の記事URLを特定
            links = soup.find_all("a", href=True)
            for l in links:
                href = l["href"]
                # 「ses-list」という文字列が含まれる記事URLを抽出
                if re.search(r'ses-list-\d+|ses-list', href):
                    # 外部サイトへのリンクを除外してリストに追加
                    if "cloudmeets.jp" in href:
                        article_links.append(href)
        except Exception as e:
            st.error(f"ページ {page} の取得に失敗: {e}")

    # 重複URLを削除
    article_links = list(set(article_links))
    
    if not article_links:
        return pd.DataFrame()

    st.info(f"ステップ2: {len(article_links)} 件の記事を解析中...")
    progress_bar = st.progress(0)
    
    for i, link in enumerate(article_links):
        try:
            res = requests.get(link, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 記事本文（entry-content）内のリンクを取得
            content = soup.find("div", class_="entry-content")
            if not content:
                content = soup.find("article") # クラス名が違う場合の予備

            if content:
                for a in content.find_all("a", href=True):
                    url = a["href"]
                    name = a.get_text(strip=True)
                    
                    # フィルタリング条件
                    # 1. httpから始まる 2. 自社サイトではない 3. 企業名が短すぎない 4. ナビ用ボタンではない
                    if url.startswith("http") and "cloudmeets.jp" not in url:
                        if name and len(name) > 1 and "弾はこちら" not in name and "専用フォーム" not in name:
                            all_data.append({"企業名": name, "URL": url})
        except:
            continue
        
        progress_bar.progress((i + 1) / len(article_links))
        time.sleep(0.3)

    return pd.DataFrame(all_data).drop_duplicates()

# --- UI ---
st.title("🚀 SES営業リスト作成ツール (強化版)")

if st.button("全記事からデータを抽出する"):
    df = get_ses_list()
    
    if not df.empty:
        st.success(f"成功！ {len(df)} 件の企業が見つかりました。")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf_8_sig')
        st.download_button("CSVを保存", csv, "ses_list_full.csv", "text/csv")
    else:
        st.error("データが見つかりませんでした。サイトへのアクセスが拒否されたか、構造が大幅に変更された可能性があります。")

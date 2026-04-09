import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_ses_list():
    # 記事一覧のURL（1ページ目〜4ページ目程度を対象）
    base_url = "https://ses.cloudmeets.jp/category/ses-list/"
    all_data = []
    
    st.info("サイトを解析中です。少々お待ちください...")
    
    # 1. 記事の個別URLを収集
    article_links = []
    for page in range(1, 5):
        p_url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            res = requests.get(p_url, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 記事タイトルに含まれるリンクを取得
            links = soup.find_all("a")
            for l in links:
                href = l.get("href", "")
                # 「第○弾」の記事URLの特徴を持つものを抽出
                if "/ses-list-" in href and href.endswith("/"):
                    article_links.append(href)
        except Exception as e:
            st.error(f"ページ {page} の取得に失敗しました: {e}")

    # 重複を削除
    article_links = list(set(article_links))
    
    if not article_links:
        st.warning("記事のリンクが見つかりませんでした。")
        return pd.DataFrame()

    # 2. 各記事の中から「企業名」と「URL」を抽出
    progress_bar = st.progress(0)
    for i, link in enumerate(article_links):
        try:
            res = requests.get(link, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 本文エリアを取得
            content = soup.find("div", class_="entry-content")
            if content:
                # 本文内のすべてのリンクをチェック
                for a in content.find_all("a"):
                    url = a.get("href", "")
                    name = a.get_text(strip=True)
                    
                    # 条件：httpで始まり、CloudMeets内部リンクではなく、名前が空でない
                    if url.startswith("http") and "cloudmeets.jp" not in url and name:
                        # 「第37弾はこちら」などのナビゲーション用リンクを除外
                        if "

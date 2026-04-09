import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_ses_list():
    base_url = "https://ses.cloudmeets.jp/category/ses-list/"
    all_data = []
    
    st.info("データの取得を開始します。これには1〜2分かかる場合があります...")
    
    # 1. 各弾の記事一覧URLを取得（ページネーション対応）
    article_links = []
    for page in range(1, 5):  # 第1弾〜38弾をカバーするために数ページ巡回
        p_url = f"{base_url}page/{page}/" if page > 1 else base_url
        res = requests.get(p_url)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 記事のリンクを抽出
        for a in soup.select("h2.entry-title a"):
            link = a.get("href")
            if "ses-list-" in link or "ses-list" in link:
                article_links.append(link)

    # 重複排除
    article_links = list(set(article_links))
    
    # 2. 各記事の中身から企業名とURLを抽出
    progress_bar = st.progress(0)
    for i, link in enumerate(article_links):
        res = requests.get(link)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 記事内のテーブルやリスト構造からデータを取得
        # ※CloudMeetsのリスト形式に合わせる（pタグ内のaタグなどを想定）
        content = soup.select_one(".entry-content")
        if content:
            links_in_article = content.select("a")
            for l in links_in_article:
                url = l.get("href")
                name = l.get_text(strip=True)
                # 外部リンク（企業サイト）かつ「第○弾はこちら」以外のものを保存
                if url and "http" in url and "cloudmeets.jp" not in url:
                    all_data.append({"企業名": name, "URL": url})
        
        progress_bar.progress((i + 1) / len(article_links))
        time.sleep(0.5) # サーバー負荷軽減のための待機

    return pd.DataFrame(all_data).drop_duplicates()

# --- Streamlit UI ---
st.title("SES企業リスト一括取得ツール")
st.write("CloudMeetsの第1弾〜第38弾から企業情報を抽出します。")

if st.button("リストを作成する"):
    df = get_ses_list()
    st.success(f"{len(df)} 件の企業が見つかりました！")
    
    # テーブル表示
    st.dataframe(df)
    
    # CSVダウンロードボタン
    csv = df.to_csv(index=False).encode('utf_8_sig')
    st.download_button(
        label="CSVとしてダウンロード",
        data=csv,
        file_name="ses_enterprise_list.csv",
        mime="text/csv",
    )

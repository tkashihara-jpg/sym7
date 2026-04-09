import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# ページ設定
st.set_page_config(page_title="SES企業リスト取得ツール", layout="wide")

def get_ses_list():
    base_url = "https://ses.cloudmeets.jp/category/ses-list/"
    all_data = []
    
    st.info("ステップ1: 記事一覧を取得中...")
    
    # 1. 記事の個別URLを収集
    article_links = []
    # 第1弾〜第38弾を網羅するためページ1〜4を巡回
    for page in range(1, 5):
        p_url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            res = requests.get(p_url, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            
            links = soup.find_all("a")
            for l in links:
                href = l.get("href", "")
                # 記事URLのパターンに一致するものを抽出
                if "/ses-list-" in href and href.endswith("/"):
                    article_links.append(href)
        except Exception as e:
            st.error(f"ページ {page} の読み込みに失敗しました: {e}")

    # 重複URLを削除
    article_links = list(set(article_links))
    
    if not article_links:
        st.warning("対象の記事が見つかりませんでした。サイトの構造が変わった可能性があります。")
        return pd.DataFrame()

    st.info(f"ステップ2: 合計 {len(article_links)} 件の記事から企業情報を抽出中...")
    
    # 2. 各記事の中から「企業名」と「URL」を抽出
    progress_bar = st.progress(0)
    for i, link in enumerate(article_links):
        try:
            res = requests.get(link, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 本文エリアを取得
            content = soup.find("div", class_="entry-content")
            if content:
                for a in content.find_all("a"):
                    url = a.get("href", "")
                    name = a.get_text(strip=True)
                    
                    # 企業サイトのリンクを判定する条件
                    if url.startswith("http") and "cloudmeets.jp" not in url and name:
                        # 不要なナビゲーションリンクを除外
                        if "弾はこちら" not in name and "専用フォーム" not in name:
                            all_data.append({"企業名": name, "URL": url})
        except:
            continue
        
        progress_bar.progress((i + 1) / len(article_links))
        time.sleep(0.3) # サーバーへの優しさ

    # 最終的なリストを作成
    result_df = pd.DataFrame(all_data).drop_duplicates()
    return result_df

# --- メイン画面レイアウト ---
st.title("🚀 SES営業リスト作成ツール")
st.markdown("""
CloudMeetsの「SES営業リスト」記事から企業名とURLを自動で収集します。  
**注意:** サーバーに負荷をかけないよう、ゆっくり取得します。
""")

if st.button("全38弾からデータを取得する"):
    df = get_ses_list()
    
    if not df.empty:
        st.success(f"完了！ {len(df)} 件の企業をリストアップしました。")
        
        # プレビュー表示
        st.dataframe(df, use_container_width=True)
        
        # ダウンロード準備
        csv = df.to_csv(index=False).encode('utf_8_sig')
        st.download_button(
            label="CSVファイルを保存する",
            data=csv,
            file_name="ses_company_list.csv",
            mime="text/csv"
        )
    else:
        st.error("データを取得できませんでした。")

import streamlit as st
from firebase_admin import firestore
from datetime import datetime, timedelta
import pandas as pd

# Firestoreの初期化
db = firestore.client()

# 日付範囲をdatetime型に変換
def convert_str_to_datetime(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d')

# Firestoreから全てのパフォーマンスデータを取得し、該当しないデータに0を設定する
def fetch_all_performance(user_id, display_name, start_date, end_date):
    # 日付範囲内でのデフォルト値を設定
    data = {
        'UID': user_id,
        'Display Name': display_name,
        'Feed Run': {date_str.strftime('%Y/%m/%d'): 0 for date_str in pd.date_range(start_date, end_date)},
        'Reel Run': {date_str.strftime('%Y/%m/%d'): 0 for date_str in pd.date_range(start_date, end_date)},
        'Feed Theme Run': {date_str.strftime('%Y/%m/%d'): 0 for date_str in pd.date_range(start_date, end_date)},
        'Reel Theme Run': {date_str.strftime('%Y/%m/%d'): 0 for date_str in pd.date_range(start_date, end_date)},
        'Data Analysis Run': {date_str.strftime('%Y/%m/%d'): 0 for date_str in pd.date_range(start_date, end_date)}
    }
    performance_ref = db.collection('users').document(user_id).collection('performance')

    # 全ての performance ドキュメントを取得
    performance_docs = performance_ref.stream()

    for doc in performance_docs:
        doc_id = doc.id
        performance_data = doc.to_dict()
        try:
            date_obj = convert_str_to_datetime(doc_id)
            date_str = date_obj.strftime('%Y/%m/%d')

            # 各種ラン数を更新
            data['Feed Run'][date_str] = performance_data.get('feed_run', 0)
            data['Reel Run'][date_str] = performance_data.get('reel_run', 0)
            data['Feed Theme Run'][date_str] = performance_data.get('feed_theme_run', 0)
            data['Reel Theme Run'][date_str] = performance_data.get('reel_theme_run', 0)
            data['Data Analysis Run'][date_str] = performance_data.get('data_analysis_run', 0)

        except ValueError:
            # 日付に変換できないドキュメントIDはスキップ
            pass

    return data

# 全てのユーザーのパフォーマンスデータを取得し、日付ごとのデータをまとめる
def get_all_users_run_data(start_date, end_date):
    users_ref = db.collection('users')
    users_docs = users_ref.stream()

    all_data = []
    for user_doc in users_docs:
        user_id = user_doc.id
        display_name = user_doc.to_dict().get('display_name', 'Unknown User')

        # すべてのパフォーマンスデータを取得
        user_data = fetch_all_performance(user_id, display_name, start_date, end_date)
        all_data.append(user_data)

    return all_data

# 表示用のDataFrameを作成
def prepare_dataframe_for_display(run_data, date_range):
    rows = []

    for user_data in run_data:
        # 各Run Typeごとに1行にまとめる
        for run_type in ['Feed Run', 'Reel Run', 'Feed Theme Run', 'Reel Theme Run', 'Data Analysis Run']:
            row = {
                'UID': user_data['UID'],
                'Display Name': user_data['Display Name'],
                'Run Type': run_type
            }

            # 各日付のデータを取得して、日付ごとのデータをカラムに追加
            for date_str in date_range:
                row[date_str] = user_data[run_type][date_str]

            rows.append(row)

    return pd.DataFrame(rows)

# Streamlit UI
st.set_page_config(page_title="Run Activity Dashboard", layout="wide")
st.title("Run Activity Dashboard")

# サイドバーで日付選択とSubmitボタン
with st.sidebar:
    st.title("フィルター")
    start_date = st.date_input("開始日", value=datetime.now().date() - timedelta(days=1))
    end_date = st.date_input("終了日", value=datetime.now().date())

    # 日付範囲をリスト化
    date_range = pd.date_range(start=start_date, end=end_date).strftime('%Y/%m/%d').tolist()

    # Submitボタン
    submit_button = st.button("データを取得")

# Submitボタンが押されたときに実行
if submit_button:
    run_data = get_all_users_run_data(start_date, end_date)

    if not run_data:
        st.warning("指定された日付範囲内にデータが見つかりませんでした。")
    else:
        # DataFrameを準備
        run_data_df = prepare_dataframe_for_display(run_data, date_range)

        # DataFrameを表示
        st.dataframe(run_data_df)

        # CSVダウンロード機能
        def convert_df(df):
            return df.to_csv().encode('utf-8')

        csv = convert_df(run_data_df)
        st.download_button(
            label="データをCSVとしてダウンロード",
            data=csv,
            file_name='run_data.csv',
            mime='text/csv',
        )

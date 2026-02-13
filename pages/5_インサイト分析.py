import streamlit as st
import pandas as pd
import numpy as np
from application.performance_service import PerformanceService
from application.insight_service import InsightService
from application.prompt_service import PromptService
from domain.insight import Insight
import traceback
from datetime import datetime, timedelta
import pytz
import anthropic
import io


env = st.secrets.get("ENV", "")

def add_insight_sidebar():
    with st.sidebar.form("new_insight_form"):
        st.header("投稿データを追加")
        post_url = st.text_input("投稿URL")
        plot = st.text_area("プロット")
        save_count = st.number_input("保存数", min_value=0, step=1)
        like_count = st.number_input("いいね数", min_value=0, step=1)
        reach_count = st.number_input("リーチ数", min_value=0, step=1)
        new_reach_count = st.number_input("/フォロワー以外リーチ%", min_value=0, step=1)
        followers_reach_count = st.number_input("/フォロワーリーチ%", min_value=0, step=1)
        posted_at = st.date_input("投稿日")

        submitted = st.form_submit_button("保存")
        if submitted:
            service = InsightService()
            user_id = st.session_state.get('user_info', {}).get('localId')
            posted_at = datetime.combine(posted_at, datetime.min.time())
            new_insight = Insight(
                user_id=user_id,
                post_url=post_url,
                plot=plot,
                save_count=save_count,
                like_count=like_count,
                reach_count=reach_count,
                new_reach_count=new_reach_count,
                followers_reach_count=followers_reach_count,
                posted_at=posted_at,
                created_at=datetime.now()
            )
            result = service.create_new_insight(new_insight)
            if result["status"] == "success":
                st.success("新しい投稿データが追加されました")
                st.session_state['show_add_form'] = False
                st.experimental_rerun()
            else:
                st.error("投稿データの追加に失敗しました")

def edit_insight_sidebar():
    service = InsightService()
    user_id = st.session_state.get('user_info', {}).get('localId')
    insights = service.get_insights_by_user(user_id)
    insights_df = pd.DataFrame([insight.dict() for insight in insights])

    post_id = st.sidebar.selectbox("編集する投稿を選択", options=insights_df['post_id'].tolist())
    insight_to_edit = insights_df[insights_df['post_id'] == post_id].iloc[0]

    with st.sidebar.form("edit_insight_form"):
        st.header("投稿データを編集")
        post_url = st.text_input("Post URL", value=insight_to_edit['post_url'])
        plot = st.text_area("Plot", value=insight_to_edit['plot'])
        save_count = st.number_input("Save Count", value=insight_to_edit['save_count'], min_value=0, step=1)
        like_count = st.number_input("Like Count", value=insight_to_edit['like_count'], min_value=0, step=1)
        reach_count = st.number_input("Reach Count", value=insight_to_edit['reach_count'], min_value=0, step=1)
        new_reach_count = st.number_input("New Reach Count", value=insight_to_edit['new_reach_count'], min_value=0, step=1)
        followers_reach_count = st.number_input("Followers Reach Count", value=insight_to_edit['followers_reach_count'], min_value=0, step=1)
        posted_at = st.date_input("Posted At", value=pd.to_datetime(insight_to_edit['posted_at']).date())

        submitted = st.form_submit_button("更新")
        if submitted:
            updated_insight = Insight(
                post_id=post_id,
                user_id=user_id,
                post_url=post_url,
                plot=plot,
                save_count=save_count,
                like_count=like_count,
                reach_count=reach_count,
                new_reach_count=new_reach_count,
                followers_reach_count=followers_reach_count,
                posted_at=posted_at,
                created_at=insight_to_edit['created_at']
            )
            result = service.update_insight(updated_insight)
            if result["status"] == "success":
                st.success(f"Post {post_id} updated successfully")
                st.session_state['show_edit_form'] = False
                st.experimental_rerun()
            else:
                st.error(f"Failed to update post {post_id}")

def get_ai_analysis(api_key, prompt, user_message):
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        temperature=0.7,
        system=prompt,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )
    generated_text = message.content[0].text.replace('\\n', '\n')
    return generated_text

def dataframe_to_string(df):
    # DataFrameをCSV形式の文字列に変換
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()

def main():
    st.markdown("## インサイト分析")
    st.markdown("---")  # ページタイトルの下に区切り線を追加

    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.warning("ログインしていません。先にログインしてください。")
        return

    user_id = st.session_state.get('user_info', {}).get('localId')
    if not user_id:
        st.error("ユーザー情報が見つかりません。再度ログインしてください。")
        return

    service = InsightService()
    performance_service = PerformanceService(user_id)

    if env == "develop":
        st.sidebar.write("デバッグ情報:")
        st.sidebar.write(f"ログイン状態: {st.session_state.get('logged_in', False)}")
        st.sidebar.write(f"ユーザーID: {user_id}")


    try:
        insights = service.get_insights_by_user(user_id)
        st.sidebar.write(f"取得したインサイト数: {len(insights)}")

        if insights:
            insights_df = pd.DataFrame([insight.dict() for insight in insights])
            insights_df['posted_at'] = pd.to_datetime(insights_df['posted_at'])

            # サマリーセクション
            st.markdown("### サマリ")

            # 日付範囲選択
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("開始日", value=datetime.now().date() - timedelta(days=6))
            with col2:
                end_date = st.date_input("終了日", value=datetime.now().date())

            # 選択された期間のデータをフィルタリング
            current_mask = (insights_df['posted_at'].dt.date >= start_date) & (insights_df['posted_at'].dt.date <= end_date)
            current_df = insights_df.loc[current_mask]

            # 過去期間の計算
            period_length = (end_date - start_date).days + 1
            past_end_date = start_date - timedelta(days=1)
            past_start_date = past_end_date - timedelta(days=period_length-1)
            past_mask = (insights_df['posted_at'].dt.date >= past_start_date) & (insights_df['posted_at'].dt.date <= past_end_date)
            past_df = insights_df.loc[past_mask]

            # サマリーデータの計算
            metrics = ["保存数", "リーチ数", "保存率", "フォロワーリーチ数", "新規リーチ数", "ホーム率", "いいね数"]
            current_metrics = {
                "保存数": current_df['save_count'].sum(),
                "リーチ数": current_df['reach_count'].sum(),
                "保存率": np.round(current_df['save_count'].sum() / current_df['reach_count'].sum() * 100, 2) if current_df['reach_count'].sum() > 0 else 0,
                "フォロワーリーチ数": current_df['followers_reach_count'].sum(),
                "新規リーチ数": current_df['new_reach_count'].sum(),
                "ホーム率": 0,  # この値の計算方法が不明なため、0としています
                "いいね数": current_df['like_count'].sum(),
            }
            past_metrics = {
                "保存数": past_df['save_count'].sum(),
                "リーチ数": past_df['reach_count'].sum(),
                "保存率": np.round(past_df['save_count'].sum() / past_df['reach_count'].sum() * 100, 2) if past_df['reach_count'].sum() > 0 else 0,
                "フォロワーリーチ数": past_df['followers_reach_count'].sum(),
                "新規リーチ数": past_df['new_reach_count'].sum(),
                "ホーム率": 0,
                "いいね数": past_df['like_count'].sum(),
            }

            # サマリーの表示（1行7列に、枠線付き）
            cols = st.columns(7)
            for col, metric in zip(cols, metrics):
                with col:
                    with st.container(border=True):
                        delta = current_metrics[metric] - past_metrics[metric]
                        st.metric(label=metric, value=int(current_metrics[metric]), delta=int(delta))

            st.sidebar.write("データフレーム作成成功")

            # 表の上に「投稿データ」と記載
            st.markdown("### 投稿データ")

            # カラムの順序を指定
            column_order = ['post_id', 'post_url', 'plot', 'save_count', 'like_count', 'reach_count', 'new_reach_count', 'followers_reach_count', 'posted_at']
            insights_df = insights_df[column_order]

            st.dataframe(
                insights_df,
                column_config={
                    "post_id": st.column_config.TextColumn("投稿ID"),
                    "post_url": st.column_config.TextColumn("投稿URL"),
                    "plot": st.column_config.TextColumn("プロット"),
                    "save_count": st.column_config.NumberColumn("保存数"),
                    "like_count": st.column_config.NumberColumn("いいね数"),
                    "reach_count": st.column_config.NumberColumn("リーチ数"),
                    "new_reach_count": st.column_config.NumberColumn("/新規リーチ%"),
                    "followers_reach_count": st.column_config.NumberColumn("/フォロワーリーチ%"),
                    "posted_at": st.column_config.DatetimeColumn("投稿日時", format="YYYY-MM-DD HH:mm:ss"),
                },
                hide_index=True,
            )
        else:
            st.info("インサイトデータがありません。下のボタンからデータを追加してください。")

        # 区切り線とスペーサーを追加
        st.markdown("---")
        st.markdown("<br>", unsafe_allow_html=True)

        # データ操作セクション
        st.markdown("### データ操作")

        if 'show_add_form' not in st.session_state:
            st.session_state['show_add_form'] = False
        if 'show_edit_form' not in st.session_state:
            st.session_state['show_edit_form'] = False

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<br>", unsafe_allow_html=True)  # 空白を追加して高さを合わせる
            if st.button("投稿データを追加", use_container_width=True):
                st.session_state['show_add_form'] = not st.session_state['show_add_form']
                st.session_state['show_edit_form'] = False
            if st.button("投稿データを編集", use_container_width=True):
                st.session_state['show_edit_form'] = not st.session_state['show_edit_form']
                st.session_state['show_add_form'] = False

        if st.session_state['show_add_form']:
            add_insight_sidebar()
        if st.session_state['show_edit_form']:
            edit_insight_sidebar()

        with col2:
            if insights:
                post_id_to_delete = st.selectbox("削除する投稿を選択", options=insights_df['post_id'].tolist())
                if st.button("削除", use_container_width=True):
                    result = service.delete_insight(user_id, post_id_to_delete)
                    if result["status"] == "success":
                        st.success(f"投稿 {post_id_to_delete} が正常に削除されました")
                        st.experimental_rerun()
                    else:
                        st.error(f"投稿 {post_id_to_delete} の削除に失敗しました")
            else:
                st.info("削除するデータがありません。先にデータを追加してください。")

        # 区切り線を追加
        st.markdown("---")

        # AI分析セクション
        st.markdown("### AI分析")
        st.write("振り返りと改善提案")

        # プロンプトサービスのインスタンス化
        prompt_service = PromptService()

        # 分析開始ボタン
        if st.button("分析を開始する", key="start_analysis_button"):
            with st.spinner('AI分析を実行中...'):
                # ユーザーのinsight_analysisプロンプトを取得
                prompt_result = prompt_service.read_prompt(user_id, 'insight_analysis')
                if prompt_result['status'] == 'success':
                    system_prompt = prompt_result['data']['text']
                else:
                    # デフォルトのプロンプトを使用
                    system_prompt = "あなたはインサイトデータ分析の専門家です。提供されたデータを分析し、詳細な洞察と改善提案を提供してください。"

                # ここでインサイトデータをAI分析用に整形
                user_message = f"CSVデータ:\n{dataframe_to_string(insights_df)}\n\nユーザーの入力: インサイトデータの分析をお願いします。"

                # AI分析の実行
                ai_analysis = get_ai_analysis(st.secrets["ANTHROPIC_API_KEY"], system_prompt, user_message)

                # 分析結果をセッション状態に保存
                st.session_state.analysis_result = ai_analysis

                today = datetime.now(pytz.timezone('Asia/Tokyo')).date()
                performance_service.log_data_analysis_run(today)

        # 分析結果の表示
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = "分析結果がここに表示されます。"

        st.subheader("AI分析結果")
        st.markdown(st.session_state.analysis_result)

    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        st.sidebar.write("エラーの詳細:")
        st.sidebar.code(traceback.format_exc())

if __name__ == "__main__":
    main()

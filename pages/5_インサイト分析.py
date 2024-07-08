# pages/5_インサイト分析.py

import streamlit as st
import pandas as pd
import numpy as np
from application.insight_service import InsightService
from domain.insight import Insight
import traceback
from datetime import datetime, timedelta

@st.experimental_dialog("投稿データを追加", width="large")
def add_insight_dialog():
    with st.form("new_insight_form"):
        post_url = st.text_input("投稿URL")
        plot = st.text_area("プロット")
        save_count = st.number_input("保存数", min_value=0, step=1)
        like_count = st.number_input("いいね数", min_value=0, step=1)
        reach_count = st.number_input("リーチ数", min_value=0, step=1)
        new_reach_count = st.number_input("新規リーチ数", min_value=0, step=1)
        followers_reach_count = st.number_input("フォロワーリーチ数", min_value=0, step=1)
        posted_at = st.date_input("投稿日")

        submitted = st.form_submit_button("保存")
        if submitted:
            service = InsightService()
            user_id = st.session_state.get('user_info', {}).get('localId')
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
                st.rerun()
            else:
                st.error("投稿データの追加に失敗しました")

@st.experimental_dialog("投稿データを編集", width="large")
def edit_insight_dialog():
    service = InsightService()
    user_id = st.session_state.get('user_info', {}).get('localId')
    insights = service.get_insights_by_user(user_id)
    insights_df = pd.DataFrame([insight.dict() for insight in insights])
    
    post_id = st.selectbox("編集する投稿を選択", options=insights_df['post_id'].tolist())
    insight_to_edit = insights_df[insights_df['post_id'] == post_id].iloc[0]

    with st.form("edit_insight_form"):
        post_url = st.text_input("投稿URL", value=insight_to_edit['post_url'])
        plot = st.text_area("プロット", value=insight_to_edit['plot'])
        save_count = st.number_input("保存数", value=insight_to_edit['save_count'], min_value=0, step=1)
        like_count = st.number_input("いいね数", value=insight_to_edit['like_count'], min_value=0, step=1)
        reach_count = st.number_input("リーチ数", value=insight_to_edit['reach_count'], min_value=0, step=1)
        new_reach_count = st.number_input("新規リーチ数", value=insight_to_edit['new_reach_count'], min_value=0, step=1)
        followers_reach_count = st.number_input("フォロワーリーチ数", value=insight_to_edit['followers_reach_count'], min_value=0, step=1)
        posted_at = st.date_input("投稿日", value=pd.to_datetime(insight_to_edit['posted_at']).date())

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
                st.success(f"投稿 {post_id} が正常に更新されました")
                st.rerun()
            else:
                st.error(f"投稿 {post_id} の更新に失敗しました")

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

            # 過去比較期間の計算
            date_diff = (end_date - start_date).days
            past_end_date = start_date - timedelta(days=1)
            past_start_date = past_end_date - timedelta(days=date_diff)

            # 過去比較期間のデータをフィルタリング
            past_mask = (insights_df['posted_at'].dt.date >= past_start_date) & (insights_df['posted_at'].dt.date <= past_end_date)
            past_df = insights_df.loc[past_mask]

            # サマリーデータの計算
            metrics = ['save_count', 'reach_count', 'followers_reach_count', 'new_reach_count', 'like_count']
            current_metrics = {metric: current_df[metric].sum() for metric in metrics}
            past_metrics = {metric: past_df[metric].sum() for metric in metrics}

            # 保存率の計算
            current_metrics['save_rate'] = (current_metrics['save_count'] / current_metrics['reach_count'] * 100) if current_metrics['reach_count'] > 0 else 0
            past_metrics['save_rate'] = (past_metrics['save_count'] / past_metrics['reach_count'] * 100) if past_metrics['reach_count'] > 0 else 0

            # 差分の計算
            metric_changes = {metric: current_metrics[metric] - past_metrics[metric] for metric in metrics + ['save_rate']}

            # サマリーの表示（1行7列に、枠線付き）
            cols = st.columns(7)
            display_metrics = [
                ("保存数", current_metrics['save_count'], metric_changes['save_count']),
                ("リーチ数", current_metrics['reach_count'], metric_changes['reach_count']),
                ("保存率", f"{current_metrics['save_rate']:.2f}%", f"{metric_changes['save_rate']:.2f}"),
                ("フォロワーリーチ数", current_metrics['followers_reach_count'], metric_changes['followers_reach_count']),
                ("新規リーチ数", current_metrics['new_reach_count'], metric_changes['new_reach_count']),
                ("ホーム率", "0%", "0"),  # この値の計算方法が不明なため、0としています
                ("いいね数", current_metrics['like_count'], metric_changes['like_count'])
            ]
            
            for col, (label, value, change) in zip(cols, display_metrics):
                with col:
                    with st.container(border=True):
                        st.metric(label=label, value=value, delta=change)

            st.sidebar.write("データフレーム作成成功")
            st.sidebar.write(f"データフレームの行数: {len(insights_df)}")

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
                    "new_reach_count": st.column_config.NumberColumn("新規リーチ数"),
                    "followers_reach_count": st.column_config.NumberColumn("フォロワーリーチ数"),
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

        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<br>", unsafe_allow_html=True)  # 空白を追加して高さを合わせる
            if st.button("投稿データを追加", use_container_width=True):
                add_insight_dialog()
            if st.button("投稿データを編集", use_container_width=True):
                edit_insight_dialog()

        with col2:
            if insights:
                post_id_to_delete = st.selectbox("削除する投稿を選択", options=insights_df['post_id'].tolist())
                if st.button("削除", use_container_width=True):
                    result = service.delete_insight(user_id, post_id_to_delete)
                    if result["status"] == "success":
                        st.success(f"投稿 {post_id_to_delete} が正常に削除されました")
                        st.rerun()
                    else:
                        st.error(f"投稿 {post_id_to_delete} の削除に失敗しました")
            else:
                st.info("削除するデータがありません。先にデータを追加してください。")

    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        st.sidebar.write("エラーの詳細:")
        st.sidebar.code(traceback.format_exc())

if __name__ == "__main__":
    main()

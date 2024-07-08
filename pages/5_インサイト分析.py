# pages/5_インサイト分析.py

import streamlit as st
import pandas as pd
from application.insight_service import InsightService
from domain.insight import Insight
import traceback
from datetime import datetime

@st.experimental_dialog("投稿データを追加", width="large")
def add_insight_dialog():
    with st.form("new_insight_form"):
        post_url = st.text_input("Post URL")
        plot = st.text_area("Plot")
        save_count = st.number_input("Save Count", min_value=0, step=1)
        like_count = st.number_input("Like Count", min_value=0, step=1)
        reach_count = st.number_input("Reach Count", min_value=0, step=1)
        new_reach_count = st.number_input("New Reach Count", min_value=0, step=1)
        followers_reach_count = st.number_input("Followers Reach Count", min_value=0, step=1)
        posted_at = st.date_input("Posted At")

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
                st.session_state.need_update = True
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
                st.session_state.need_update = True
                st.rerun()
            else:
                st.error(f"Failed to update post {post_id}")

def main():
    st.title("インサイトデータ表示")

    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.warning("ログインしていません。先にログインしてください。")
        return

    user_id = st.session_state.get('user_info', {}).get('localId')
    if not user_id:
        st.error("ユーザー情報が見つかりません。再度ログインしてください。")
        return

    service = InsightService()

    try:
        insights = service.get_insights_by_user(user_id)
        
        if insights:
            insights_df = pd.DataFrame([insight.dict() for insight in insights])
            insights_df['posted_at'] = pd.to_datetime(insights_df['posted_at'])

            # サマリーセクション
            st.header("サマリ")

            # 日付範囲選択
            col1, col2 = st.columns(2)
            with col1:
                end_date = st.date_input("終了日", value=datetime.now().date())
            with col2:
                start_date = st.date_input("開始日", value=end_date - timedelta(days=6))

            # 選択された期間のデータをフィルタリング
            mask = (insights_df['posted_at'].dt.date >= start_date) & (insights_df['posted_at'].dt.date <= end_date)
            filtered_df = insights_df.loc[mask]

            # サマリーデータの計算
            summary_data = {
                "保存数": filtered_df['save_count'].sum(),
                "リーチ数": filtered_df['reach_count'].sum(),
                "保存率": np.round(filtered_df['save_count'].sum() / filtered_df['reach_count'].sum() * 100, 2) if filtered_df['reach_count'].sum() > 0 else 0,
                "フォロワーリーチ数": filtered_df['followers_reach_count'].sum(),
                "新規リーチ数": filtered_df['new_reach_count'].sum(),
                "ホーム率": 0,  # この値の計算方法が不明なため、0としています
                "いいね数": filtered_df['like_count'].sum(),
                "フォロワー数": 0,  # この値はデータフレームに含まれていないため、0としています
            }

            # サマリーの表示
            col1, col2, col3, col4 = st.columns(4)
            col5, col6, col7, col8 = st.columns(4)

            with col1:
                st.metric("保存数", f"{summary_data['保存数']:,}")
            with col2:
                st.metric("リーチ数", f"{summary_data['リーチ数']:,}")
            with col3:
                st.metric("保存率", f"{summary_data['保存率']}%")
            with col4:
                st.metric("フォロワーリーチ数", f"{summary_data['フォロワーリーチ数']:,}")
            with col5:
                st.metric("新規リーチ数", f"{summary_data['新規リーチ数']:,}")
            with col6:
                st.metric("ホーム率", f"{summary_data['ホーム率']}%")
            with col7:
                st.metric("いいね数", f"{summary_data['いいね数']:,}")
            with col8:
                st.metric("フォロワー数", f"{summary_data['フォロワー数']:,}")

            # 既存のデータフレーム表示コードはそのままです

    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        st.sidebar.write("エラーの詳細:")
        st.sidebar.code(traceback.format_exc())

if __name__ == "__main__":
    main()

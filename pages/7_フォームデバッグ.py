import streamlit as st

def add_insight_sidebar():
    print("add_insight_sidebar")
    with st.sidebar.form("new_insight_form", clear_on_submit=True):
        post_url = st.text_input("投稿URL")
        plot = st.text_area("プロット")
        save_count = st.number_input("保存数", min_value=0, step=1)
        like_count = st.number_input("いいね数", min_value=0, step=1)
        reach_count = st.number_input("リーチ数", min_value=0, step=1)
        new_reach_count = st.number_input("新規リーチ数", min_value=0, step=1)
        followers_reach_count = st.number_input("フォロワーリーチ数", min_value=0, step=1)
        posted_at = st.date_input("投稿日")

        submitted_add = st.form_submit_button("保存")
        if submitted_add:
            st.write("slider", post_url, "checkbox", plot)

with st.sidebar.form("my_form"):
    # st.write("Inside the form")
    # slider_val = st.slider("Form slider")
    # checkbox_val = st.checkbox("Form checkbox")

    # # Every form must have a submit button.
    # submitted = st.form_submit_button("Submit")
    # if submitted:
    #     st.write("slider", slider_val, "checkbox", checkbox_val)
    add_insight_sidebar()
st.write("Outside the form")
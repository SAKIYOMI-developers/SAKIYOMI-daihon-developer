import streamlit as st
import utils.scraping_helper as sh
import time
import pytz
from datetime import datetime, timedelta
from utils.firebase_auth import sign_in, get_user_info
from application.user_service import UserService
from application.user_index_service import UserIndexService
from application.prompt_service import PromptService
from application.performance_service import PerformanceService
from utils.example_prompt import system_prompt_example, system_prompt_title_reccomend_example

user_service = UserService()
user_index_service = UserIndexService()
prompt_service = PromptService()
env = st.secrets.get("ENV", "")

def main():
    st.set_page_config(
        page_icon='🤖',
        layout='wide',
    )

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # クエリパラメータからIDトークンを取得してログイン状態を維持
    query_params = st.experimental_get_query_params()
    plan = query_params.get('plan', [''])[0]

    if 'id_token' in query_params and not st.session_state['logged_in']:
        id_token = query_params['id_token'][0]
        user_info_response = get_user_info(id_token)
        if user_info_response:
            st.session_state['logged_in'] = True
            st.session_state['id_token'] = id_token
            st.session_state['user_info'] = user_info_response['users'][0]

            # プロンプトの取得
            list_prompts = prompt_service.list_prompts(st.session_state['user_info']['localId'])

            has_feed = any(prompt['type'] == 'feed_post' for prompt in list_prompts) and any(prompt['type'] == 'feed_theme' for prompt in list_prompts)
            has_reel = any(prompt['type'] == 'reel_post' for prompt in list_prompts) and any(prompt['type'] == 'reel_theme' for prompt in list_prompts)

            if has_feed and not has_reel:
                plan = 'feed'
            elif not has_feed and has_reel:
                plan = 'reel'
            elif has_feed and has_reel and not plan:
                plan = 'feed'

            if plan:
                st.experimental_set_query_params(id_token=id_token, plan=plan)

            if plan == 'feed':
                prompt_post_feed = prompt_service.read_prompt(st.session_state['user_info']['localId'], type='feed_post')
                prompt_theme_feed = prompt_service.read_prompt(st.session_state['user_info']['localId'], type='feed_theme')
                st.session_state['prompt'] = {
                    'system_prompt': prompt_post_feed['data']['text'] if prompt_post_feed['status'] == 'success' else system_prompt_example,
                    'system_prompt_title_reccomend': prompt_theme_feed['data']['text'] if prompt_theme_feed['status'] == 'success' else system_prompt_title_reccomend_example
                }
                # ユーザーインデックスの取得
                user_index = user_index_service.read_user_index(st.session_state['user_info']['localId'], 'feed')
                if user_index['status'] == 'success':
                    st.session_state['user_index'] = user_index['data']
                else:
                    st.session_state['user_index'] = None

            elif plan == 'reel':
                prompt_post_reel = prompt_service.read_prompt(st.session_state['user_info']['localId'], type='reel_post')
                prompt_theme_reel = prompt_service.read_prompt(st.session_state['user_info']['localId'], type='reel_theme')
                st.session_state['prompt'] = {
                    'system_prompt': prompt_post_reel['data']['text'] if prompt_post_reel['status'] == 'success' else system_prompt_example,
                    'system_prompt_title_reccomend': prompt_theme_reel['data']['text'] if prompt_theme_reel['status'] == 'success' else system_prompt_title_reccomend_example
                }
                # ユーザーインデックスの取得
                user_index = user_index_service.read_user_index(st.session_state['user_info']['localId'], 'reel')
                if user_index['status'] == 'success':
                    st.session_state['user_index'] = user_index['data']
                else:
                    st.session_state['user_index'] = None

    if not st.session_state['logged_in']:
        st.markdown("# SAKIYOMI Intelligence")
        with st.container():
            st.empty()
            email = st.text_input('Email')
            password = st.text_input('Password', type='password')
            login_button = st.button('ログイン')

            if login_button:
                auth_response = user_service.login_user(email, password)
                if auth_response:
                    st.session_state['logged_in'] = True
                    st.session_state['id_token'] = auth_response['idToken']
                    user_info_response = get_user_info(auth_response['idToken'])
                    if user_info_response:
                        st.session_state['user_info'] = user_info_response['users'][0]
                        st.experimental_set_query_params(id_token=auth_response['idToken'])
                        st.success('ログインに成功しました')
                        st.write('<meta http-equiv="refresh" content="0">', unsafe_allow_html=True)
                    else:
                        st.error('ユーザー情報の取得に失敗しました')
                else:
                    st.error('ログインに失敗しました')

        return

    st.sidebar.title('ユーザー情報')

    if 'has_feed' not in locals():
        list_prompts = prompt_service.list_prompts(st.session_state['user_info']['localId'])
        has_feed = any(prompt['type'] == 'feed_post' for prompt in list_prompts) and any(prompt['type'] == 'feed_theme' for prompt in list_prompts)
        has_reel = any(prompt['type'] == 'reel_post' for prompt in list_prompts) and any(prompt['type'] == 'reel_theme' for prompt in list_prompts)

    if plan == 'feed':
        st.title('SAKIYOMI Intelligence - フィード')
    elif plan == 'reel':
        st.title('SAKIYOMI Intelligence - リール')
    else:
        st.title('SAKIYOMI Intelligence')

    if has_feed and has_reel:
        st.sidebar.write("プラン : フィード&リール")
    elif has_feed and not has_reel:
        st.sidebar.write("プラン : フィードのみ")
    elif not has_feed and has_reel:
        st.sidebar.write("プラン : リールのみ")
    else:
        st.sidebar.write("フィードプランにもリールプランにも入っていないため、どちらかのプランに入ってください。")
        return

    if has_feed and has_reel:
        options = {"フィード": "feed", "リール": "reel"}
        selected_label = st.sidebar.radio("投稿タイプを選択", list(options.keys()), index=0 if plan == 'feed' else 1)
        selected_plan = options[selected_label]

        if selected_plan != plan:
            st.experimental_set_query_params(id_token=query_params['id_token'][0], plan=selected_plan)
            st.write('<meta http-equiv="refresh" content="0">', unsafe_allow_html=True)
            return

    elif not has_feed and not has_reel:
        st.sidebar.write("フィードかリールのプランに登録してください")
        return

    if st.sidebar.button('ログアウト'):
        st.session_state['logged_in'] = False
        st.session_state.pop('id_token', None)
        st.session_state.pop('user_info', None)
        st.session_state.pop('user_index', None)
        st.experimental_set_query_params()
        st.sidebar.success('ログアウトしました')
        st.write('<meta http-equiv="refresh" content="0">', unsafe_allow_html=True)
        return

    if 'user_info' in st.session_state:
        if env == "develop":
            st.sidebar.write(f"User ID: {st.session_state['user_info']['email']}")

    if 'user_index' in st.session_state and st.session_state['user_index']:
        if env == "develop":
            st.sidebar.write(f"Index Name: {st.session_state['user_index']['index_name']}")
            st.sidebar.write(f"Langsmith Project Name: {st.session_state['user_index']['langsmith_project_name']}")
        index_name = st.session_state['user_index']['index_name']
        pinecone_api_key = st.session_state['user_index']['pinecone_api_key']
        langsmith_project_name = st.session_state['user_index']['langsmith_project_name']
        try:
            index = sh.initialize_pinecone(index_name, pinecone_api_key)
        except Exception as e:
            st.sidebar.write("インデックスの初期化に失敗しました")
            st.sidebar.write("エラーメッセージ: ", e)
            index_name = None
            return
    else:
        st.sidebar.write("インデックスがありません")
        st.sidebar.write("新しいインデックスを作成してください")
        index_name = None

    if 'prompt' in st.session_state:
        if env == "develop":
            st.sidebar.write("投稿プロンプト:")
            st.sidebar.code(st.session_state['prompt']['system_prompt'], language='markdown')
            st.sidebar.write("タイトル提案プロンプト:")
            st.sidebar.code(st.session_state['prompt']['system_prompt_title_reccomend'], language='markdown')
    else:
        st.sidebar.write("プロンプトがありません")
        st.sidebar.write("新しいプロンプトを作成してください")
        return

    tab1, tab2, tab3 = st.tabs(["プロット生成", "データ登録", "テーマ提案"])

    performance_service = PerformanceService(st.session_state['user_info']['localId'])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            user_input = st.text_area("生成指示 : 作りたいプロットのイメージを入力", value="""以下の内容で台本を書いてください。\nテーマ：\n\nターゲット：\n\nその他の指示：""", height=300)
            url = st.text_input("参考URL")
            selected_llm = st.radio("LLMの選択", ("GPT-4o", "Claude3"))
            submit_button = st.button('送信')

        if submit_button:
            with st.spinner('送信中...'):
                if sh.is_ng_url(url):
                    st.info("このURLは読み込めません。お手数をおかけしますが別のURLをお試し下さい。")
                    st.stop()
                else:
                    if 'last_url' not in st.session_state or (st.session_state['last_url'] != url or url == ""):
                        try:
                            sh.delete_all_data_in_namespace(index, "ns1")
                        except Exception:
                            pass

                        st.session_state['last_url'] = url
                        if url != "":
                            scraped_data = sh.scrape_url(url)
                            combined_text, metadata_list = sh.prepare_text_and_metadata(sh.extract_keys_from_json(scraped_data))
                            chunks = sh.split_text(combined_text)
                            embeddings = sh.make_chunks_embeddings(chunks)
                            sh.store_data_in_pinecone(index, embeddings, chunks, metadata_list, "ns1")
                            time.sleep(10)
                            st.success("ウェブサイトを読み込みました！")
                    else:
                        st.info("同じウェブサイトのデータを使用")

        with col2:
            if submit_button:
                with st.spinner('台本を生成中...'):
                    namespaces = ["ns1", "ns2", "ns3", "ns4", "ns5"]
                    response = sh.generate_response_with_llm_for_multiple_namespaces(index, user_input, namespaces, selected_llm, st.session_state['prompt']['system_prompt'], langsmith_project_name)
                    if response:
                        response_text = response.get('text')
                        st.session_state['response_text'] = response_text
                        if plan == 'feed':
                            today = datetime.now(pytz.timezone('Asia/Tokyo')).date()
                            performance_service.log_feed_run(today)
                        elif plan == 'reel':
                            today = datetime.now(pytz.timezone('Asia/Tokyo')).date()
                            performance_service.log_reel_run(today)
                    else:
                        st.session_state['response_text'] = "エラー: プロットを生成できませんでした。"

            displayed_value = st.session_state.get('response_text', "生成結果 : プロットが表示されます")
            st.text_area("生成結果", value=displayed_value, height=400)

    with tab2:
        st.header('データを登録')
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.subheader("URLの登録")
            url = st.text_input("登録URLを入力してください")
            register_button1 = st.button("URL登録")

            if register_button1:
                scraped_data = sh.scrape_url(url)
                combined_text, metadata_list = sh.prepare_text_and_metadata(sh.extract_keys_from_json(scraped_data))
                chunks = sh.split_text(combined_text)
                embeddings = sh.make_chunks_embeddings(chunks)
                sh.store_data_in_pinecone(index, embeddings, chunks, metadata_list, "ns2")
                st.success("データをPineconeに登録しました！")

            delete_all_button1 = st.button("URL全データ削除")

            if delete_all_button1:
                sh.delete_all_data_in_namespace(index, "ns2")
                st.success("全データが削除されました！")

        with col2:
            st.subheader("過去プロットの登録")
            pdf_file1 = st.file_uploader("PDFファイルをアップロード", type=["pdf"], key="pdf_file1")
            register_button2 = st.button("PDF登録")

            if register_button2 and pdf_file1 is not None:
                pdf_text = sh.extract_text_from_pdf(pdf_file1)
                chunks = sh.split_text(pdf_text)
                embeddings = sh.make_chunks_embeddings(chunks)
                sh.store_pdf_data_in_pinecone(index, embeddings, chunks, pdf_file1.name, "ns3")
                st.success("データをPineconeに登録しました！")

            delete_all_button2 = st.button("全データ削除")

            if delete_all_button2:
                sh.delete_all_data_in_namespace(index, "ns3")
                st.success("全データが削除されました！")

        with col3:
            st.subheader("競合データの登録")
            pdf_file2 = st.file_uploader("PDFファイルをアップロード", type=["pdf"], key="pdf_file2")
            register_button3 = st.button("PDF登録", key="register_button3")

            if register_button3 and pdf_file2 is not None:
                pdf_text = sh.extract_text_from_pdf(pdf_file2)
                chunks = sh.split_text(pdf_text)
                embeddings = sh.make_chunks_embeddings(chunks)
                sh.store_pdf_data_in_pinecone(index, embeddings, chunks, pdf_file2.name, "ns4")
                st.success("データをPineconeに登録しました！")

            delete_all_button3 = st.button("全データ削除", key="delete_all_3")

            if delete_all_button3:
                sh.delete_all_data_in_namespace(index, "ns4")
                st.success("全データが削除されました！")

        with col4:
            st.subheader("その他PDFの登録")
            pdf_file3 = st.file_uploader("PDFをアップロード", type=["pdf"], key="pdf_file3")
            register_button4 = st.button("PDF登録", key="register_button4")

            if register_button4 and pdf_file3 is not None:
                pdf_text = sh.extract_text_from_pdf(pdf_file3)
                chunks = sh.split_text(pdf_text)
                embeddings = sh.make_chunks_embeddings(chunks)
                sh.store_pdf_data_in_pinecone(index, embeddings, chunks, pdf_file3.name, "ns5")
                st.success("データをPineconeに登録しました！")

            delete_all_button4 = st.button("全データ削除", key="delete_all_4")

            if delete_all_button4:
                sh.delete_all_data_in_namespace(index, "ns5")
                st.success("全データが削除されました！")

    with tab3:
        st.header("投稿テーマ提案")
        col1, col2 = st.columns(2)
        with col1:
            with st.form("search_form"):
                user_query = st.text_area("作りたい投稿ジャンルのキーワードやイメージを入力して下さい。", height=50)
                selected_llm_title = st.radio("LLMの選択", ("GPT-4o", "Claude3"), key="radio_llm_selection_title")
                submit_button = st.form_submit_button("テーマ提案")

        with col2:
            if submit_button:
                with st.spinner('テーマ提案中...'):
                    if not user_query:
                        user_query = "*"
                    query_results = sh.perform_similarity_search(index, user_query, "ns4", top_k=10)
                    titles = sh.get_search_results_titles(query_results)
                    original_titles = sh.generate_new_titles(user_query, titles, selected_llm_title, st.session_state['prompt']['system_prompt_title_reccomend'])
                    st.session_state['reccomend_title'] = [f"- {title}" for title in original_titles.split('\n') if title.strip()]
                    if plan == 'feed':
                        today = datetime.now(pytz.timezone('Asia/Tokyo')).date()
                        performance_service.log_feed_theme_run(today)
                    elif plan == 'reel':
                        today = datetime.now(pytz.timezone('Asia/Tokyo')).date()
                        performance_service.log_reel_theme_run(today)
                display_titles = st.session_state.get('reccomend_title', "")
                st.text_area("生成されたタイトル案:", "\n".join(display_titles), height=500)

if __name__ == "__main__":
    main()

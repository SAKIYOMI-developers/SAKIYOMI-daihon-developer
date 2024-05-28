import streamlit as st
import utils.scraping_helper as sh
import time
from utils.firebase_auth import sign_in, get_user_info
from application.user_service import UserService
from application.user_index_service import UserIndexService
from application.prompt_service import PromptService
from utils.example_prompt import system_prompt_example, system_prompt_title_reccomend_example


user_service = UserService()
user_index_service = UserIndexService()
prompt_service = PromptService()


def main():

    st.set_page_config(
        page_icon='🤖',
        layout='wide',
    )

    st.title('SAKIYOMI 投稿作成AI')

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # クエリパラメータからIDトークンを取得してログイン状態を維持
    query_params = st.experimental_get_query_params()
    if 'id_token' in query_params and not st.session_state['logged_in']:
        id_token = query_params['id_token'][0]
        user_info_response = get_user_info(id_token)
        if user_info_response:
            st.session_state['logged_in'] = True
            st.session_state['id_token'] = id_token
            st.session_state['user_info'] = user_info_response['users'][0]

            # ユーザーインデックスの取得
            user_index = user_index_service.read_user_index(st.session_state['user_info']['localId'])
            if user_index['status'] == 'success':
                st.session_state['user_index'] = user_index['data']
            else:
                st.session_state['user_index'] = None

            # プロンプトの取得
            prompt_post = prompt_service.read_prompt(st.session_state['user_info']['localId'], type='post')
            prompt_title = prompt_service.read_prompt(st.session_state['user_info']['localId'], type='title')
            if prompt_post['status'] == 'success' and prompt_title['status'] == 'success':
                st.session_state['prompt'] = {
                    'system_prompt': prompt_post['data']['text'],
                    'system_prompt_title_reccomend': prompt_title['data']['text']
                }
            else:
                st.session_state['prompt'] = {
                    'system_prompt': system_prompt_example,
                    'system_prompt_title_reccomend': system_prompt_title_reccomend_example
                }

    if not st.session_state['logged_in']:
        st.sidebar.title('ログイン')
        email = st.sidebar.text_input('Email')
        password = st.sidebar.text_input('Password', type='password')
        login_button = st.sidebar.button('ログイン')

        if login_button:
            # auth_response = sign_in(email, password)
            auth_response = user_service.login_user(email, password)
            print(auth_response)
            if auth_response:
                st.session_state['logged_in'] = True
                st.session_state['id_token'] = auth_response['idToken']
                user_info_response = get_user_info(auth_response['idToken'])
                if user_info_response:
                    st.session_state['user_info'] = user_info_response['users'][0]
                    user_index = user_index_service.read_user_index(st.session_state['user_info']['localId'])
                    if user_index['status'] == 'success':
                        st.session_state['user_index'] = user_index['data']
                    else:
                        st.session_state['user_index'] = None
                    # クエリパラメータにIDトークンを設定し、その後にリロードをトリガーする
                    st.experimental_set_query_params(id_token=auth_response['idToken'])
                    st.sidebar.success('ログインに成功しました')
                    st.write('<meta http-equiv="refresh" content="0">', unsafe_allow_html=True)
                else:
                    st.sidebar.error('ユーザー情報の取得に失敗しました')
            else:
                st.sidebar.error('ログインに失敗しました')

        st.write("## SAKIYOMI 投稿 AI へようこそ！ログインしてください。")
        return

    st.sidebar.title('ユーザー情報')

    if st.sidebar.button('ログアウト'):
        st.session_state['logged_in'] = False
        st.session_state.pop('id_token', None)
        st.session_state.pop('user_info', None)
        st.session_state.pop('user_index', None)
        # クエリパラメータをクリア
        st.experimental_set_query_params()
        st.sidebar.success('ログアウトしました')
        st.write('<meta http-equiv="refresh" content="0">', unsafe_allow_html=True)
        return

    # ユーザー情報を表示
    if 'user_info' in st.session_state:
        st.sidebar.write(f"User ID: {st.session_state['user_info']['email']}")

    # インデックス情報を表示
    if 'user_index' in st.session_state and st.session_state['user_index']:
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

    # プロンプト情報を表示
    if 'prompt' in st.session_state:
        st.sidebar.write("投稿プロンプト:")
        st.sidebar.code(st.session_state['prompt']['system_prompt'], language='markdown')
        st.sidebar.write("タイトル提案プロンプト:")
        st.sidebar.code(st.session_state['prompt']['system_prompt_title_reccomend'], language='markdown')
    else:
        st.sidebar.write("プロンプトがありません")
        st.sidebar.write("新しいプロンプトを作成してください")
        return

    # タブセット1: "Input / Generated Script" を含むタブ
    tab1, tab2, tab3 = st.tabs(["プロット生成", "データ登録", "ネタ提案"])

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
                        if url != "":  # URLが空欄でない場合のみスクレイピングを実行
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
                    else:
                        st.session_state['response_text'] = "エラー: プロットを生成できませんでした。"

            # セッション状態からresponse_textを取得、存在しない場合はデフォルトのメッセージを表示
            displayed_value = st.session_state.get('response_text', "生成結果 : プロットが表示されます")
            st.text_area("生成結果", value=displayed_value, height=400)


    # タブ2: パラメーター設定
    with tab2:
        st.header('データを登録')
        # 2カラムを作成
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.subheader("URLの登録")

            # URL入力
            url = st.text_input("登録URLを入力してください")

            # 登録ボタン
            register_button1 = st.button("URL登録")

            if register_button1:
                # スクレイピング
                scraped_data = sh.scrape_url(url)


                combined_text, metadata_list = sh.prepare_text_and_metadata(sh.extract_keys_from_json(scraped_data))


                chunks = sh.split_text(combined_text)

                embeddings = sh.make_chunks_embeddings(chunks)

                # Pineconeにデータを保存
                sh.store_data_in_pinecone(index, embeddings, chunks, metadata_list, "ns2")

                st.success("データをPineconeに登録しました！")

            # 全データ削除ボタン
            delete_all_button1 = st.button("URL全データ削除")

            if delete_all_button1:
                sh.delete_all_data_in_namespace(index, "ns2")  # 全データを削除する関数を呼び出し
                st.success("全データが削除されました！")


        with col2:
            st.subheader("過去プロットの登録")

            # PDFファイルアップロード
            pdf_file1 = st.file_uploader("PDFファイルをアップロード", type=["pdf"], key="pdf_file1")

            # 登録ボタン
            register_button2 = st.button("PDF登録")

            if register_button2 and pdf_file1 is not None:
                # PDFファイルからテキストを抽出
                pdf_text = sh.extract_text_from_pdf(pdf_file1)

                # テキストをチャンクに分割
                chunks = sh.split_text(pdf_text)

                # チャンクの埋め込みを生成
                embeddings = sh.make_chunks_embeddings(chunks)


                # Pineconeにデータを保存
                sh.store_pdf_data_in_pinecone(index, embeddings, chunks, pdf_file1.name, "ns3")
                st.success("データをPineconeに登録しました！")

            # 全データ削除ボタン
            delete_all_button2 = st.button("全データ削除")

            if delete_all_button2:
                # 全データを削除する関数を呼び出し
                sh.delete_all_data_in_namespace(index, "ns3")
                st.success("全データが削除されました！")


        with col3:
            st.subheader("競合データの登録")

            # PDFファイルアップロード
            pdf_file2 = st.file_uploader("PDFファイルをアップロード", type=["pdf"], key="pdf_file2")

            # 登録ボタン
            register_button3 = st.button("PDF登録", key="register_button3")

            if register_button3 and pdf_file2 is not None:
                # PDFファイルからテキストを抽出
                pdf_text = sh.extract_text_from_pdf(pdf_file2)

                # テキストをチャンクに分割
                chunks = sh.split_text(pdf_text)

                # チャンクの埋め込みを生成
                embeddings = sh.make_chunks_embeddings(chunks)


                # Pineconeにデータを保存
                sh.store_pdf_data_in_pinecone(index, embeddings,chunks, pdf_file2.name, "ns4")
                st.success("データをPineconeに登録しました！")

            # 全データ削除ボタン
            delete_all_button3 = st.button("全データ削除", key="delete_all_3")

            if delete_all_button3:
                # 全データを削除する関数を呼び出し
                sh.delete_all_data_in_namespace(index, "ns4")
                st.success("全データが削除されました！")

        with col4:
            st.subheader("SAKIYOMIデータの登録")

            # PDFファイルアップロード
            pdf_file3 = st.file_uploader("PDFをアップロード", type=["pdf"], key="pdf_file3")

            # 登録ボタン
            register_button4 = st.button("PDF登録", key="register_button4")

            if register_button4 and pdf_file3 is not None:
                # PDFファイルからテキストを抽出
                pdf_text = sh.extract_text_from_pdf(pdf_file3)

                # テキストをチャンクに分割
                chunks = sh.split_text(pdf_text)

                # チャンクの埋め込みを生成
                embeddings = sh.make_chunks_embeddings(chunks)


                # Pineconeにデータを保存
                sh.store_pdf_data_in_pinecone(index, embeddings, chunks, pdf_file3.name, "ns5")
                st.success("データをPineconeに登録しました！")

            # 全データ削除ボタン
            delete_all_button4 = st.button("全データ削除", key="delete_all_4")

            if delete_all_button4:
                # 全データを削除する関数を呼び出し
                sh.delete_all_data_in_namespace(index, "ns5")
                st.success("全データが削除されました！")

    # テーマ提案タブ
    with tab3:
        st.header("投稿ネタ提案")
        col1, col2 = st.columns(2)
        with col1:
            with st.form("search_form"):
                user_query = st.text_area("作りたい投稿ジャンルのキーワードやイメージを入力して下さい。", height=50)
                selected_llm_title = st.radio("LLMの選択", ("GPT-4o", "Claude3"), key="radio_llm_selection_title")
                submit_button = st.form_submit_button("テーマ提案")

        # 検索実行
        with col2:
            if submit_button:
                with st.spinner('テーマ提案中...'):
                    if not user_query:
                        user_query = "*"
                    # クエリの実行
                    query_results = sh.perform_similarity_search(index, user_query, "ns3", top_k=10)
                    titles = sh.get_search_results_titles(query_results)
                    original_titles = sh.generate_new_titles(user_query, titles, selected_llm_title, st.session_state['prompt']['system_prompt_title_reccomend'])
                    st.session_state['reccomend_title'] = [f"- {title}" for title in original_titles.split('\n') if title.strip()]
                display_titles = st.session_state.get('reccomend_title', "")
                st.text_area("生成されたタイトル案:", "\n".join(display_titles), height=500)

if __name__ == "__main__":
    main()
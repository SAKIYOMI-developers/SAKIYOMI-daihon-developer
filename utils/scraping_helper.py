import requests
import json
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pinecone
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
import langchain
from openai import OpenAI
import streamlit as st
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.callbacks import tracing_v2_enabled
from utils.example_prompt import system_prompt_example, system_prompt_title_reccomend_example
import anthropic
from apify_client import ApifyClient
import logging
from ng_url_list import ng_urls

# ロガーを設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ハンドラーを設定してログを外部ファイルに記録
handler = logging.FileHandler("external_log.txt")
logger.addHandler(handler)

apify_wcc_endpoint = st.secrets['website_content_crawler_endpoint']
apifyapi_key = st.secrets['apifyapi_key']
openai_api_key = st.secrets['OPENAI_API_KEY']

#NG URLを判別する関数
def is_ng_url(url):
    return any(ng_url in url for ng_url in ng_urls)

# URLからコンテンツをスクレイピングする関数
def scrape_url(url):
    apify_client = ApifyClient('apify_api_akEVaWF0kZKZZT68WMUTvfrvOcAUjm436pIg')
    actor_call = apify_client.actor('apify/website-content-crawler').call(
        run_input={
            'startUrls': [{'url': url}],
            'maxRequestsPerCrawl': 3,
            'maxCrawlingDepth': 3,
        },
        timeout_secs=120
    )
    dataset_items = apify_client.dataset(actor_call['defaultDatasetId']).list_items().items
    return list(dataset_items)




# データ内の必要なキーだけを取得する関数
def extract_keys_from_json(data):  # 引数名を json_data から data に変更
    extracted_data = []
    for item in data:  # json.loads を使用せずに直接リストを処理
        formatted_data = {
            'url': item.get('url', ''),
            'description': item.get('metadata', {}).get('description', ''),
            'title': item.get('metadata', {}).get('title', ''),
            'text': item.get('text', ''),
            'keywords': item.get('metadata', {}).get('keywords', '')
        }
        extracted_data.append(formatted_data)
    return extracted_data


# テキストとメタデータを準備
def prepare_text_and_metadata(combined_data):
    texts = []
    metadata_list = []

    for item in combined_data:
        # テキスト部分の抽出と結合
        texts.append(item['text'])

        # メタデータの抽出
        metadata = {
            "original_url": item.get('url', ''),
            "description": item.get('description', '') if item.get('description') is not None else '',
            "title": item.get('title', '') if item.get('title') is not None else '',
            "keywords": item.get('keywords', '')  # Noneの場合は空文字列を返す
        }
        if metadata["keywords"]:  # キーワードが存在する場合のみ分割
            metadata["keywords"] = metadata["keywords"].split(', ')
        else:
            metadata["keywords"] = []  # キーワードがNoneまたは空の場合、空のリストを割り当てる

        metadata_list.append(metadata)

    # すべてのテキストを一つの文字列に結合
    combined_text = " ".join(texts)

    return combined_text, metadata_list




# テキストをチャンクに
def split_text(combined_text):
    set_chunk_length = 1000
    set_chunk_overlap = 100
    chunks = RecursiveCharacterTextSplitter(chunk_size = set_chunk_length, chunk_overlap = set_chunk_overlap)
    return chunks.split_text(combined_text)

from sentence_transformers import SentenceTransformer

def make_chunks_embeddings(chunks):
    # モデルのロード
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(chunks)

    return embeddings



### pinecone処理
def initialize_pinecone(pinecone_index_name, pinecone_api_key):
    pinecone = Pinecone(api_key=pinecone_api_key)
    index = pinecone.Index(pinecone_index_name)
    return index


def store_data_in_pinecone(index, chunk_embeddings, chunks, metadata_list, namespace):
    # 最初のメタデータを使用（共通部分）
    common_metadata = metadata_list[0]

    vectors_to_upsert = []
    for i, (embedding, chunk) in enumerate(zip(chunk_embeddings, chunks)):
        # 一意のIDの生成
        unique_id = f"{common_metadata['original_url']}-chunk-{i}"

        # メタデータにテキストチャンクを追加
        metadata = {
            "original_url": common_metadata['original_url'],
            "description": common_metadata['description'],
            "title": common_metadata['title'],
            "keywords": common_metadata['keywords'],
            "text_chunk": chunk  # テキストチャンクを追加
        }

        # ベクトルとメタデータをリストに追加
        vectors_to_upsert.append({
            "id": unique_id,
            "values": embedding.tolist(),  # numpy配列をリストに変換
            "metadata": metadata
        })

    # 一度に全てのベクトルをアップロード
    index.upsert(vectors=vectors_to_upsert, namespace=namespace)

    # 保存したIDをプリント（オプション）
    for vector in vectors_to_upsert:
        print(f"Saved: {vector['id']}")

# シミラリティ検索を実行する関数
# def perform_similarity_search(index, query, namespace, top_k=3):
#     query_embedding = generate_query_embedding(query)
#     return index.query(
#         namespace=namespace,
#         vector=query_embedding.tolist(),
#         top_k=top_k,
#         include_metadata=True
#     )

def perform_similarity_search(index, query, namespace, top_k=3):
    """
    指定したインデックスでセマンティック検索を実行し、最も類似した上位k個の結果を返す。

    :param index: Pineconeのインデックスオブジェクト
    :param query: 検索に使用するクエリテキスト
    :param namespace: 使用する名前空間
    :param top_k: 返される結果の数
    :return: 検索結果のリスト、各要素は辞書形式でメタデータを含む
    """
    # クエリのベクトル化
    query_embedding = generate_query_embedding(query)

    # logger.info(query_embedding.tolist())

    # クエリの実行
    search_results = index.query(
        namespace=namespace,
        vector=query_embedding.tolist(),
        top_k=top_k,
        include_metadata=True
    )

    # logger.info("------------------ search_results ------------------")
    # logger.info(search_results)
    return search_results

# 検索結果からメタデータの中のタイトルキーのみを取得する関数
def get_search_results_titles(search_results):
    search_results_metadata = search_results["matches"]
    search_results_titles = []

    for result in search_results_metadata:
        metadata = result["metadata"]
        title = metadata.get("1枚目-表紙 (タイトル)", metadata.get("タイトル", "N/A"))
        search_results_titles.append(title)
    logger.info(search_results_titles)
    return search_results_titles

# クエリの埋め込みベクトルを生成する関数
def generate_query_embedding(query):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode([query])[0]

def delete_all_data_in_namespace(index, namespace):
    index.delete(delete_all=True, namespace=namespace)
    print(f"次のネームスペースから全データが削除されました： '{namespace}'.")



def delete_data_by_url(index, namespace, url):
    # 名前空間内のすべてのIDを取得
    all_ids = index.describe_index_stats(namespace=namespace)["namespaces"][namespace]["ids"]

    # 指定されたURLに基づいてIDをフィルタリング
    ids_to_delete = [id for id in all_ids if url in id]

    # フィルタリングされたIDを削除
    index.delete(ids=ids_to_delete, namespace=namespace)
    print(f"ネームスペース【'{namespace}'】から次のURLの全データ削除されました【'{url}'】.")


def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def store_pdf_data_in_pinecone(index, chunk_embeddings, chunks, pdf_file_name, namespace):
    vectors_to_upsert = []
    for i, (embedding, chunk) in enumerate(zip(chunk_embeddings, chunks)):
        unique_id = f"pdf-chunk-{i}"  # PDFチャンクのIDを設定
        # メタデータにファイル名を使用
        metadata = {
            "pdf_filename": pdf_file_name,  # ファイル名をoriginal_urlとして使用
            "title": pdf_file_name,  # ファイル名をタイトルとして使用
            "description": "",  # 説明は空
            "keywords": [],  # キーワードは空のリスト
            "text_chunk": chunk  # テキストチャンクを追加
        }
        # ベクトルとメタデータをリストに追加
        vectors_to_upsert.append({
            "id": unique_id,
            "values": embedding.tolist(),
            "metadata": metadata
        })
    # 一度に全てのベクトルをアップロード
    index.upsert(vectors=vectors_to_upsert, namespace=namespace)
    # 保存したIDをプリント（オプション）
    for vector in vectors_to_upsert:
        print(f"Saved: {vector['id']}")


def generate_response_with_llm_for_multiple_namespaces(index, user_input, namespaces, selected_llm, system_prompt, project_name):
    results = {}  # 各名前空間の検索結果を格納する辞書

    # 名前空間ごとに検索結果を取得
    for ns in namespaces:
        try:
            query_embedding = generate_query_embedding(user_input)
            search_results = index.query(
                namespace=ns,
                vector=query_embedding.tolist(),
                top_k=3,
                include_metadata=True
            )
            if ns == "ns3":
                # ns3のメタデータを直接利用する特別な処理
                if search_results['matches']:
                    metadata = search_results['matches'][0]['metadata']
                    # 新しいメタデータ形式に基づいて内容を整形してLLMに渡す
                    results[ns] = "\n".join([f"{key}: {value}" for key, value in metadata.items()])
            else:
                # 他の名前空間の処理は変更なし
                result_texts = [result['metadata'] for result in search_results['matches']]
                if type(result_texts) == str:
                    "".join(result_texts) if result_texts else "情報なし"
                elif type(result_texts) == dict:
                    results[ns] = "\n".join([f"{key}: {value}" for key, value in result_texts.items()])
                elif isinstance(result_texts, list) and all(isinstance(item, dict) for item in result_texts):
                    results[ns] = "\n".join([f"{key}: {value}" for item in result_texts for key, value in item.items()])
                else:
                    results[ns] = "".join(str(result_texts)) if result_texts else "情報なし"

        except KeyError as e:
            print(f"エラーが発生しました: 名前空間 '{ns}' で {e} キーが見つかりません。")
            results[ns] = "エラー: 検索結果が見つかりませんでした。"

    # プロンプトテンプレートの準備
    prompt_template = PromptTemplate(template=system_prompt, input_variables=["user_input", "results_ns1", "results_ns2", "results_ns3", "results_ns4", "results_ns5"])

    # LLMの選択
    if selected_llm == "o1":
        llm = ChatOpenAI(model='o1', temperature=1.0)
    else:
        llm = ChatAnthropic(model_name='claude-3-5-sonnet-20240620', temperature=1.0, max_tokens=3072)

    llm_chain = LLMChain(prompt=prompt_template, llm=llm)

    with tracing_v2_enabled(project_name=project_name):
        response = llm_chain.invoke({
            "user_input": user_input,
            "results_ns1": results.get('ns1', '情報なし'),
            "results_ns2": results.get('ns2', '情報なし'),
            "results_ns3": results.get('ns3', '情報なし'),
            "results_ns4": results.get('ns4', '情報なし'),
            "results_ns5": results.get('ns5', '情報なし'),
        })

    print("LLMの応答:", response)

    return response

# 競合他社の投稿タイトルのリストからオリジナルのタイトル候補を生成する関数
def generate_new_titles(user_query, competing_titles, selected_llm, system_prompt_title_reccomend):
    prompt_template = PromptTemplate(template=system_prompt_title_reccomend, input_variables=["user_query", "competing_titles"])
    if selected_llm == "o1":
        llm = ChatOpenAI(model='o1', temperature=1.0, max_completion_tokens=3072)
    else:
        llm = ChatAnthropic(model_name='claude-3-5-sonnet-20240620', temperature=1.0, max_tokens=3072)
    llm_chain = LLMChain(prompt=prompt_template, llm=llm)
    response = llm_chain.run({
        "user_query": user_query,
        "competing_titles": "\n".join(competing_titles)
    })
    return response

""""
user_input = "トマトとはを最初に解説して、その後トマトの育て方を詳しく教えてください。 また栄養面からもトマトを育てるメリットを。そして絵文字をたくさんつかってください"
namespaces = ["ns1", "ns2", "ns3", "ns4"]
index = initialize_pinecone()
response = generate_response_with_llm_for_multiple_namespaces(index, user_input, namespaces)
print('ひーはー', response)


# ここでinitialize_pinecone関数を呼び出してindexオブジェクトを取得
index = initialize_pinecone()

# インデックスの状態をチェック
try:
    index_stats = index.describe_index_stats()
    print("インデックスの状態:", index_stats)
except Exception as e:
    print("接続エラー:", e)


# テスト用のURLを直接指定
test_url = "https://www.renoveru.jp/journal/14601"

scraped_data = scrape_url(test_url)

# combined_text と metadata_list の準備
combined_text, metadata_list = prepare_text_and_metadata(extract_keys_from_json(scraped_data))

print(metadata_list)

# テキストをチャンクに分割
chunks = split_text(combined_text)


# チャンクの埋め込みを生成
embeddings = make_chunks_embeddings(chunks)

print("エンベディングスの数:", len(embeddings))

#print("テスト: データをPineconeに保存")
store_data_in_pinecone(index, embeddings, chunks, metadata_list, "ns1")


# クエリを実行して結果をプリント
query = "トマトとはを最初に解説して、その後トマトの育て方を詳しく教えてください。 また栄養面からもトマトを育てるメリットを"
search_results = perform_similarity_search(index, query, "ns1" , top_k=1)
print(search_results)

delete_all_data_in_namespace(index, "ns1")
"""

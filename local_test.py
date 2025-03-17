from application.user_service import UserService
from application.user_index_service import UserIndexService
from domain.user import User

# サービスの初期化
user_service = UserService()
user_index_service = UserIndexService()

def test_create_user_and_index():
    # テスト用のユーザー情報
    email = "testuser333@example.com"
    password = "password123"
    display_name = "Test User"
    instagram_username = "@testuser"

    # ユーザーの作成または更新
    user = User(
        user_id="",
        email=email,
        display_name=display_name,
        role="user",
        created_at=None,
        instagram_username=instagram_username
    )

    print("Creating or updating user...")
    user_response = user_service.create_or_update_user(user, password)
    if user_response['status'] == 'success':
        print("User created or updated successfully!")
        user_id = user_response['user_id']
    else:
        print("Failed to create or update user:", user_response['message'])
        return

    # インデックスの作成
    index_name = "manu-test-index"
    langsmith_project_name = "test-project"

    print("Creating user index...")
    index_response = user_index_service.create_user_index(user_id, index_name, langsmith_project_name)
    if index_response['status'] == 'success':
        print("User index created successfully!")
        index_id = index_response['index_id']
        print("Index ID:", index_id)
    else:
        print("Failed to create user index:", index_response['message'])

if __name__ == "__main__":
    test_create_user_and_index()

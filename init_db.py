from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    print("データベースを作成中...")
    db.create_all()
    print("成功しました！usersテーブルが作成されました。")

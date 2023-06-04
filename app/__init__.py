from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.bbdd_secrets import dbsecrets
db = SQLAlchemy()
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


@login_manager.request_loader
def load_user_from_request(request):
    from app.models import User
    user_id = request.headers.get('X-Auth-User')
    if user_id:
        return User.query.get(int(user_id))
    return None


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = dbsecrets.get('DATABASE_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = dbsecrets.get('SQLALCHEMY_DATABASE_URI')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    with app.app_context():
        from . import routes, models
        db.create_all()

    return app

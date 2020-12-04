from flask import Flask
from authlib.integrations.flask_client import OAuth
from app.models import db
import os

# from flask_bcrypt import Bcrypt


app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
app.config.from_object("app.config.Config")

# initialize SQLAlchemy
db.init_app(app)

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", None),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", None),
    access_token_url="https://accounts.google.com/o/oauth2/token",
    access_token_params=None,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    authorize_params=None,
    api_base_url="https://www.googleapis.com/oauth2/v1/",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",  # This is only needed if using openId to fetch user info
    client_kwargs={"scope": "openid email profile"},
)

from app import views

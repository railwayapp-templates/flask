from flask import Flask
from config import SECRET_KEY, DEBUG, HOST, PORT
from database import init_users_db
from routes import register_blueprints

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Регистрация blueprints
register_blueprints(app)

if __name__ == '__main__':
    init_users_db()
    app.run(debug=DEBUG, host=HOST, port=PORT, threaded=True)

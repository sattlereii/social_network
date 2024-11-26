from flask import Flask, redirect, url_for
from routes.auth import auth_blueprint
from routes.profile import profile_blueprint
from routes.challenges import challenges_blueprint
from routes.search import search_blueprint
from routes.admin import admin_blueprint


app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    return redirect(url_for('auth.login'))
app.register_blueprint(admin_blueprint, url_prefix='/admin')
app.register_blueprint(auth_blueprint)
app.register_blueprint(profile_blueprint)
app.register_blueprint(challenges_blueprint)
app.register_blueprint(search_blueprint)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

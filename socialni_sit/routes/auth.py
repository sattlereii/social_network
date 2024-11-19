from flask import Blueprint, render_template, request, redirect, url_for, session
from db.neo4j_connection import Neo4jConnection

auth_blueprint = Blueprint('auth', __name__)

# Login route
@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = Neo4jConnection()
        user = conn.query("MATCH (u:User {username: $username, password: $password}) RETURN u",
                          {'username': username, 'password': password})
        conn.close()

        if user:
            session['username'] = username
            return redirect(url_for('challenges.home'))
        else:
            return "Login failed", 401

    return render_template('login.html')

# Register route
@auth_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        age = request.form['age']
        password = request.form['password']
        interests = request.form['interests'].split(',')

        conn = Neo4jConnection()
        conn.query("CREATE (u:User {username: $username, age: $age, password: $password, interests: $interests})",
                   {'username': username, 'age': int(age), 'password': password, 'interests': interests})
        conn.close()
        return redirect(url_for('auth.login'))  # Po registraci se vrací na login stránku

    return render_template('register.html')

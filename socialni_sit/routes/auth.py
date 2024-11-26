from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db.neo4j_connection import Neo4jConnection
from db.export_data import export_data
from db.import_data import import_data

auth_blueprint = Blueprint('auth', __name__)

# Login route
# Login route
@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = Neo4jConnection()

        # Získání uživatele na základě přihlašovacích údajů
        user = conn.query(
            "MATCH (u:User {username: $username, password: $password}) RETURN u.role AS role, u.suspended AS suspended",
            {'username': username, 'password': password}
        )

        if user:  # Pokud byl uživatel nalezen
            user_data = user[0]  # První výsledek dotazu

            if 'suspended' in user_data and user_data['suspended']:  # Kontrola, zda je účet pozastaven
                flash("Tento účet je pozastaven!", "danger")
                conn.close()
                return redirect(url_for('auth.login'))

            # Uložení uživatelského jména a role do session
            session['username'] = username
            session['role'] = user_data['role']  # Získání role uživatele
            flash("Přihlášení bylo úspěšné!", "success")
            conn.close()
            return redirect(url_for('profile.view_profile'))
        else:
            flash("Neplatné přihlašovací údaje.", "danger")
            conn.close()
            return redirect(url_for('auth.login'))

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

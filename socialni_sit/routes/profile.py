from flask import Blueprint, render_template, request, redirect, url_for, session
from db.neo4j_connection import Neo4jConnection

profile_blueprint = Blueprint('profile', __name__)

@profile_blueprint.route('/profile')
def view_profile():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    username = session['username']
    conn = Neo4jConnection()

    # Načtení bodů uživatele a role
    user_data = conn.query(
        "MATCH (u:User {username: $username}) RETURN u.points AS points, u.role AS role",
        {'username': username}
    )
    points = user_data[0]['points'] if user_data and 'points' in user_data[0] else 0
    role = user_data[0]['role'] if user_data and 'role' in user_data[0] else "user"

    # Výzvy, které uživatel vytvořil
    created_challenges = conn.query(
        """
        MATCH (u:User {username: $username})-[:CREATED]->(c:Challenge)
        RETURN c.id AS id, c.name AS name, c.hashtags AS hashtags
        """,
        {'username': username}
    )
    created_challenges = created_challenges if created_challenges else []  # Pokud je None, nastav prázdný seznam

    # Debug: výpis dat vytvořených výzev
    print("Created Challenges Debug:", created_challenges)

    # Splněné výzvy
    completed_challenges = conn.query(
        """
        MATCH (u:User {username: $username})-[rel:COMPLETED]->(c:Challenge)
        RETURN c.id AS id, c.name AS name, rel.result AS result
        """,
        {'username': username}
    )
    completed_challenges = completed_challenges if completed_challenges else []  # Pokud je None, nastav prázdný seznam

    # Debug: výpis dat sezení
    print("Session data:", session)

    conn.close()

    return render_template(
        'profile.html',
        user={'username': username, 'points': points},
        created_challenges=created_challenges,
        completed_challenges=completed_challenges,
        is_self=True,
        is_admin=(role == "admin")  # Kontrola, zda je uživatel admin
    )


@profile_blueprint.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    username = session['username']
    conn = Neo4jConnection()

    if request.method == 'POST':
        new_username = request.form['username']
        new_age = request.form['age']
        new_interests = request.form['interests'].split(',')

        conn.query("MATCH (u:User {username: $username}) "
                   "SET u.username = $new_username, u.age = $new_age, u.interests = $new_interests",
                   {'username': username, 'new_username': new_username, 'new_age': int(new_age), 'new_interests': new_interests})
        
        session['username'] = new_username
        conn.close()
        return redirect(url_for('profile.view_profile'))

    user = conn.query("MATCH (u:User {username: $username}) RETURN u", {'username': username})
    conn.close()
    return render_template('edit_profile.html', user=user[0]['u'])

@profile_blueprint.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('auth.login'))


@profile_blueprint.route('/user/<username>')
def view_other_profile(username):
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    conn = Neo4jConnection()

    # Výzvy, které uživatel vytvořil
    created_challenges = conn.query(
        """
        MATCH (u:User {username: $username})-[:CREATED]->(c:Challenge)
        RETURN c.id AS id, c.name AS name, c.hashtags AS hashtags
        """,
        {'username': username}
    )

    # Splněné výzvy
    completed_challenges = conn.query(
        "MATCH (u:User {username: $username})-[:COMPLETED]->(c:Challenge) RETURN c",
        {'username': username}
    )

    conn.close()
    return render_template(
        'profile.html', 
        user={'username': username},
        created_challenges=created_challenges,
        completed_challenges=completed_challenges,
        is_self=False  # Označení, že jde o jiný profil
    )
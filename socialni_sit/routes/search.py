from flask import Blueprint, render_template, request, redirect, url_for, session
from db.neo4j_connection import Neo4jConnection

# Inicializace Blueprint
search_blueprint = Blueprint('search', __name__)

@search_blueprint.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    conn = Neo4jConnection()
    users = []
    challenges = []

    if request.method == 'POST':
        query = request.form['query']

        # Vyhledání uživatelů
        users = conn.query(
            """
            MATCH (u:User)
            WHERE u.username CONTAINS $query
            RETURN u.username AS username, u.interests AS interests
            """,
            {'query': query}
        )

        # Vyhledání výzev
        challenges = conn.query(
            """
            MATCH (c:Challenge)
            WHERE c.name CONTAINS $query OR ANY(tag IN c.hashtags WHERE tag CONTAINS $query)
            RETURN c.id AS id, c.name AS name, c.hashtags AS hashtags
            """,
            {'query': query}
        )

    conn.close()
    return render_template(
        'search.html',
        users=users,
        challenges=challenges
    )

    return render_template('search.html', users=users, challenges=challenges)

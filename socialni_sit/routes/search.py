import unicodedata
from flask import Blueprint, render_template, request, redirect, url_for, session
from db.neo4j_connection import Neo4jConnection

search_blueprint = Blueprint('search', __name__)

def remove_diacritics(input_str):
    """Odstranění diakritiky z textu."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', input_str)
        if unicodedata.category(c) != 'Mn'
    )

@search_blueprint.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    conn = Neo4jConnection()
    users = []
    challenges = []
    hashtags_found = set()  # Unikátní hashtagy nalezené během hledání
    search_term = ""

    if request.method == 'POST':
        query = request.form['query']
        normalized_query = remove_diacritics(query.lower())  # Normalizace vstupu
        search_term = query  # Pro zobrazení na stránce

        # Načíst všechny uživatele z databáze
        db_users = conn.query(
            """
            MATCH (u:User)
            RETURN u.username AS username, u.interests AS interests
            """
        )

        # Načíst všechny výzvy z databáze
        db_challenges = conn.query(
            """
            MATCH (c:Challenge)
            RETURN c.id AS id, c.name AS name, c.hashtags AS hashtags
            """
        )

        # Filtrovat výsledky uživatelů
        users = [
            user for user in db_users
            if normalized_query in remove_diacritics(user['username'].lower())
               or any(normalized_query in remove_diacritics(interest.lower()) for interest in (user['interests'] or []))
        ]

        # Filtrovat výsledky výzev
        challenges = [
            challenge for challenge in db_challenges
            if normalized_query in remove_diacritics(challenge['name'].lower())
               or any(normalized_query in remove_diacritics(tag.lower()) for tag in (challenge['hashtags'] or []))
        ]

        # Najít všechny unikátní hashtagy
        for challenge in challenges:
            if challenge['hashtags']:
                hashtags_found.update(
                    tag for tag in challenge['hashtags'] if normalized_query in remove_diacritics(tag.lower())
                )

    conn.close()
    return render_template(
        'search.html',
        users=users,
        challenges=challenges,
        search_term=search_term,
        hashtags=list(hashtags_found)  # Převést na seznam pro šablonu
    )

from flask import Blueprint, render_template, request
from db.neo4j_connection import Neo4jConnection

search_blueprint = Blueprint('search', __name__)

@search_blueprint.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query']
        conn = Neo4jConnection()
        users = conn.query("MATCH (u:User) WHERE u.username CONTAINS $query RETURN u", {'query': query})
        challenges = conn.query("MATCH (c:Challenge) WHERE c.name CONTAINS $query OR $query IN c.hashtags RETURN c", {'query': query})
        conn.close()
        return render_template('search.html', users=users, challenges=challenges)

    return render_template('search.html')
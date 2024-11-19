from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db.neo4j_connection import Neo4jConnection
from datetime import datetime, timedelta
import uuid


challenges_blueprint = Blueprint('challenges', __name__)


@challenges_blueprint.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    conn = Neo4jConnection()
    challenges = conn.query("MATCH (c:Challenge) RETURN c")
    conn.close()

    # Přidání zbývajícího času pro každou výzvu
    for challenge in challenges:
        created_at = datetime.strptime(challenge['c']['created_at'], "%Y-%m-%d")
        duration_days = int(challenge['c']['duration'])
        end_date = created_at + timedelta(days=duration_days)
        challenge['c']['time_remaining'] = (end_date - datetime.now()).days

    return render_template('home.html', challenges=challenges)


@challenges_blueprint.route('/create_challenge', methods=['GET', 'POST'])
def create_challenge():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form['name']
        duration = request.form['duration']
        description = request.form['description']
        hashtags = request.form['hashtags'].split(',')

        conn = Neo4jConnection()
        challenge_id = str(uuid.uuid4())
        conn.query(
            "MATCH (u:User {username: $username}) "
            "CREATE (u)-[:CREATED]->(c:Challenge {id: $id, name: $name, duration: $duration, description: $description, hashtags: $hashtags, created_by: $username, created_at: $created_at})",
            {
                'username': session['username'], 
                'id': challenge_id, 
                'name': name, 
                'duration': duration, 
                'description': description, 
                'hashtags': hashtags, 
                'created_at': datetime.now().strftime("%Y-%m-%d")
            }
        )
        conn.close()
        return redirect(url_for('challenges.home'))

    return render_template('create_challenge.html')



@challenges_blueprint.route('/challenge/<challenge_id>', methods=['GET', 'POST'])
def challenge_detail(challenge_id):
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    conn = Neo4jConnection()
    challenge = conn.query("MATCH (c:Challenge) WHERE c.id = $id RETURN c", {'id': challenge_id})[0]['c']
    
    # Kontrola, zda uživatel již dokončil výzvu
    user_completed = conn.query("MATCH (u:User {username: $username})-[:COMPLETED]->(c:Challenge {id: $id}) RETURN c",
                                {'username': session['username'], 'id': challenge_id})

    # Kontrola, zda uživatel přihlásil do výzvy, pokud ji ještě nedokončil
    user_registered = None
    if not user_completed:
        user_registered = conn.query("MATCH (u:User {username: $username})-[:JOINED]->(c:Challenge {id: $id}) RETURN c",
                                     {'username': session['username'], 'id': challenge_id})
    
    if request.method == 'POST' and not user_completed:
        if 'result' in request.form:
            # Uložit výsledek a zobrazit úspěšnou zprávu
            result = request.form['result']
            conn.query("MATCH (u:User {username: $username}), (c:Challenge {id: $id}) "
                       "MERGE (u)-[:COMPLETED {result: $result}]->(c)", 
                       {'username': session['username'], 'id': challenge_id, 'result': result})
            conn.close()
            flash("Úspěšně jsi dokončil výzvu")
            return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))
        else:
            # Přihlášení k výzvě
            conn.query("MATCH (u:User {username: $username}), (c:Challenge {id: $id}) "
                       "MERGE (u)-[:JOINED]->(c)", 
                       {'username': session['username'], 'id': challenge_id})

    conn.close()
    return render_template('challenge_detail.html', challenge=challenge, user_registered=bool(user_registered), user_completed=bool(user_completed))

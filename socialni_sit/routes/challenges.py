from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
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
    active_challenges = []
    
    for challenge in challenges:
        created_at = datetime.strptime(challenge['c']['created_at'], "%Y-%m-%d")
        duration_days = int(challenge['c']['duration'])
        end_date = created_at + timedelta(days=duration_days)
        time_remaining = (end_date - datetime.now()).days

        if time_remaining >= 0:
            challenge['c']['time_remaining'] = time_remaining
            active_challenges.append(challenge)
        else:
            # Označení výzvy jako archivované, pokud již skončila
            conn.query("MATCH (c:Challenge {id: $id}) SET c.archived = true", {'id': challenge['c']['id']})

    conn.close()

    return render_template('home.html', challenges=active_challenges)

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

        # Vytvoření výzvy
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

        # Přidání bodů za vytvoření výzvy
        conn.query(
            "MATCH (u:User {username: $username}) "
            "SET u.points = coalesce(u.points, 0) + 2",
            {'username': session['username']}
        )
        conn.close()
        flash("Výzva byla úspěšně vytvořena a získali jste 2 činky!")
        return redirect(url_for('challenges.home'))

    return render_template('create_challenge.html')

@challenges_blueprint.route('/archive')
def archive():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    conn = Neo4jConnection()
    archived_challenges = conn.query("MATCH (c:Challenge) WHERE c.archived = true RETURN c")
    conn.close()
    return render_template('archive.html', challenges=archived_challenges)

@challenges_blueprint.route('/challenge/<challenge_id>', methods=['GET', 'POST'])
def challenge_detail(challenge_id):
    if 'username' not in session:
        return render_template('challenge_detail.html', challenge_id=challenge_id, user_joined=False, user_completed=False)

    conn = Neo4jConnection()

    # Načíst detail výzvy
    challenge_data = conn.query(
        "MATCH (c:Challenge) WHERE c.id = $id RETURN c",
        {'id': challenge_id}
    )
    if not challenge_data:
        flash("Výzva nebyla nalezena.", "danger")
        return redirect(url_for('challenges.home'))

    challenge = challenge_data[0]['c']
    
    # Zkontrolovat, zda je aktuální uživatel tvůrcem výzvy
    is_creator = challenge['created_by'] == session['username']
    
    # Vypočítat čas zbývající do konce výzvy
    created_at = datetime.strptime(challenge['created_at'], "%Y-%m-%d")
    duration_days = int(challenge['duration'])
    end_date = created_at + timedelta(days=duration_days)
    time_remaining = (end_date - datetime.now()).days

    # Kontrola, zda uživatel přihlásil nebo dokončil výzvu
    user_joined = conn.query(
        """
        MATCH (u:User {username: $username})-[:JOINED]->(c:Challenge {id: $id})
        RETURN c
        """,
        {'username': session['username'], 'id': challenge_id}
    )
    user_completed = conn.query(
        """
        MATCH (u:User {username: $username})-[:COMPLETED]->(c:Challenge {id: $id})
        RETURN c
        """,
        {'username': session['username'], 'id': challenge_id}
    )

    if request.method == 'POST':
        if 'result' in request.form:
            result = request.form['result']
            # Dokončit výzvu
            conn.query(
                """
                MATCH (u:User {username: $username})-[r:JOINED]->(c:Challenge {id: $id})
                DELETE r
                MERGE (u)-[rel:COMPLETED]->(c)
                SET rel.result = $result
                """,
                {'username': session['username'], 'id': challenge_id, 'result': result}
            )
            conn.query(
                "MATCH (u:User {username: $username}) "
                "SET u.points = coalesce(u.points, 0) + 1",
                {'username': session['username']}
            )
            conn.close()
            flash("Výzvu jste úspěšně dokončili a získali jste 1 činku!", "success")
            return redirect(url_for('profile.view_profile'))

        elif 'join' in request.form:
            # Připojit se k výzvě
            if not user_joined and not user_completed:
                conn.query(
                    "MATCH (u:User {username: $username}), (c:Challenge {id: $id}) "
                    "MERGE (u)-[:JOINED]->(c)",
                    {'username': session['username'], 'id': challenge_id}
                )
                conn.close()
                flash("Připojili jste se k výzvě!", "success")
                return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))

        elif 'leave' in request.form:
            # Odpojit se od výzvy
            if user_joined and not user_completed:
                conn.query(
                    "MATCH (u:User {username: $username})-[r:JOINED]->(c:Challenge {id: $id}) "
                    "DELETE r",
                    {'username': session['username'], 'id': challenge_id}
                )
                conn.close()
                flash("Odpojili jste se od výzvy!", "info")
                return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))

    conn.close()

    return render_template(
        'challenge_detail.html',
        challenge=challenge,
        user_joined=bool(user_joined),
        user_completed=bool(user_completed),
        time_remaining=time_remaining,
        is_creator=is_creator  # Předáváme informaci do šablony
    )

@challenges_blueprint.route('/delete_challenge/<challenge_id>', methods=['POST'])
def delete_challenge(challenge_id):
    if 'username' not in session:
        print("User is not authenticated.")
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401

    conn = Neo4jConnection()

    try:
        print(f"Attempting to delete challenge with ID: {challenge_id}")

        # Zkontroluj, jestli výzva existuje
        result = conn.query("MATCH (c:Challenge {id: $id}) RETURN c", {'id': challenge_id})
        print(f"Query result for challenge existence: {result}")
        
        if not result:
            print("Challenge not found.")
            return jsonify({'success': False, 'error': 'Challenge not found'}), 404

        # Smaž výzvu a její vztahy
        conn.query("MATCH (c:Challenge {id: $id}) DETACH DELETE c", {'id': challenge_id})
        print("Challenge successfully deleted.")
        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Error occurred while deleting challenge: {str(e)}")
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

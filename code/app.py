from py2neo import Graph, Node, Relationship
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from random import choice
from random import choice
from database import init_db, get_user_node, create_sample_data, get_matches, available_matches


app = Flask(__name__)
app.secret_key = "your_secret_key"  # Nastavte silný tajný klíč
graph = Graph("bolt://neo4j:7687", auth=("neo4j", "adminpass"))

# Funkce pro vytvoření uživatele s body sluníček a ohýnků
def create_user(graph, username, password, age=None, hobbies=None):
    password_hash = generate_password_hash(password)
    user_node = Node("User", name=username, password=password_hash, sun_points=0, fire_points=0, age=age, hobbies=hobbies)
    graph.create(user_node)

# Funkce pro ověření uživatele při přihlášení
def verify_user(graph, username, password):
    user = graph.evaluate("MATCH (user:User {name: $username}) RETURN user", username=username)
    if user and check_password_hash(user["password"], password):
        return True
    return False

# Získání profilu přihlášeného uživatele
def get_logged_user_profile(graph, username):
    result = graph.run(f"""
        MATCH (user:User)
        WHERE user.name = '{username}'
        RETURN user.name AS name, user.age AS age, user.hobbies AS hobbies, user.sun_points AS sun_points, user.fire_points AS fire_points
    """).data()
    return result[0] if result else {}

def get_all_hashtags(graph):
    """Načte všechny hashtagy z databáze."""
    return graph.run("MATCH (h:Hashtag) RETURN h.name AS name").data()

def add_hashtag(graph, name):
    """Přidá nový hashtag do databáze, pokud ještě neexistuje."""
    graph.run("""
        MERGE (h:Hashtag {name: $name})
    """, name=name)


# Funkce pro vytvoření výzvy
def create_challenge(graph, username, title, description, duration, hashtags):
    end_date = datetime.now() + timedelta(days=duration)
    challenge_node = Node("Challenge", title=title, description=description, creator=username, end_date=end_date.isoformat())
    creator_node = get_user_node(graph, username)
    
    # Vytvoření vztahu mezi uživatelem a výzvou
    created_rel = Relationship(creator_node, "CREATED", challenge_node)
    graph.create(challenge_node | created_rel)
    
    # Přidání bodů sluníček uživateli za vytvoření výzvy
    graph.run("MATCH (u:User {name: $username}) SET u.sun_points = u.sun_points + 2", username=username)
    
    # Přidání vztahu k hashtagům
    for hashtag in hashtags:
        hashtag_node = graph.evaluate("MATCH (h:Hashtag {name: $name}) RETURN h", name=hashtag)
        if hashtag_node:
            hashtag_rel = Relationship(challenge_node, "TAGGED_WITH", hashtag_node)
            graph.create(hashtag_rel)


def get_all_challenges(graph, username):
    return graph.run("""
        MATCH (c:Challenge)
        OPTIONAL MATCH (u:User {name: $username})-[r:JOINED]->(c)
        OPTIONAL MATCH (u)-[cr:COMPLETED]->(c)
        RETURN c.title AS title, c.description AS description, c.creator AS creator, c.end_date AS end_date,
               CASE WHEN r IS NOT NULL THEN true ELSE false END AS is_joined,
               CASE WHEN cr IS NOT NULL THEN true ELSE false END AS is_completed
        ORDER BY c.end_date DESC
    """, username=username).data()


# Získání aktivních výzev
def get_active_challenges(graph):
    return graph.run("""
        MATCH (c:Challenge)
        WHERE datetime(c.end_date) > datetime()
        RETURN c.title, c.description, c.creator, c.end_date
    """).data()

# Připojení uživatele k výzvě
def join_challenge(graph, username, challenge_title, result=None, comment=None):
    user_node = get_user_node(graph, username)
    challenge_node = graph.evaluate("MATCH (c:Challenge {title: $title}) RETURN c", title=challenge_title)

    if challenge_node:
        # Zkontroluje, zda uživatel již není připojen
        existing_join = graph.evaluate("""
            MATCH (u:User {name: $username})-[r:JOINED]->(c:Challenge {title: $title})
            RETURN r
        """, username=username, title=challenge_title)

        # Pokud není připojen, připojí ho k výzvě a přičte body
        if not existing_join:
            join_rel = Relationship(user_node, "JOINED", challenge_node)
            graph.create(join_rel)
        
# Získání archivu výzev
def get_challenge_archive(graph):
    return graph.run("""
        MATCH (c:Challenge)
        WHERE datetime(c.end_date) <= datetime()
        OPTIONAL MATCH (u:User)-[r:COMPLETED]->(c)
        RETURN c.title, c.description, c.creator, c.end_date, collect({user: u.name, photo: r.photo}) AS completions
    """).data()

def available_matches(graph, username):
    return graph.run(f"""
        MATCH (user:User {{name: '{username}'}})
        MATCH (friend:User)
        WHERE NOT (user)-[:LIKES]->(friend)
          AND NOT (friend)-[:DISLIKES]->(user)
          AND user.name <> friend.name
        RETURN friend.name AS name, friend.age AS age, friend.hobbies AS hobbies
    """).data()

# Získání uzlu uživatele podle jména
def get_user_node(graph, username):
    return graph.evaluate("MATCH (u:User {name: $username}) RETURN u", username=username)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        age = int(request.form.get("age"))
        hobbies = request.form.get("hobbies").split(",")  # Rozdělte koníčky podle čárek

        existing_user = graph.evaluate("MATCH (user:User {name: $username}) RETURN user", username=username)
        if existing_user:
            flash("Username already exists!")
            return redirect(url_for("register"))

        create_user(graph, username, password, age, hobbies)
        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if verify_user(graph, username, password):
            session["username"] = username
            flash("Login successful!")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.")
    
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    new_name = request.form.get("name")
    new_password = request.form.get("password")
    new_age = request.form.get("age")
    new_hobbies = request.form.get("hobbies").split(",")

    # Aktualizace uživatelských údajů v databázi
    if new_password:
        password_hash = generate_password_hash(new_password)
        graph.run("""
            MATCH (u:User {name: $username})
            SET u.password = $password_hash
        """, username=username, password_hash=password_hash)

    graph.run("""
        MATCH (u:User {name: $username})
        SET u.name = $new_name, u.age = $new_age, u.hobbies = $new_hobbies
    """, username=username, new_name=new_name, new_age=int(new_age), new_hobbies=new_hobbies)

    # Aktualizujte jméno v session, pokud bylo změněno
    session["username"] = new_name

    flash("Profil byl úspěšně aktualizován.")
    return redirect(url_for("user_profile"))

@app.route("/")
@app.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    logged_user = session["username"]
    logged_user_info = get_logged_user_profile(graph, logged_user)
    challenges = get_all_challenges(graph, logged_user)  # Získání všech výzev s informací o připojení
    return render_template("home.html", profile=logged_user_info, challenges=challenges)




@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.args.get("query", "")
    search_type = request.args.get("search_type", "users")
    results = []

    if search_type == "users":
        # Hledání uživatelů s podobným jménem
        results = graph.run("""
            MATCH (u:User)
            WHERE toLower(u.name) CONTAINS toLower($query)
            RETURN u.name AS name, 'user' AS type
        """, query=query).data()

    elif search_type == "challenges_title":
        # Hledání výzev s podobným názvem
        results = graph.run("""
            MATCH (c:Challenge)
            WHERE toLower(c.title) CONTAINS toLower($query)
            RETURN c.title AS title, c.description AS description, 'challenge' AS type
        """, query=query).data()

    elif search_type == "challenges_hashtag":
        # Hledání výzev podle hashtagu
        results = graph.run("""
            MATCH (c:Challenge)-[:TAGGED_WITH]->(h:Hashtag)
            WHERE toLower(h.name) CONTAINS toLower($query)
            RETURN c.title AS title, c.description AS description, h.name AS hashtag, 'hashtag_challenge' AS type
        """, query=query).data()

    return render_template("search.html", results=results)


@app.route("/profile")
def user_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user_info = get_logged_user_profile(graph, username)
    
    # Získání probíhajících výzev (připojených, ale nesplněných)
    ongoing_challenges = graph.run("""
        MATCH (u:User {name: $username})-[:JOINED]->(c:Challenge)
        WHERE NOT (u)-[:COMPLETED]->(c)
        RETURN c.title AS title, c.description AS description, c.end_date AS end_date
    """, username=username).data()
    
@app.route("/profile/<username>")
def users_profile(username):
    user_info = get_logged_user_profile(graph, username)
    
    # Získání probíhajících a splněných výzev tohoto uživatele
    ongoing_challenges = graph.run("""
        MATCH (u:User {name: $username})-[:JOINED]->(c:Challenge)
        WHERE NOT (u)-[:COMPLETED]->(c)
        RETURN c.title AS title, c.description AS description, c.end_date AS end_date
    """, username=username).data()
    
    completed_challenges = graph.run("""
        MATCH (u:User {name: $username})-[r:COMPLETED]->(c:Challenge)
        RETURN c.title AS title, c.description AS description, c.end_date AS end_date, r.result AS result, r.comment AS comment
    """, username=username).data()
    
    return render_template("profile.html", profile=user_info, ongoing_challenges=ongoing_challenges, completed_challenges=completed_challenges)


@app.route("/create_challenge", methods=["GET", "POST"])
def create_challenge_route():
    if "username" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        duration = int(request.form.get("duration"))
        hashtags = request.form.getlist("hashtags")

        # Vytvoření výzvy s vybranými hashtagy
        create_challenge(graph, session["username"], title, description, duration, hashtags)
        flash("Výzva byla úspěšně vytvořena!")
        return redirect(url_for("home"))
    
    # Načtení existujících hashtagů pro zobrazení ve formuláři
    hashtags = get_all_hashtags(graph)
    return render_template("create_challenge.html", hashtags=hashtags)

@app.route("/add_hashtag", methods=["GET", "POST"])
def add_hashtag():
    if request.method == "POST":
        new_hashtag = request.form.get("new_hashtag")
        add_hashtag(graph, new_hashtag)
        flash("Nový hashtag byl přidán.")
        return redirect(url_for("create_challenge_route"))
    
    return render_template("add_hashtag.html")



@app.route("/join_challenge/<title>", methods=["POST"])
def join_challenge_route(title):
    if "username" not in session:
        return redirect(url_for("login"))
    
    username = session["username"]
    join_challenge(graph, username, title)
    
    flash("Připojil(a) jste se k výzvě!")
    return redirect(url_for("home"))



@app.route("/matches")
def matches():
    if "username" not in session:
        return redirect(url_for("login"))

    user_matches = get_matches(graph, session["username"])
    return render_template("matches.html", profiles=user_matches)

@app.route("/archive")
def archive():
    archive_data = get_challenge_archive(graph)
    return render_template("archive.html", archive=archive_data)

@app.route("/submit_result/<title>", methods=["POST"])
def submit_result(title):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    result = request.form.get("result")
    comment = request.form.get("comment")

    user_node = get_user_node(graph, username)
    challenge_node = graph.evaluate("MATCH (c:Challenge {title: $title}) RETURN c", title=title)

    if challenge_node:
        # Vytvoření vztahu COMPLETED mezi uživatelem a výzvou s výsledkem a komentářem
        completed_rel = Relationship(user_node, "COMPLETED", challenge_node, result=result, comment=comment)
        graph.create(completed_rel)

        # Přidání bodů sluníček a ohýnku za splněnou výzvu
        graph.run("""
            MATCH (u:User {name: $username})
            SET u.fire_points = u.fire_points + 1, u.sun_points = u.sun_points + 1
        """, username=username)

        flash("Výsledek byl úspěšně odeslán a body byly přičteny.")
    
    return redirect(url_for("home"))

@app.route("/challenge/<title>")
def challenge_details(title):
    challenge = graph.run("""
        MATCH (c:Challenge {title: $title})
        RETURN c.title AS title, c.description AS description, c.creator AS creator, c.end_date AS end_date
    """, title=title).data()

    # Pokud výzva existuje, zobrazí její detaily, jinak přesměruje na stránku s výzvami
    if challenge:
        challenge = challenge[0]  # Vezmeme první a jediný výsledek
        return render_template("challenge_details.html", challenge=challenge)
    else:
        flash("Výzva nebyla nalezena.")
        return redirect(url_for("search"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

from py2neo import Graph, Node, Relationship
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from random import choice
from database import init_db, get_user_node, create_sample_data, get_matches, available_matches
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Nastavte silný tajný klíč
graph = Graph("bolt://neo4j:7687", auth=("neo4j", "adminpass"))
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Nastavte složku pro ukládání obrázků
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Funkce na kontrolu přípustných formátů obrázků
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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


def create_challenge(graph, username, title, description, duration, hashtags, image_filename=None):
    created_at = datetime.now()  # Uložení aktuálního času vytvoření
    end_date = created_at + timedelta(days=duration)
    challenge_node = Node("Challenge", title=title, description=description, creator=username, end_date=end_date.isoformat(), created_at=created_at.isoformat())
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
               c.created_at AS created_at,
               CASE WHEN r IS NOT NULL THEN true ELSE false END AS is_joined,
               CASE WHEN cr IS NOT NULL THEN true ELSE false END AS is_completed
        ORDER BY c.end_date DESC
    """, username=username).data()

def get_total_user_count(graph):
    """Získá celkový počet uživatelů."""
    return graph.evaluate("MATCH (u:User) RETURN count(u) AS total_users")

def get_total_challenge_count(graph):
    """Získá celkový počet výzev."""
    return graph.evaluate("MATCH (c:Challenge) RETURN count(c) AS total_challenges")

def get_highest_score_user(graph):
    """Najde uživatele s nejvyšším počtem bodů."""
    result = graph.run("""
        MATCH (u:User)
        RETURN u.name AS username, (u.sun_points + u.fire_points) AS total_points
        ORDER BY total_points DESC
        LIMIT 1
    """).data()
    return result[0] if result else None

def get_current_user_count():
    """Vrací počet aktuálně přihlášených uživatelů."""
    # Toto je jen příklad, skutečné sledování přihlášení by vyžadovalo více logiky nebo jiné řešení.
    # Například můžete sledovat přihlášení v reálném čase prostřednictvím session nebo specifického pole v databázi.
    return len(session)


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

def delete_all_challenges(graph):
    graph.run("MATCH (c:Challenge) DETACH DELETE c")

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
            # Nastavení role admin, pokud je přihlášen administrátor
            session["is_admin"] = (username == "admin")
            flash("Login successful!")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.")
    
    return render_template("login.html")



@app.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    session.pop("is_admin", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    new_name = request.form.get("name") or username  # Pokud není zadáno, ponecháme stávající jméno
    new_password = request.form.get("password")
    new_age = request.form.get("age")

    # Získáme hodnotu hobbies, pokud není zadána, nastavíme prázdný seznam
    hobbies_input = request.form.get("hobbies")
    new_hobbies = hobbies_input.split(",") if hobbies_input else []

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
    """, username=username, new_name=new_name, new_age=int(new_age) if new_age else None, new_hobbies=new_hobbies)

    # Aktualizujte jméno v session, pokud bylo změněno
    if new_name != username:
        session["username"] = new_name

    flash("Profil byl úspěšně aktualizován.")
    return redirect(url_for("user_profile", username=session["username"]))

@app.route("/edit_profile")
def edit_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user_info = get_logged_user_profile(graph, username)
    return render_template("edit_profile.html", profile=user_info)

@app.route("/")
@app.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    logged_user = session["username"]
    logged_user_info = get_logged_user_profile(graph, logged_user)
    challenges = get_all_challenges(graph, logged_user)
    
    # Načtení statistik
    total_user_count = get_total_user_count(graph)
    total_challenge_count = get_total_challenge_count(graph)
    highest_score_user = get_highest_score_user(graph)
    current_user_count = get_current_user_count()
    
    return render_template(
        "home.html",
        profile=logged_user_info,
        challenges=challenges,
        total_user_count=total_user_count,
        total_challenge_count=total_challenge_count,
        highest_score_user=highest_score_user,
        current_user_count=current_user_count
    )


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

    elif search_type == "challenges":
        # Hledání výzev s podobným názvem nebo popisem
        results = graph.run("""
            MATCH (c:Challenge)
            WHERE toLower(c.title) CONTAINS toLower($query) OR toLower(c.description) CONTAINS toLower($query)
            RETURN c.title AS title, c.description AS description, 'challenge' AS type
        """, query=query).data()

    return render_template("search.html", results=results)


@app.route("/profile")
def user_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user_info = get_logged_user_profile(graph, username)

    # Získání probíhajících a splněných výzev
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
        
        # Zpracování nahrání obrázku
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename
        else:
            image_filename = None  # Pokud žádný obrázek není nahrán nebo formát není povolen

        # Vytvoření výzvy s vybranými hashtagy a cestou k obrázku
        create_challenge(graph, session["username"], title, description, duration, hashtags, image_filename)
        flash("Výzva byla úspěšně vytvořena!")
        return redirect(url_for("home"))

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
    moment_image = request.files.get("moment_image")

    image_filename = None
    if moment_image and allowed_file(moment_image.filename):
        image_filename = secure_filename(moment_image.filename)
        moment_image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    user_node = get_user_node(graph, username)
    challenge_node = graph.evaluate("MATCH (c:Challenge {title: $title}) RETURN c", title=title)

    if challenge_node:
        completed_rel = Relationship(user_node, "COMPLETED", challenge_node, result=result, comment=comment, photo=image_filename)
        graph.create(completed_rel)
        
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

@app.route("/delete_all_challenges", methods=["POST"])
def delete_all_challenges():
    # Code to delete all challenges
    graph.run("MATCH (c:Challenge) DETACH DELETE c")
    flash("All test challenges have been deleted.")
    return redirect(url_for("admin"))

@app.route("/admin")
def admin():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("admin.html")

# Route pro smazání bodů všem uživatelům
@app.route("/reset_all_points", methods=["POST"])
def reset_all_points():
    # Nastavení bodů všem uživatelům na nulu
    graph.run("MATCH (u:User) SET u.sun_points = 0, u.fire_points = 0")
    flash("Všem uživatelům byly smazány body.")
    return redirect(url_for("admin"))

# Route pro smazání bodů konkrétnímu uživateli
@app.route("/reset_user_points", methods=["POST"])
def reset_user_points():
    username = request.form.get("username")
    # Nastavení bodů vybranému uživateli na nulu
    result = graph.run("MATCH (u:User {name: $username}) SET u.sun_points = 0, u.fire_points = 0 RETURN u", username=username).data()
    if result:
        flash(f"Body uživatele {username} byly smazány.")
    else:
        flash(f"Uživatel {username} nebyl nalezen.")
    return redirect(url_for("admin"))

@app.route("/upload_profile_picture", methods=["POST"])
def upload_profile_picture():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    profile_image = request.files.get("profile_image")

    if profile_image and allowed_file(profile_image.filename):
        image_filename = secure_filename(profile_image.filename)
        profile_image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
        graph.run("""
            MATCH (u:User {name: $username})
            SET u.profile_image = $image_filename
        """, username=username, image_filename=image_filename)

        flash("Profilový obrázek byl úspěšně nahrán.")
    
    return redirect(url_for("user_profile"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

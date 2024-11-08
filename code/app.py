from py2neo import Graph, Node, Relationship
from flask import Flask, render_template, request, redirect, session, url_for, flash
from random import choice
from database import init_db, get_user_node, create_sample_data, get_matches, available_matches
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Nastavte silný tajný klíč
graph = Graph("bolt://neo4j:7687", auth=("neo4j", "adminpass"))

# Odstraňte funkci mock_data, pokud ji už nebudeme potřebovat
# mock_data(graph)

def create_user(graph, username, password, age, hobbies):
    password_hash = generate_password_hash(password)
    user_node = Node("Person", name=username, password=password_hash, age=age, hobbies=hobbies)
    graph.create(user_node)

def verify_user(graph, username, password):
    user = graph.evaluate("MATCH (user:Person {name: $username}) RETURN user", username=username)
    if user and check_password_hash(user["password"], password):
        return True
    return False

def get_logged_user_profile(graph, username):
    return graph.run(f"""
        MATCH (user:Person)
        WHERE user.name = '{username}'
        RETURN user.name, user.age, user.hobbies
    """).data()[0]

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        age = int(request.form.get("age"))
        hobbies = request.form.get("hobbies").split(",")  # Rozdělte koníčky podle čárek

        # Zkontrolujte, zda uživatel již existuje
        existing_user = graph.evaluate("MATCH (user:Person {name: $username}) RETURN user", username=username)
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
            return redirect(url_for("hello_world"))
        else:
            flash("Invalid username or password.")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/")
@app.route("/home")
def hello_world():
    if "username" not in session:
        return redirect(url_for("login"))

    logged_user = session["username"]
    logged_user_info = get_logged_user_profile(graph, logged_user)
    num_of_matches = len(get_matches(graph, logged_user))
    num_of_available_matches = len(available_matches(graph, logged_user))
    return render_template("home.html", profile=logged_user_info, num_of_matches=num_of_matches, num_of_available_matches=num_of_available_matches)

@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    logged_user = session["username"]
    user_info = get_logged_user_profile(graph, logged_user)
    return render_template("profile.html", profile=user_info)

# Ostatní existující route jako /matches a /search zůstanou beze změny

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

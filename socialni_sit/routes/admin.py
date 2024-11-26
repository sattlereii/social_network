from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db.neo4j_connection import Neo4jConnection

admin_blueprint = Blueprint('admin', __name__)

# Admin Menu
@admin_blueprint.route('/admin_menu')
def admin_menu():
    return render_template('admin_menu.html')


# Smazání všech výzev
@admin_blueprint.route('/delete_all_challenges', methods=['POST'])
def delete_all_challenges():
    conn = Neo4jConnection()
    conn.query("MATCH (c:Challenge) DETACH DELETE c")
    conn.close()
    flash("All challenges have been deleted.", "success")
    return redirect(url_for('admin.admin_menu'))

# Smazání konkrétní výzvy
@admin_blueprint.route('/delete_challenge', methods=['POST'])
def delete_challenge():
    challenge_id = request.form['challenge_id']
    conn = Neo4jConnection()
    conn.query("MATCH (c:Challenge {id: $id}) DETACH DELETE c", {'id': challenge_id})
    conn.close()
    flash(f"Challenge with ID {challenge_id} has been deleted.", "success")
    return redirect(url_for('admin.admin_menu'))

# Reset bodů všem uživatelům
@admin_blueprint.route('/reset_all_points', methods=['POST'])
def reset_all_points():
    conn = Neo4jConnection()
    conn.query("MATCH (u:User) SET u.points = 0")
    conn.close()
    flash("All users' points have been reset to 0.", "success")
    return redirect(url_for('admin.admin_menu'))

# Reset bodů konkrétnímu uživateli
@admin_blueprint.route('/reset_user_points', methods=['POST'])
def reset_user_points():
    username = request.form['username']
    conn = Neo4jConnection()
    conn.query("MATCH (u:User {username: $username}) SET u.points = 0", {'username': username})
    conn.close()
    flash(f"Points for user {username} have been reset to 0.", "success")
    return redirect(url_for('admin.admin_menu'))

# Pozastavit možnost přihlášení konkrétnímu uživateli
@admin_blueprint.route('/suspend_user', methods=['POST'])
def suspend_user():
    username = request.form['username']
    conn = Neo4jConnection()
    conn.query("MATCH (u:User {username: $username}) SET u.suspended = true", {'username': username})
    conn.close()
    flash(f"User {username} has been suspended from logging in.", "success")
    return redirect(url_for('admin.admin_menu'))

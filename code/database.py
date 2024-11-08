from py2neo import Graph, Node, Relationship

# Inicializace připojení k Neo4j databázi
def init_db():
    # Nastavte připojení k Neo4j databázi
    return Graph("bolt://neo4j:7687", auth=("neo4j", "adminpass"))

# Funkce pro získání uzlu uživatele podle jména
def get_user_node(graph, username):
    return graph.nodes.match("Person", name=username).first()

# Funkce pro vytvoření základních dat (uživatelů a vztahů)
def create_sample_data(graph):
    users_data = [
        {"name": "Pepa", "age": 34, "hobbies": ["programming", "running"]},
        {"name": "Jana", "age": 30, "hobbies": ["cats", "running"]},
        {"name": "Michal", "age": 38, "hobbies": ["partying", "cats"]},
        {"name": "Alena", "age": 32, "hobbies": ["kids", "cats"]},
        {"name": "Richard", "age": 33, "hobbies": ["partying", "cats"]}
    ]
    relationships_data = [
        ("Pepa", "LIKES", "Jana"),
        ("Jana", "LIKES", "Pepa"),
        ("Michal", "LIKES", "Alena"),
        ("Alena", "DISLIKES", "Michal"),
        ("Richard", "LIKES", "Alena")
    ]

    # Vytvoření uživatelských uzlů
    for user_data in users_data:
        user = Node("Person", **user_data)
        graph.merge(user, "Person", "name")

    # Vytvoření vztahů mezi uživateli
    for u1, rel, u2 in relationships_data:
        user1 = get_user_node(graph, u1)
        user2 = get_user_node(graph, u2)
        relationship = Relationship(user1, rel, user2)
        graph.create(relationship)

# Funkce pro získání vzájemných "matches" pro daného uživatele
def get_matches(graph, username):
    return graph.run(f"""
        MATCH (user:Person {{name: '{username}'}})-[:LIKES]->(friend:Person)-[:LIKES]->(user)
        RETURN friend.name AS name, friend.age AS age, friend.hobbies AS hobbies
    """).data()

# Funkce pro získání dostupných uživatelů k matchování
def available_matches(graph, username):
    return graph.run(f"""
        MATCH (user:Person {{name: '{username}'}})
        MATCH (friend:Person)
        WHERE NOT (user)-[:LIKES|DISLIKES]->(friend) AND friend.name <> '{username}'
        RETURN friend.name AS name, friend.age AS age, friend.hobbies AS hobbies
    """).data()

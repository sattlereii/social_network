from neo4j import GraphDatabase
import os

def export_data():
    # Cesta pro ukládání dat
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Smazání starých souborů
    for file in ["users.csv", "challenges.csv", "relationships.csv"]:
        file_path = os.path.join(data_dir, file)
        if os.path.exists(file_path):
            os.remove(file_path)

    # Připojení k Neo4j
    uri = "bolt://neo4j:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "mypassword"))

    with driver.session() as session:
        # Export uživatelů
        session.run("""
            CALL apoc.export.csv.query(
                "MATCH (u:User) RETURN u.username AS username, u.points AS points",
                "data/users.csv", {}
            )
        """)

        # Export výzev
        session.run("""
            CALL apoc.export.csv.query(
                "MATCH (c:Challenge) RETURN c.id AS id, c.name AS name, c.description AS description, c.duration AS duration, c.created_by AS created_by, c.created_at AS created_at",
                "data/challenges.csv", {}
            )
        """)

        # Export relací
        session.run("""
            CALL apoc.export.csv.query(
                "MATCH (u:User)-[r]->(c:Challenge) RETURN u.username AS username, type(r) AS relationship, c.id AS challenge_id, r.result AS result",
                "data/relationships.csv", {}
            )
        """)

    driver.close()
    print("Data successfully exported.")

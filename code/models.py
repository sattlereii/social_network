from py2neo import Node, Relationship
from database import graph  # Předpokládáme, že `graph` je inicializován v `database.py`

class User:
    def __init__(self, name, age, hobbies):
        self.name = name
        self.age = age
        self.hobbies = hobbies

    def save(self):
        user_node = Node("Person", name=self.name, age=self.age, hobbies=self.hobbies)
        graph.merge(user_node, "Person", "name")

    @staticmethod
    def find_by_name(name):
        return graph.nodes.match("Person", name=name).first()

    @staticmethod
    def all():
        return graph.nodes.match("Person").all()

class LikeRelationship:
    @staticmethod
    def create_likes(user1, user2):
        relationship = Relationship(user1, "LIKES", user2)
        graph.create(relationship)

    @staticmethod
    def create_dislikes(user1, user2):
        relationship = Relationship(user1, "DISLIKES", user2)
        graph.create(relationship)

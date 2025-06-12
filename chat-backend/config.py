import mysql.connector
from flask import g
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', '12345'),
    'database': os.getenv('MYSQL_DB', 'chat_app'),
    'autocommit': True
}

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(**DATABASE_CONFIG)
    return g.db

def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()
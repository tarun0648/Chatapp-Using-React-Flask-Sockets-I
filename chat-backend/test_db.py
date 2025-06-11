import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

try:
    connection = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', '12345'),
        database=os.getenv('MYSQL_DB', 'chat_app')
    )
    
    cursor = connection.cursor()
    cursor.execute("DESCRIBE users")
    columns = cursor.fetchall()
    
    print("Database connection successful!")
    print("Users table structure:")
    for column in columns:
        print(f"  {column}")
    
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"Database connection failed: {e}")
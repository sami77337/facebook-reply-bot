import mysql.connector
import os

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=3306,
        user= os.getenv("DB_USER_NAME"),
        password= os.getenv("DB_PASSWORD"),
        database= os.getenv("DB_NAME")
    )

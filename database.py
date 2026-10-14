import mysql.connector

db = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root@SQL',
    database='eshop'
)

cursor = db.cursor()
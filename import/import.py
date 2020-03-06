import csv
import psycopg2

# Creates connection with database and allows commands.
connection = psycopg2.connect("host=ec2-107-22-228-141.compute-1.amazonaws.com dbname=d8u7rj319n10u6 user=eihlqaagoqafiz password=b88014c70e4195f1e91ef436da25435bf45d4986ea49728d363a90bc64931d12")
cur = connection.cursor()

#read books.csv and create books variables for each one of it.
b = open('books.csv')
bReader = csv.reader(b)
for isbn, title, author, year in bReader:
    cur.execute("INSERT INTO books (isbn, title, author, year) VALUES (%s, %s, %s, %s)", (isbn, title, author, year))
connection.commit()
#committed to the database.
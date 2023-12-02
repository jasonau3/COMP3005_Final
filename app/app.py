from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from psycopg2 import pool
import traceback
from flask import session
import secrets

app = Flask(__name__)
secret_key = secrets.token_urlsafe(16)
app.secret_key = secret_key 

# database pool - use this instead of connections since its more efficient
db_pool = psycopg2.pool.SimpleConnectionPool(1, 20,
                                             database="final_dec1",
                                             user="postgres",
                                             password="postgres",
                                             host="localhost",
                                             port="5432")

def get_db_connection():
    return db_pool.getconn()

def release_db_connection(conn):
    db_pool.putconn(conn)

@app.route('/')
def index():
        
    return render_template('index.html')

@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/handle_register', methods=['POST'])
def handle_register():
    session['first_name'] = request.form.get('first_name')
    session['last_name'] = request.form.get('last_name')
    session['fitness_goal'] = request.form.get('fitness_goal')
    session['weight'] = request.form.get('weight')
    session['height'] = request.form.get('height')
    session['age'] = request.form.get('age')

    return redirect(url_for('register2'))

@app.route('/register-2')
def register2():
        return render_template('register-2.html')

@app.route('/handle_register2', methods=['POST'])
def handle_register2():
    username = request.form.get('username')
    password = request.form.get('password')  
    role = request.form.get('role')
    session['username'] = username
    session['password'] = password
    session['role'] = role

    conn = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = "INSERT INTO users (username, user_password, user_role) VALUES (%s, %s, %s )"
        cur.execute(query, (session["username"], session["password"], session["role"])) 

        if role == 'Administrator':
            admin_query = "INSERT INTO administrators (admin_name) VALUES (%s)"
            cur.execute(admin_query, (session['first_name'] + "_" +session['last_name'],))
        elif role == 'Member':
            member_query = "INSERT INTO members (first_name, last_name, fitness_goals, age, weight, height) VALUES (%s, %s, %s, %s, %s, %s)"
            cur.execute(member_query, (session['first_name'], session['last_name'], session['fitness_goal'], session['age'], session['weight'], session['height']))
        elif role == 'Trainer':
            trainer_query = "INSERT INTO trainers (trainer_name) VALUES (%s)"
            cur.execute(trainer_query, (session['first_name'] + "_" +session['last_name'],))

        conn.commit()
        cur.close()
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    finally:
        if conn:
            release_db_connection(conn)
    return redirect(url_for('index'))

@app.route('/login')
def login():
        return render_template('login.html')

@app.route('/handle_login', methods=['POST'])
def handle_login():
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT user_password FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        release_db_connection(conn)

        if user and user[0] == password:
            session['username'] = username
            print("good")
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'
        
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from psycopg2 import pool
import traceback
from flask import session
import secrets
from datetime import datetime

app = Flask(__name__)
secret_key = secrets.token_urlsafe(16)
app.secret_key = secret_key 

# database pool - use this instead of connections since its more efficient
db_pool = psycopg2.pool.SimpleConnectionPool(1, 20,
                                             database="Final_December3",
                                             user="postgres",
                                             password="myPOSTGRES",
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

        query = "INSERT INTO users (username, user_password, user_role) VALUES (%s, %s, %s) RETURNING user_id"
        cur.execute(query, (session["username"], session["password"], session["role"])) 

        # Get user_id for the person who just submitted the query
        user_id = cur.fetchone()[0]

        if role == 'Administrator':
            # Insert into administrators table
            admin_query = "INSERT INTO administrators (admin_name) VALUES (%s) RETURNING admin_id"
            cur.execute(admin_query, (session['first_name'] + "_" +session['last_name'],))

            # Get admin_id for the person who just submitted the query
            admin_id = cur.fetchone()[0]

            # Insert into is_admin table
            admin_query = "INSERT INTO is_admin (user_id, admin_id) VALUES (%s, %s)" 
            cur.execute(admin_query, (user_id,admin_id))
        elif role == 'Trainer':
            # Insert into trainers table
            trainer_query = "INSERT INTO trainers (trainer_name) VALUES (%s) RETURNING trainer_id"
            cur.execute(trainer_query, (session['first_name'] + "_" +session['last_name'],))

            # Get trainer_id for the person who just submitted the query
            trainer_id = cur.fetchone()[0]

            # Insert into is_trainer table
            trainer_query = "INSERT INTO is_trainer (user_id, trainer_id) VALUES (%s, %s)"
            cur.execute(trainer_id, (user_id,trainer_id))
        elif role == 'Member':
            # Insert into members table
            member_query = "INSERT INTO members (first_name, last_name, fitness_goals, age, weight, height) VALUES (%s, %s, %s, %s, %s, %s) RETURNING member_id"
            cur.execute(member_query, (session['first_name'], session['last_name'], session['fitness_goal'], session['age'], session['weight'], session['height']))

            # Get member_id for the person who just submitted the query
            member_id = cur.fetchone()[0]

            # Insert into is_member table
            member_query = "INSERT INTO is_member (user_id, member_id) VALUES (%s, %s)"
            cur.execute(member_query, (user_id,member_id))

            # Insert into billing table
            bill_query = "INSERT INTO billing (cost_of_membership, last_date_payed, loyalty_points) VALUES (%s, %s, %s) RETURNING bill_id"
            today_date = datetime.today().strftime('%Y-%m-%d')
            cur.execute(bill_query, (50, today_date, 0))

            # Get bill_id for the person who just submitted the query
            bill_id = cur.fetchone()[0]

            # Insert into has_bill table
            bill_query = "INSERT INTO has_bill (bill_id, member_id) VALUES (%s, %s)"
            cur.execute(bill_query, (bill_id,member_id))

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
    
    
    
@app.route('/ptSignUp')
def ptSignUp():
    #session['username'] = username
    #session['role'] = role
    
    
    
    return render_template('ptSignUp.html')
    
#@app.route('/ptMember', methods=['POST'])
#def ptMember():
    
    
    
    
    
    

if __name__ == '__main__':
    app.run(debug = True)
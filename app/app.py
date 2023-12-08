from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from psycopg2 import pool
import traceback
from flask import session
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)
secret_key = secrets.token_urlsafe(16)
app.secret_key = secret_key 

# database pool - use this instead of connections since its more efficient
db_pool = psycopg2.pool.SimpleConnectionPool(1, 20,
                                             database="Final_December5",
                                             user="postgres",
                                             password="postgres",
                                             host="localhost",
                                             port="5432")

def get_db_connection():
    return db_pool.getconn()

def release_db_connection(conn):
    db_pool.putconn(conn)

# This is the main page for members, trainers or admins
# It checks to see what role you are, and displays information corresponding to you
@app.route('/')
def index():
    if 'username' in session:
        print(session)
        conn = get_db_connection()
        cur = conn.cursor()
        if session['role'] == 'Administrator':
            # get user_id
            cur.execute("SELECT user_id FROM users WHERE username = %s", (session["username"],))
            session["user_id"] = cur.fetchone()[0]

            # get schedules 
            cur.execute("SELECT * FROM classes")
            classes = cur.fetchall()
            print(classes)

            cur.execute("SELECT * FROM personal_training")
            personal_training = cur.fetchall()
            print(personal_training)

            # get room bookings
            cur.execute("SELECT * FROM room_bookings")
            room_bookings = cur.fetchall()
            print(room_bookings)

            # get fitness equipment
            cur.execute("SELECT * FROM fitness_eqp")
            fitness_eqp = cur.fetchall()
            print(fitness_eqp)

            # get billings
            cur.execute("SELECT * FROM billing")
            billings = cur.fetchall()
            print(billings)


            cur.close()
    
            return render_template('index.html', classes=classes, personal_training=personal_training, room_bookings=room_bookings, fitness_eqp=fitness_eqp, billings=billings)
        
        elif session['role'] == 'Trainer':
            # get user_id
            cur.execute("SELECT user_id FROM users WHERE username = %s", (session["username"],))
            session["user_id"] = cur.fetchone()[0]

            # get trainer_id
            cur.execute("SELECT * FROM is_trainer WHERE user_id = %s", (session["user_id"],))
            session['trainer_id'] = cur.fetchone()[0]

            # get schedules for trainer - USING CURRENT TRAINER ID  
            #cur.execute("SELECT * FROM taught_by WHERE trainer_id = %s", (session['trainer_id'],))
            cur.execute("SELECT classes.c_session_id, classes.rating FROM classes, taught_by WHERE classes.c_session_id = taught_by.c_session_id AND taught_by.trainer_id = %s", (session['trainer_id'],))
            
            classes = cur.fetchall()

            cur.execute("SELECT * FROM conducts WHERE trainer_id = %s", (session['trainer_id'],))
            personal_training = cur.fetchall()

            # get trainees
            query = """
            SELECT DISTINCT rt.member_id
            FROM conducts AS c
            JOIN register_training AS rt ON c.p_session_id = rt.p_session_id
            WHERE c.trainer_id = %s;
            """
            cur.execute(query, (session['trainer_id'],))
            trainees = cur.fetchall()

            cur.close()

            return render_template('index.html', classes=classes, personal_training=personal_training, trainees=trainees)
        
        elif session['role'] == 'Member':
            # get user_id
            cur.execute("SELECT user_id FROM users WHERE username = %s", (session["username"],))
            session["user_id"] = cur.fetchone()[0]

            # get member_id
            cur.execute("SELECT * FROM is_member WHERE user_id = %s", (session["user_id"],))
            session['member_id'] = cur.fetchone()[0]

            # get billing id
            cur.execute("SELECT * FROM has_bill WHERE member_id = %s", (session['member_id'],))
            bill_id = cur.fetchone()[0]

            # get billing record
            cur.execute("SELECT * FROM billing WHERE bill_id = %s", (bill_id,))
            my_billings = cur.fetchone()
            print("BILLINGS")
            print(my_billings)
            my_bill_amount = my_billings[1]
            my_bill_date = my_billings[2]
            my_loaylty_points = my_billings[3]

            # get schedules for member - USING CURRENT MEMBER ID
            cur.execute("SELECT * FROM register_training WHERE member_id = %s", (session['member_id'],))
            my_personal_training = cur.fetchall()
            print(my_personal_training)

            cur.execute("SELECT * FROM registers_classes WHERE member_id = %s", (session['member_id'],))
            my_classes = cur.fetchall()
            print(my_classes)

            # get ALL upcoming schedule for member
            # classes NOT registered by the member
            cur.execute("""
                SELECT * 
                FROM classes c
                LEFT JOIN registers_classes rc ON c.c_session_id = rc.c_session_id AND rc.member_id = %s
                WHERE rc.member_id IS NULL
                """, (session["member_id"],))
            classes = cur.fetchall()
            print(classes)

            # personal training sessions NOT registered by the member
            cur.execute("""
                SELECT * 
                FROM personal_training pt
                LEFT JOIN register_training rt ON pt.p_session_id = rt.p_session_id AND rt.member_id = %s
                WHERE rt.member_id IS NULL
                """, (session["member_id"],))
            personal_training = cur.fetchall()
            print(personal_training)

            # get achievements
            cur.execute("""
                SELECT *
                FROM achieved_by ab
                JOIN fitness_achievement fa ON ab.achievement_id = fa.achievement_id
                WHERE ab.member_id = %s""", (session['member_id'],))
            my_achievements = cur.fetchall()
            print(my_achievements)

            cur.close()
            return render_template('index.html', my_billings=my_billings, classes=classes, personal_training=personal_training, my_personal_training=my_personal_training, my_classes=my_classes, my_achievements=my_achievements, my_loaylty_points=my_loaylty_points, my_bill_amount=my_bill_amount, my_bill_date=my_bill_date)
    else:
        return render_template('index.html')

@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/handle_register', methods=['POST'])
def handle_register():
    username = request.form.get('username')
    password = request.form.get('password')  
    role = request.form.get('role')
    session['username'] = username
    session['password'] = password  # need to save for next page
    session['role'] = role

    conn = None

    if role == 'Member':
        return redirect(url_for('register2'))

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = "INSERT INTO users (username, user_password, user_role) VALUES (%s, %s, %s) RETURNING user_id"
        cur.execute(query, (session["username"], session['password'], session["role"])) 
        session.pop('password', None)

        # Get user_id for the person who just submitted the query
        user_id = cur.fetchone()[0]

        print(user_id)
        
        if role == 'Administrator':
            
            # Insert into administrators table
            admin_query = "INSERT INTO administrators (admin_name) VALUES (%s) RETURNING admin_id"
            cur.execute(admin_query, (session['username'],))

            # Get admin_id for the person who just submitted the query
            admin_id = cur.fetchone()[0]

            # Insert into is_admin table
            admin_query = "INSERT INTO is_admin (user_id, admin_id) VALUES (%s, %s)" 
            cur.execute(admin_query, (user_id,admin_id))
        elif role == 'Trainer':
            # Insert into trainers table
            trainer_query = "INSERT INTO trainers (trainer_name) VALUES (%s) RETURNING trainer_id"
            cur.execute(trainer_query, (session['username'],))

            # Get trainer_id for the person who just submitted the query
            trainer_id = cur.fetchone()[0]

            # Insert into is_trainer table
            trainer_query = "INSERT INTO is_trainer (user_id, trainer_id) VALUES (%s, %s)"
            cur.execute(trainer_query, (user_id,trainer_id))

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


@app.route('/register-2')
def register2():
        return render_template('register-2.html')

@app.route('/handle_register2', methods=['POST'])
def handle_register2():
    session['first_name'] = request.form.get('first_name')
    session['last_name'] = request.form.get('last_name')
    session['fitness_goal'] = request.form.get('fitness_goal')
    session['weight'] = request.form.get('weight')
    session['height'] = request.form.get('height')
    session['age'] = request.form.get('age')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = "INSERT INTO users (username, user_password, user_role) VALUES (%s, %s, %s) RETURNING user_id"
        cur.execute(query, (session["username"], session["password"], session["role"])) 
        session.pop('password', None)

        # Get user_id for the person who just submitted the query
        user_id = cur.fetchone()[0]

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
        cur.execute('SELECT user_password, user_role FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        release_db_connection(conn)

        if user and user[0] == password:
            session['username'] = username
            session['role'] = user[1]
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'
    
@app.route('/logout')
def logout():
    session.clear()

    return redirect(url_for('index'))



# Finds (or calculates) all the needed information to create a new booking, and adds it to the database
def create_new_booking(conn):
    try:
        cur = conn.cursor()

        # Calculate the start and end times
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        formatted_start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
        formatted_end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')

        # Make a new booking
        booking_query = "INSERT INTO room_bookings (room_number, start_time, end_time) VALUES (%s, %s, %s) RETURNING booking_id"
        cur.execute(booking_query, (1, formatted_start_time, formatted_end_time))

        booking_id = cur.fetchone()[0]
        conn.commit()
        return booking_id

    except Exception as e:
        print("Error creating booking:", e)
        raise  # Re-raise the exception to handle it in the calling function

    finally:
        cur.close()



# (Only accessible by the administrator)
# Adds a new class into the database with the given information
@app.route('/add_class')
def add_class():
    if 'username' not in session or session['role'] != 'Administrator':
        return redirect(url_for('index'))

    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Create a new booking
        booking_id = create_new_booking(conn)

        # Insert into classes table
        class_query = "INSERT INTO classes (rating, c_session_date, c_booking_id) VALUES (%s, %s, %s) RETURNING c_session_id"
        cur.execute(class_query, (0, datetime.today().strftime('%Y-%m-%d'), booking_id))

        new_class_id = cur.fetchone()[0]
        
        
        # Get a list of all available trainers for the admin
        query = "SELECT * FROM trainers"
        cur.execute(query)
        
        trainers = cur.fetchall()

        conn.commit()
        
        
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

    return render_template('class_details.html', class_id=new_class_id, trainers=trainers, sent_from="addClass")



# (Only accessible by the administrator)
# Adds a new personal training session into the database with the given information
@app.route('/add_training')
def add_training():
    if 'username' not in session or session['role'] != 'Administrator':
        return redirect(url_for('index'))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Create a new booking
        booking_id = create_new_booking(conn)

        # Insert into training table
        training_query = "INSERT INTO personal_training (p_session_date, p_booking_id, notes) VALUES (%s, %s, %s) RETURNING p_session_id"
        cur.execute(training_query, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), booking_id, "N/A"))

        new_training_id = cur.fetchone()[0]
        
        
        # Get a list of all available trainers for the admin
        query = "SELECT * FROM trainers"
        cur.execute(query)
        
        trainers = cur.fetchall()
        
       
        conn.commit()
        
        
        
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

    return render_template('training_details.html', training_id=new_training_id, trainers=trainers, sent_from="addPersonalTraining")



# (Only accessible by the administrator)
# Adds a new piece of fitness equipment into the database with the given information
@app.route('/add_equipment')
def add_equipment():
    if 'username' not in session or session['role'] != 'Administrator':
        return redirect(url_for('index'))
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Insert into training table
        query = "INSERT INTO fitness_eqp (recent_maintenance_date) VALUES (%s) RETURNING equipment_id"
        formatted_date = datetime.now().strftime('%Y-%m-%d')
        cur.execute(query, (formatted_date,))

        new_fitness_eqp = cur.fetchone()[0]

        conn.commit()
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)
    
    return redirect(url_for('equipment_details', fitness_eqp_id=new_fitness_eqp))


# This function handles all the logic needed to display information for a given class
@app.route('/class/<int:class_id>')
def class_details(class_id):
    if 'username' not in session:
        return redirect(url_for('index'))
        
    conn = None
    
    # This whole section is just making SQL queries, getting the results, and storing them in a variable
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        
        query = "SELECT trainer_id FROM taught_by WHERE c_session_id=%s"
        cur.execute(query, (class_id,))

        trainer_id = cur.fetchone()[0]
        
        
        query = "SELECT trainer_name FROM trainers WHERE trainer_id=%s"
        cur.execute(query, (trainer_id,))
        
        trainer_name = cur.fetchone()[0]
        
        
        query = "SELECT c_session_date FROM classes WHERE c_session_id=%s"
        cur.execute(query, (class_id,))

        session_date = cur.fetchone()[0]
        
        query = "SELECT rating FROM classes WHERE c_session_id=%s"
        cur.execute(query, (class_id,))

        rating = cur.fetchone()[0]
        
        
        # Join the tables for register_class and members, join on member_id, and take the id, first and last name
        query = "SELECT members.member_id, members.first_name, members.last_name, registers_classes.c_session_id FROM members JOIN registers_classes ON registers_classes.member_id=members.member_id"
        cur.execute(query)

        memberInfo = cur.fetchall()

        conn.commit()
        
        
        # Checks to see if the user is registered in the current class
        registered = False
        
        if session["role"] == "Member":
            for data in memberInfo:
                
                # Checks 2 things:
                # If the member's id is found in the table of members enrolled in a class
                # If the class that member is enrolled in has the same ID as this current class 
                # If both of these are true, the user must be enrolled already
                if (session['member_id'] in data) and (data[3] == class_id):
                    registered = True
                    break
                
                else:
                    registered = False
                    break

    
    # General error handling
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
        
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)


    # If the user is a member, then add in the registered variable
    # If not, registered makes no difference and shouldn't be included
    return render_template('class_details.html', class_id=class_id, trainer_id=trainer_id, trainer_name=trainer_name, session_date=session_date, rating=rating, memberInfo=memberInfo, registered=registered, sent_from="classDetails")


# This function handles the logic for a user registering into a class
@app.route('/class_member_register', methods=['POST'])
def class_member_submit():
    
    class_id = request.form["register_member"]
    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = "INSERT INTO registers_classes (c_session_id, member_id) VALUES (%s, %s)"
        cur.execute(query, (class_id, session["member_id"]))
        
        conn.commit()
    
    
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
        
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)
    
    
    return redirect(url_for('index'))
        
      
# This function handles the logic for a user cancelling their registration into a class
@app.route('/class_member_cancel', methods=['POST'])
def class_member_cancel():
    conn = None
    
    # Get the class ID to know which class should be dropped 
    class_id = request.form["cancel_member"]
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = "DELETE FROM registers_classes WHERE registers_classes.c_session_id=%s AND registers_classes.member_id=%s"
        cur.execute(query, (class_id, session["member_id"]))
        
        conn.commit()
    
    
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)
    
    
    return redirect(url_for('index'))

# This function handles the logic for a user registering into a training
@app.route('/register_training_member', methods=['POST'])
def register_training_member():
    
    class_id = request.form["register_training_member"]
    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = "INSERT INTO register_training (p_session_id, member_id) VALUES (%s, %s)"
        cur.execute(query, (class_id, session["member_id"]))
        
        conn.commit()
    
    
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
        
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)
    
    
    return redirect(url_for('index'))
        
      
# This function handles the logic for a user cancelling their registration into a personal training
@app.route('/cancel_training_member', methods=['POST'])
def cancel_training_member():
    conn = None
    
    # Get the class ID to know which class should be dropped 
    class_id = request.form["cancel_training_member"]
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = "DELETE FROM register_training WHERE register_training.p_session_id=%s AND register_training.member_id=%s"
        cur.execute(query, (class_id, session["member_id"]))
        
        conn.commit()
    
    
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)
    
    
    return redirect(url_for('index'))

# This function handles the logic for an admin creating a class
# Since the class was already made earlier, this gives the admin the ability to choose a trainer to be in charge
@app.route('/add_trainer_admin', methods=['POST'])
def add_trainer_admin():
    conn = None
    
    class_id = request.form["newClass"]
    trainer_id = request.form["classTrainer"]
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Add this trainer to the table, showing that this trainer is in charge of this class
        query = "INSERT INTO taught_by (trainer_id, c_session_id) VALUES (%s, %s)"
        cur.execute(query, (trainer_id, class_id))
        
        conn.commit()
    
    
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)
    
    
    return redirect(url_for('index'))



# This function handles all the logic needed to display information for a given personal training session
@app.route('/training/<int:training_id>')
def training_details(training_id):
    if 'username' not in session:
        return redirect(url_for('index'))

    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = "SELECT trainer_id FROM conducts WHERE p_session_id=%s"
        cur.execute(query, (training_id,))

        trainer_id = cur.fetchone()[0]
        
        query = "SELECT trainer_name FROM trainers WHERE trainer_id=%s"
        cur.execute(query, (trainer_id,))

        trainer_name = cur.fetchone()[0]
        
        query = "SELECT p_session_date FROM personal_training WHERE p_session_id=%s"
        cur.execute(query, (training_id,))

        session_date = cur.fetchone()[0]

        # Join the tables for register_training and members, join on member_id, and take the id, first and last name
        query = "SELECT members.member_id, members.first_name, members.last_name, register_training.p_session_id FROM members JOIN register_training ON register_training.member_id=members.member_id"
        cur.execute(query)

        memberInfo = cur.fetchall()

        conn.commit()

        # Checks to see if the user is registered in the current training
        registered = False
        
        if session["role"] == "Member":
            for data in memberInfo:
                
                # Checks 2 things:
                # If the member's id is found in the table of members enrolled in a training
                # If the training that member is enrolled in has the same ID as this current training 
                # If both of these are true, the user must be enrolled already
                if (session['member_id'] in data) and (data[3] == training_id):
                    registered = True
                    break
                
                else:
                    registered = False
                    break
    
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)
    
    return render_template('training_details.html', trainer_id=trainer_id, trainer_name=trainer_name, session_date=session_date, training_id=training_id, registered=registered)
    
    
   
   
# This function handles the logic for an admin creating a personal training 
# Since the session was already made earlier, this gives the admin the ability to choose a trainer to be in charge
@app.route('/add_ptrainer_admin', methods=['POST'])
def add_ptrainer_admin():
    conn = None
    
    training_id = request.form["newPTrain"]
    trainer_id = request.form["personalTrainer"]
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Add this trainer to the table, showing that this trainer is in charge of this session
        query = "INSERT INTO conducts (p_session_id, trainer_id) VALUES (%s, %s)"
        cur.execute(query, (training_id, trainer_id))
        
        conn.commit()
    
    
    except Exception as e:
        print("Database not connected or query error")
        print("Error: ", e) 
        traceback.print_exc()  # Print traceback
        return "Error connecting to the database. Please verify the database is running and the credentials are correct."
    
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)
    
    
    return redirect(url_for('index'))
    
    
# This function handles all the logic needed to display information for a given piece of equipment
@app.route('/fitness_eqp/<int:fitness_eqp_id>')
def equipment_details(fitness_eqp_id):
    if 'username' not in session:
        return redirect(url_for('index'))

    return render_template('equipment_details.html', fitness_eqp_id=fitness_eqp_id)


# This function handles all the logic needed to display information for a given billing
@app.route('/billings/<int:billing_id>')
def billing_details(billing_id):
    if 'username' not in session:
        return redirect(url_for('index'))

    return render_template('billing_detail.html', billing_id=billing_id)



if __name__ == '__main__':
    app.run(debug = True)

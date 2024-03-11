from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_mysqldb import MySQL
import bcrypt

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'kejgon'
app.config['MYSQL_PASSWORD'] = 'Password'
app.config['MYSQL_DB'] = 'budget_tracker'

mysql = MySQL(app)

app.secret_key = 'ff93cedce7fbdd43168d6be0145e0952'

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            try:
                if bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                    # Store username and user ID in session
                    session['username'] = username
                    session['user_id'] = user[0]  # Assuming user ID is the first column in the users table
                    return redirect(url_for('dashboard'))
                else:
                    error_message = 'Invalid password'
            except ValueError:
                error_message = 'Error: Invalid Credentials'
        else:
            error_message = 'Invalid username'

        return render_template('signin.html', error_message=error_message)
        
    return render_template('signin.html')


@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']  # Retrieve the username from the session
        return render_template('dashboard.html', username=username)  # Pass the username to the template
    else:
        return redirect(url_for('signin'))  # Redirect to the sign-in page if not logged in
    

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
        gender = request.form['gender']
        date_of_birth = request.form['date_of_birth']

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (username, password, email, gender, date_of_birth) VALUES (%s, %s, %s, %s, %s)',
                       (username, password, email, gender, date_of_birth))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('index'))

    return render_template('signup.html')

    
# Route to display the budget page
@app.route('/budget')
def budget():
    if 'username' in session:
        username = session['username']  # Retrieve the username from the session
        # Retrieve the user_id from the session
        user_id = session.get('user_id')

        # Fetch budget data for the current user from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM budget WHERE user_id = %s", (user_id,))
        budget_data = cur.fetchall()
        cur.close()

        # Pass both username and budget data to the template
        return render_template('budget.html', username=username,budget_data=budget_data)
    else:
        # Redirect to the sign-in page if not logged in
        return redirect(url_for('signin'))


# Route to add a budget item
@app.route('/add_item', methods=['POST'])
# Function to add a budget item
def add_item():
    if request.method == 'POST':
        category = request.form['category']
        amount = request.form['amount']
        item_type = request.form['type']
        user_id = session.get('user_id')  # Retrieve user_id from session

        # Insert data into the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO budget (user_id, category, amount, type) VALUES (%s, %s, %s, %s)",
                    (user_id, category, amount, item_type))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('budget'))
    
@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if request.method == 'POST':
        new_category = request.form['new_category']
        new_amount = request.form['new_amount']
        new_type = request.form['new_type']
        # Update data in the database
        cur = mysql.connection.cursor(dictionary=True)  # Fetch items as dictionaries
        cur.execute("UPDATE budget SET category = %s, amount = %s, type = %s WHERE id = %s",
                    (new_category, new_amount, new_type, item_id))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('budget'))
    else:
        # Fetch the item to be edited from the database
        cur = mysql.connection.cursor(dictionary=True)  # Fetch items as dictionaries
        cur.execute("SELECT * FROM budget WHERE id = %s", (item_id,))
        item = cur.fetchone()
        cur.close()
        return render_template('edit_item.html', item=item)



    
# Route to delete a budget item
@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    # Delete the item from the database
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM budget WHERE id = %s", (item_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('budget'))

    
@app.route('/logout')
def logout():
    # Clear the session data
    session.pop('username', None)
    # Redirect to the sign-in page
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.run(debug=True)

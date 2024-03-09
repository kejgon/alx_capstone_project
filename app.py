from flask import Flask, render_template, request, redirect, url_for, session
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

@app.route('/sigin', methods=['POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password, user['password'].encode('utf-8')):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid username/password combination'

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return f'Welcome {session["username"]}!'
    else:
        return redirect(url_for('index'))
    

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


if __name__ == '__main__':
    app.run(debug=True)

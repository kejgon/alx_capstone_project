from flask import Flask, Response, render_template, request, redirect, url_for, session, abort, jsonify,flash
from decimal import Decimal



from flask_mysqldb import MySQL
import bcrypt
from networkx import generate_adjlist

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
        
        # Fetch budget data for the current user from the database
        user_id = session.get('user_id')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM budget WHERE user_id = %s", (user_id,))
        budget_data = cur.fetchall()
        cur.close()
        
        total_income = 0
        total_expenses = 0
        total_saving = 0
        
        for item in budget_data:
            if item[4] == 'income':
                total_income += item[3]
            elif item[4] == 'expense':
                total_expenses += item[3]
            elif item[4] == 'saving':
                total_saving += item[3]
        
        remaining_balance = total_income - total_expenses
        
        return render_template('dashboard.html', username=username, total_income=total_income, total_expenses=total_expenses, remaining_balance=remaining_balance, total_saving=total_saving)
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

@app.route('/budget')
def budget():
    success_message = request.args.get('success')
    if 'username' in session:
        username = session['username']
        # Retrieve the user_id from the session
        user_id = session.get('user_id')
        # Fetch budget data for the current user from the database
        cur = mysql.connection.cursor()
        page = int(request.args.get('page', 1))  # Get page number from query parameters, default to 1
        per_page = 10  # Number of items per page
        offset = (page - 1) * per_page  # Calculate offset
        cur.execute("SELECT * FROM budget WHERE user_id = %s LIMIT %s OFFSET %s", (user_id, per_page, offset))
        budget_data = cur.fetchall()
        cur.close()
        
        # Check if there are more pages
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM budget WHERE user_id = %s", (user_id,))
        total_items = cur.fetchone()[0]
        cur.close()
        next_page = page + 1 if total_items > page * per_page else None
        prev_page = page - 1 if page > 1 else None
        # Pass both username and budget data to the template
        return render_template('budget.html', username=username, budget_data=budget_data, success_message=success_message, next_page=next_page, prev_page=prev_page)
    else:
        # Redirect to the sign-in page if not logged in
        return redirect(url_for('signin'))
# Route to add a budget item
@app.route('/add_item', methods=['POST'])
# Function to add a budget item
def add_item():
    if request.method == 'POST':
        category = request.form['category']
        amount = Decimal(request.form['amount'])  # Convert amount to Decimal
        item_type = request.form['type']
        user_id = session.get('user_id')  # Retrieve user_id from session
        
        if item_type == 'expense':
            cur = mysql.connection.cursor()
            cur.execute("SELECT SUM(amount) FROM budget WHERE user_id = %s AND type = 'income'", (user_id,))
            total_income = cur.fetchone()[0]
            cur.close()
            
            if total_income is None or total_income == 0:
                flash("Cannot add expense. No income available.", 'delete')
                return redirect(url_for('budget'))
            
            cur = mysql.connection.cursor()
            cur.execute("SELECT SUM(amount) FROM budget WHERE user_id = %s AND type = 'expense'", (user_id,))
            total_expense = cur.fetchone()[0]
            cur.close()
            
            if total_expense is not None and amount > total_income - total_expense:
                flash("Cannot add expense. Expense amount exceeds available income.", 'delete')
                return redirect(url_for('budget'))
        
        # Deduct saving from the total income if it's a saving item
        if item_type == 'saving':
            cur = mysql.connection.cursor()
            cur.execute("SELECT SUM(amount) FROM budget WHERE user_id = %s AND type = 'income'", (user_id,))
            total_income = cur.fetchone()[0]
            cur.close()
            
            if total_income is None:
                flash("Cannot add saving. No income available.", 'delete')
                return redirect(url_for('budget'))
            
            if amount > total_income:
                flash("Cannot add saving. Saving amount exceeds total income.", 'delete')
                return redirect(url_for('budget'))
            
            # Deduct the saving amount from the total income
            remaining_income = total_income - amount
            
            # Update the remaining income in the database
            cur = mysql.connection.cursor()
            cur.execute("UPDATE budget SET amount = %s WHERE user_id = %s AND type = 'income'", (remaining_income, user_id))
            mysql.connection.commit()
            cur.close()
        
        # Insert data into the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO budget (user_id, category, amount, type) VALUES (%s, %s, %s, %s)",
                    (user_id, category, amount, item_type))
        mysql.connection.commit()
        cur.close()
        flash("Budget item added successfully.", 'success')
        return redirect(url_for('budget'))
    
@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if request.method == 'POST':
        # Handle form submission
        new_category = request.form['new_category']
        new_amount = request.form['new_amount']
        new_type = request.form['new_type']
        # Update data in the database
        cur = mysql.connection.cursor()
        cur.execute("UPDATE budget SET category = %s, amount = %s, type = %s WHERE id = %s",
                    (new_category, new_amount, new_type, item_id))
        mysql.connection.commit()
        cur.close()
        flash('Item updated successfully', 'success')
        return redirect(url_for('budget'))
    else:
        # Fetch the item to be edited from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM budget WHERE id = %s", (item_id,))
        item = cur.fetchone()
        cur.close()
        return render_template('edit_item.html', item=item)
    


@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    # Delete the item from the database
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM budget WHERE id = %s", (item_id,))
    mysql.connection.commit()
    cur.close()
    flash('Item deleted successfully', 'delete')
    return redirect(url_for('budget'))

    
@app.route('/logout')
def logout():
    # Clear the session data
    session.pop('username', None)
    # Redirect to the sign-in page
    return render_template('index.html')

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    if 'username' in session:
        username = session['username']  # Retrieve the username from the session
        
        if request.method == 'POST':
            # Handle form submission
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            category = request.form['category']
            transaction_type = request.form['type']  # Get selected transaction type
            
            # Fetch budget data based on user selections
            cur = mysql.connection.cursor()
            query = "SELECT * FROM budget WHERE user_id = %s"
            params = [session.get('user_id')]
            
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            
            if category:
                query += " AND category = %s"
                params.append(category)
            
            if transaction_type:
                query += " AND type = %s"
                params.append(transaction_type)
            
            cur.execute(query, params)
            budget_data = cur.fetchall()
            cur.close()
            
            # Render the reports page template with filtered data and username
            return render_template('reports.html', budget_data=budget_data, username=username)
        else:
            # Render the reports page template with initial data and username
            return render_template('reports.html', budget_data=[], username=username)
    else:
        # Redirect to the sign-in page if not logged in
        return redirect(url_for('signin'))


@app.route('/export', methods=['POST'])
def export():
    if request.method == 'POST':
        export_format = request.form['export_format']
        
        # Get filtered budget data
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        category = request.form['category']
        transaction_type = request.form['type']
        
        cur = mysql.connection.cursor()
        query = "SELECT * FROM budget WHERE user_id = %s"
        params = [session.get('user_id')]
        
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)
        
        if category:
            query += " AND category = %s"
            params.append(category)
        
        if transaction_type:
            query += " AND type = %s"
            params.append(transaction_type)
        
        cur.execute(query, params)
        budget_data = cur.fetchall()
        cur.close()
        
        if export_format == 'csv':
            # Generate CSV file
            csv_data = "Category,Amount,Type,Date\n"
            for item in budget_data:
                csv_data += f"{item[2]},{item[3]},{item[4]},{item[5]}\n"
            
            return Response(
                csv_data,
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=report.csv'}
            )
        elif export_format == 'pdf':
            # Generate PDF file
            pdf_file = generate_pdf(budget_data)  # You need to define the generate_pdf function
            return Response(
                pdf_file,
                mimetype='application/pdf',
                headers={'Content-Disposition': 'attachment; filename=report.pdf'}
            )

        # Handle other export formats
        return "Unsupported export format"
@app.route('/profile', methods=['GET'])
def profile():
    if 'user_id' in session:
        user_id = session['user_id']
        username = session.get('username', None)  # Get username from session
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        user_dict = {
            'id': user[0],
            'username': user[1],
            'password': user[2],
            'email': user[3],
            'gender': user[4],
            'date_of_birth': user[5]
        }
        return render_template('profile.html', user=user_dict, username=username)  # Pass username to template
    else:
        return redirect(url_for('signin'))
    
@app.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' in session:
        user_id = session['user_id']
        email = request.form['email']
        gender = request.form['gender']
        dob = request.form['dob']
        
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET email = %s, gender = %s, date_of_birth = %s WHERE id = %s", (email, gender, dob, user_id))
        mysql.connection.commit()
        cur.close()
        
        flash("Profile updated successfully.", 'success')  # Add success flash message
        # Redirect to profile page after updating
        return redirect(url_for('profile'))
    else:
        return redirect(url_for('signin'))


if __name__ == '__main__':
    app.run(debug=True)

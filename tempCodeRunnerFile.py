   
@app.route('/budget')
def budget():
    success_message = request.args.get('success')
    if 'username' in session:
        username = session['username']
        # Retrieve the user_id from the session
        user_id = session.get('user_id')
        # Fetch budget data for the current user from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM budget WHERE user_id = %s", (user_id,))
        budget_data = cur.fetchall()
        cur.close()
        # Pass both username and budget data to the template
        return render_template('budget.html', username=username, budget_data=budget_data, success_message=success_message)
    else:
        # Redirect to the sign-in page if not logged in
        return redirect(url_for('signin'))
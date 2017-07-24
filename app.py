from flask import Flask, request, render_template, flash, redirect, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

app.config.from_envvar('BLOG_SETTINGS')

mysql = MySQL(app)

#Index
@app.route('/')
def index():
    return render_template('home.html')

#About
@app.route('/about')
def about():
    return render_template("about.html")

# Articles
@app.route('/articles')
def articles():
    # Create cursor
    with mysql.connection.cursor() as cur:
        # Get Articles
        result = cur.execute('SELECT * FROM articles')
        articles = cur.fetchall()

        if result > 0:
            return render_template('articles.html', articles=articles)
        else:
            msg = 'Articles not found'
            return render_template('articles.html', msg=msg)

# Single article
@app.route('/article/<string:id>/')
def article(id):
    # Create cursor
    with mysql.connection.cursor() as cur:

        # Get Articles
        result = cur.execute('SELECT * FROM articles WHERE id = %s', [id])
        article = cur.fetchone()

    return render_template("article.html", article=article)


# Register form class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField("Email", [validators.Length(min=6, max=50)])
    password = PasswordField("Password", [
        validators.DataRequired(),
        validators.EqualTo("confirm", message="Pass")
    ])
    confirm = PasswordField('Confirm Password')

# User register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        result = cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s,"
                    "%s, %s, %s)", (name, email, username, password))

        # Comit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash("You are now registered can log in", "success")


        return redirect(url_for("login"))
    return render_template('register.html', form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        # Get from fields
        username = request.form['username']
        password_candidate = request.form['password']

        #Create cursor
        with mysql.connection.cursor() as cur:

            #Get user by username
            result = cur.execute('SELECT * FROM users WHERE username = %s', [username])

            if result > 0:
                # Get stored hash
                data = cur.fetchone()
                password = data["password"]

                # Compare passwords
                if sha256_crypt.verify(password_candidate, password):
                    # Passed
                    session['logged_in'] = True
                    session['username'] = username

                    flash('You are now logged in', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Invalid login'
                    return render_template('login.html', error=error)
                # Close connection
            else:
                error = 'Username not found'
                return render_template('login.html', error=error)

    return render_template('login.html')

#Check if user logged in

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You logged out now', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route("/dashboard")
@is_logged_in
def dashboard():
#Create cursor
    with mysql.connection.cursor() as cur:
# Get Articles
        result = cur.execute('SELECT * FROM articles')
        articles = cur.fetchall()

        if result > 0:
            return render_template('dashboard.html', articles=articles)
        else:
            msg = 'Articles not found'
            return render_template('dashboard.html', msg=msg)

# Article form class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=20)])

# Add Article
@app.route("/add_article", methods=["GET", "POST"])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",
                    (title, body, session['username']))

        # Comit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash("Article created", "success")

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

# Edit Article

@app.route("/edit_article/<string:id>", methods=["GET", "POST"])
@is_logged_in
def edit_article(id):
    cur = mysql.connection.cursor()
    # Get Articles bi id
    result = cur.execute('SELECT * FROM articles WHERE id = %s', [id])

    article = cur.fetchone()

    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']


    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        cur = mysql.connection.cursor()

        # Execute
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))

        # Comit to DB
        mysql.connection.commit()

        cur.close()

        flash("Article Updated", "success")

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

#Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    flash("Article Deleted", "success")
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = "secret123"
    app.run(debug=True)


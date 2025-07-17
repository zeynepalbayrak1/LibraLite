from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()  # .env dosyasını yükler

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # .env içindeki SECRET_KEY değerini alır

def get_db_connection():
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    #kitap tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            available INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()
    
def create_users_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()
create_users_table()

#her mailde ödünç kitap alma özel olsun diye
def alter_table_add_borrowed_by():
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE books ADD COLUMN borrowed_by INTEGER')
        conn.commit()
        print("borrowed_by sütunu eklendi.")
    except Exception as e:
        print("borrowed_by sütunu eklenemedi. Muhtemelen zaten var:", e)
    finally:
        conn.close()

alter_table_add_borrowed_by()

def alter_table_add_description():
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE books ADD COLUMN description TEXT')
        conn.commit()
        print("Açıklama sütunu eklendi.")
    except Exception as e:
        print("Açıklama sütunu eklenemedi. Muhtemelen zaten var:", e)
    finally:
        conn.close()

init_db()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('home.html')


@app.route('/index')
def index():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books').fetchall()
    conn.close()
    return render_template('index.html', books=books)

@app.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']

        conn = get_db_connection()
        conn.execute('INSERT INTO books (title, author, year) VALUES (?, ?, ?)',
                     (title, author, year))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM books WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/update/<int:id>', methods=('GET', 'POST'))
def update(id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']

        conn.execute('UPDATE books SET title = ?, author = ?, year = ? WHERE id = ?',
                     (title, author, year, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('update.html', book=book)

@app.route('/borrow/<int:id>')
def borrow(id):
    if 'user_id' not in session:
        flash('Ödünç almak için giriş yapmalısınız.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (id,)).fetchone()
    if book and book['available'] == 1:
        conn.execute('UPDATE books SET available = 0, borrowed_by = ? WHERE id = ?', (session['user_id'], id))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/return/<int:id>')
def return_book(id):
    if 'user_id' not in session:
        flash('İade etmek için giriş yapmalısınız.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (id,)).fetchone()

    if book and book['available'] == 0 and book['borrowed_by'] == session['user_id']:
        conn.execute('UPDATE books SET available = 1, borrowed_by = NULL WHERE id = ?', (id,))
        conn.commit()
    else:
        flash("Bu kitabı sadece ödünç alan kişi iade edebilir.")

    conn.close()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, hashed_password))
            conn.commit()
            flash('Kayıt başarılı! Giriş yapabilirsin.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Bu kullanıcı adı zaten alınmış.')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Giriş başarılı!')
            return redirect(url_for('index'))
        else:
            flash('Kullanıcı adı veya şifre hatalı.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Çıkış yapıldı.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
#可添加、查询图书，待完善借阅功能
#可注册、登录

from flask import Flask, render_template, request, redirect, url_for, flash, session, g
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用于 session 加密

# 数据库初始化
def init_db():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            publisher TEXT,
            category TEXT,
            publication_date TEXT,
            total_copies INTEGER,
            available_copies INTEGER,
            borrow_count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'reader'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            book_id INTEGER,
            borrow_date TEXT,
            return_date TEXT,
            expected_return_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (book_id) REFERENCES books (id)
        )
    ''')
    conn.commit()
    conn.close()

# 数据库连接
def get_db():
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row  # 使返回结果为字典形式
    return conn

# 添加图书
def add_book(title, author, publisher, category, publication_date, total_copies):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO books (title, author, publisher, category, publication_date, total_copies, available_copies)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, author, publisher, category, publication_date, total_copies, total_copies))
    conn.commit()
    conn.close()

# 删除图书
def delete_book(book_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()

# 修改图书信息
def update_book(book_id, title=None, author=None, publisher=None, category=None, publication_date=None, total_copies=None):
    conn = get_db()
    cursor = conn.cursor()
    update_query = 'UPDATE books SET '
    params = []
    if title is not None:
        update_query += 'title = ?, '
        params.append(title)
    if author is not None:
        update_query += 'author = ?, '
        params.append(author)
    if publisher is not None:
        update_query += 'publisher = ?, '
        params.append(publisher)
    if category is not None:
        update_query += 'category = ?, '
        params.append(category)
    if publication_date is not None:
        update_query += 'publication_date = ?, '
        params.append(publication_date)
    if total_copies is not None:
        update_query += 'total_copies = ?, '
        params.append(total_copies)
    update_query = update_query.strip(', ') + ' WHERE id = ?'
    params.append(book_id)
    cursor.execute(update_query, params)
    conn.commit()
    conn.close()

# 获取所有图书
def get_all_books():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()
    conn.close()
    return books

# 获取特定图书
def get_book_by_id(book_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    conn.close()
    return book

# 按条件查询图书
def search_books(title=None, author=None, publisher=None, category=None):
    conn = get_db()
    cursor = conn.cursor()
    query = 'SELECT * FROM books WHERE 1=1'
    params = []
    if title:
        query += ' AND title LIKE ?'
        params.append(f'%{title}%')
    if author:
        query += ' AND author LIKE ?'
        params.append(f'%{author}%')
    if publisher:
        query += ' AND publisher LIKE ?'
        params.append(f'%{publisher}%')
    if category:
        query += ' AND category = ?'
        params.append(category)
    cursor.execute(query, params)
    books = cursor.fetchall()
    conn.close()
    return books

# 添加用户
def add_user(username, password, role='reader'):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        return False
    cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
    conn.commit()
    conn.close()
    return True

# 用户登录
def login(username, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, role FROM users WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()
    return user


# 借阅图书
def borrow_book(user_id, book_id):
    conn = get_db()
    cursor = conn.cursor()
    book_list = get_book_by_id(book_id)
    if book_list and book_list['available_copies'] > 0:
        borrow_date = datetime.now().strftime('%Y-%m-%d')
        expected_return_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')  # 默认借期30天

        cursor.execute('''
            INSERT INTO borrow_records (user_id, book_id, borrow_date, expected_return_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, book_id, borrow_date, expected_return_date))

        new_available_copies = book_list['available_copies'] - 1
        cursor.execute('UPDATE books SET available_copies = ?, borrow_count = borrow_count + 1 WHERE id = ?',
                       (new_available_copies, book_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# 归还图书
def return_book(record_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, book_id, return_date FROM borrow_records WHERE id = ?', (record_id,))
    record = cursor.fetchone()
    if record and not record['return_date']:
        return_date = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('UPDATE borrow_records SET return_date = ? WHERE id = ?', (return_date, record_id))

        cursor.execute('SELECT available_copies FROM books WHERE id = ?', (record['book_id'],))
        available_copies = cursor.fetchone()['available_copies'] + 1
        cursor.execute('UPDATE books SET available_copies = ? WHERE id = ?', (available_copies, record['book_id']))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# 获取用户的借阅记录
def get_user_borrow_records(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT br.id, b.title, br.borrow_date, br.return_date, br.expected_return_date
        FROM borrow_records br
        JOIN books b ON br.book_id = b.id
        WHERE br.user_id = ?
        ORDER BY br.borrow_date DESC
    ''', (user_id,))
    records = cursor.fetchall()
    conn.close()
    return records

# 初始化数据库
@app.before_first_request
def initialize_database():
    init_db()

@app.before_request
def before_request():
    g.logged_in = 'user_id' in session

# 首页
@app.route('/')
def index():
    return render_template('index.html')

# 添加图书
@app.route('/add_books', methods=['GET', 'POST'])
def add_book_route():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        publisher = request.form['publisher']
        category = request.form['category']
        publication_date = request.form['publication_date']
        total_copies = int(request.form['total_copies'])
        add_book(title, author, publisher, category, publication_date, total_copies)
        flash('图书添加成功！', 'success')
        return redirect(url_for('add_book_route'))
    return render_template('add_books.html')

# 查询图书
"""
@app.route('/search_books', methods=['GET', 'POST'])
def search_books_route():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        publisher = request.form['publisher']
        category = request.form['category']
        books = search_books(title, author, publisher, category)
        return render_template('search_books.html', books=books)
    return render_template('search_books.html')



"""

@app.route('/search_books')
def search_books_route():
    # 获取查询参数（如果有）
    search_query = request.args.get('q', '')

    # 查询数据库
    conn = get_db()
    cursor = conn.cursor()

    if search_query:
        cursor.execute('''
            SELECT * FROM books 
            WHERE title LIKE ? OR author LIKE ? OR publisher LIKE ?
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('SELECT * FROM books')

    # 确保获取的是字典列表
    books = [dict(row) for row in cursor.fetchall()]
    conn.close()


    return render_template('search_books.html', books=books)




# 借阅图书
@app.route('/borrow_books', methods=['GET', 'POST'])
def borrow_book_route():
    if request.method == 'POST':
        user_id = session.get('user_id')
        book_id = request.form['book_id']
        if borrow_book(user_id, book_id):
            # 获取借阅记录以获取预期归还日期
            record = get_user_borrow_records(user_id)[0]  # 获取最新的借阅记录
            expected_return_date = record['expected_return_date']
            flash(f'借书成功！请在 {expected_return_date} 前归还。', 'success')
        else:
            flash('借阅失败，图书已借完或不存在！', 'danger')
        return redirect(url_for('borrow_book_route'))
    return render_template('borrow_books.html')

# 用户注册
@app.route('/register', methods=['GET', 'POST'])
def register_route():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  # 可选：允许选择角色（如 'reader' 或 'admin'）
        if add_user(username, password, role):
            flash('注册成功！请登录。', 'success')
            return redirect(url_for('login_route'))
        else:
            flash('用户名已存在！请使用其他用户名。', 'danger')
    return render_template('register.html')

# 添加用户
def add_user(username, password, role='reader'):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        return False
    cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
    conn.commit()
    conn.close()
    return True

# 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = login(username, password)
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            flash('登录成功！', 'success')
            return redirect(url_for('user_records'))  # 修改为跳转到借阅记录页面
        else:
            flash('用户名或密码错误！', 'danger')
    return render_template('login.html')

# 用户借阅记录
@app.route('/user_records')
def user_records():
    user_id = session.get('user_id')
    if user_id:
        records = get_user_borrow_records(user_id)
        return render_template('user_records.html', records=records)
    else:
        flash('请先登录！', 'danger')
        return redirect(url_for('login_route'))

# 归还图书

# 还书
def return_book(record_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, book_id, return_date FROM borrow_records WHERE id = ?', (record_id,))
    record = cursor.fetchone()
    if record and not record['return_date']:  # 如果该记录未归还
        return_date = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('UPDATE borrow_records SET return_date = ? WHERE id = ?', (return_date, record_id))

        # 更新图书可借副本数
        cursor.execute('SELECT available_copies FROM books WHERE id = ?', (record['book_id'],))
        available_copies = cursor.fetchone()['available_copies'] + 1
        cursor.execute('UPDATE books SET available_copies = ? WHERE id = ?', (available_copies, record['book_id']))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# 还书路由
@app.route('/return_book/<int:record_id>', methods=['POST'])
def return_book_route(record_id):
    if return_book(record_id):
        flash('图书已成功归还！', 'success')
    else:
        flash('归还失败，记录不存在或图书已归还！', 'danger')
    return redirect(url_for('user_records'))

if __name__ == '__main__':
    app.run(debug=True) #,port="5060")


    """
    
    
    """
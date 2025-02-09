from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для сессий

# Настройка Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # Ваш email
app.config['MAIL_PASSWORD'] = 'your_email_password'  # Ваш пароль приложения Gmail
mail = Mail(app)

# Настройка токенов для восстановления пароля
serializer = URLSafeTimedSerializer(app.secret_key)

# Функция подключения к БД
def get_db():
    conn = sqlite3.connect('exchange.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn



# Маршрут для страницы входа (ДОБАВЛЕН)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('index'))
        else:
            flash("Неверное имя пользователя или пароль", "error")

    return render_template('login.html')

# Маршрут для регистрации (ДОБАВЛЕН)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                           (username, email, password))
            conn.commit()
            flash('Регистрация успешна! Войдите в систему.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Ошибка: такой пользователь уже существует.', 'error')
        finally:
            conn.close()

    return render_template('register.html')

# Маршрут для главной страницы 
# @app.route('/')
# def index():
#     # Проверяем, авторизован ли пользователь
#     if 'user_id' not in session:
#         return redirect(url_for('login'))  # Перенаправляем на страницу входа, если пользователь не авторизован

#     # Получаем флаг выхода из сессии, чтобы ограничить доступ
#     logged_out = session.get('logged_out', False)  # Если пользователь только что вышел, этот флаг будет True

#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute('SELECT * FROM items')
#     items = cursor.fetchall()
#     conn.close()

#     return render_template('index.html', items=items, logged_out=logged_out)

@app.route('/')
def index():
    # Проверяем, авторизован ли пользователь
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Перенаправляем на страницу входа, если пользователь не авторизован

    # Получаем флаг выхода из сессии, чтобы ограничить доступ
    logged_out = session.get('logged_out', False)  # Если пользователь только что вышел, этот флаг будет True
    session.pop('logged_out', None)  # Удаляем флаг после использования, чтобы не показывать его снова

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    conn.close()

    return render_template('index.html', items=items, logged_out=logged_out)




# Маршрут для главной страницы ВЫХОД
@app.route('/logout', methods=['POST'])
def logout():
    # Обновляем сессию, чтобы оставить пользователя на главной странице с ограничениями
    session.pop('user_id', None)
    session['logged_out'] = True  # Устанавливаем флаг, что пользователь вышел
    return redirect(url_for('index'))  # Перенаправляем на главную страницу

# Страница добавления нового товара
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Если пользователь не залогинен, перенаправить на страницу входа

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        contact = request.form['contact']
        city = request.form['city']
        image_url = request.form['image_url']
        
        user_id = session['user_id']  # Получаем user_id из сессии

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO items (title, description, contact, city, image_url, user_id)
                          VALUES (?, ?, ?, ?, ?, ?)''', (title, description, contact, city, image_url, user_id))
        conn.commit()
        return redirect(url_for('index'))

    return render_template('add_item.html')


# Страница редактирования товара
@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Если пользователь не залогинен, перенаправить на страницу входа

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
    item = cursor.fetchone()

    if item is None or item['user_id'] != session['user_id']:
        return "Вы не можете редактировать этот товар.", 403

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        contact = request.form['contact']
        city = request.form['city']
        
        cursor.execute('''UPDATE items 
                          SET title = ?, description = ?, contact = ?, city = ? 
                          WHERE id = ?''', (title, description, contact, city, item_id))
        conn.commit()
        return redirect(url_for('index'))

    return render_template('edit_item.html', item=item)


# Страница запроса восстановления пароля
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            reset_token = serializer.dumps(email, salt='password-reset')
            reset_link = url_for('reset_password', token=reset_token, _external=True)

            msg = Message('Восстановление пароля', sender='your_email@gmail.com', recipients=[email])
            msg.body = f'Для восстановления пароля перейдите по ссылке: {reset_link}'

            try:
                mail.send(msg)
                flash('Письмо для сброса пароля отправлено на вашу почту.', 'info')
                return redirect(url_for('login'))
            except Exception as e:
                flash(f'Ошибка при отправке письма: {str(e)}', 'error')
        else:
            flash("Пользователь с таким email не найден", 'error')

    return render_template('forgot_password.html')

# Страница сброса пароля
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = serializer.loads(token, salt='password-reset', max_age=3600)
    if not email:
        flash("Ссылка для восстановления пароля недействительна или устарела", 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        new_password_hash = generate_password_hash(new_password)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password = ? WHERE email = ?', (new_password_hash, email))
        conn.commit()
        conn.close()

        flash('Пароль успешно обновлен!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
import os

# Инициализация приложения Flask
app = Flask(__name__, template_folder=os.path.join(os.getcwd(), 'templates'))
app.secret_key = os.urandom(24).hex()

# Настройки Flask-Mail
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='barterx911@gmail.com',
    MAIL_PASSWORD='cwho zojp fibl rvyx'
)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# Функция подключения к БД
def get_db():
    conn = sqlite3.connect('exchange.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Обработчики ошибок
@app.errorhandler(500)
def internal_error(error):
    return "500 Internal Server Error", 500

@app.errorhandler(404)
def not_found_error(error):
    return "404 Not Found", 404

# Маршрут входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('index'))
        flash("Неверное имя пользователя или пароль", "error")
    return render_template('login.html')

# Маршрут регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username, email, password = request.form['username'], request.form['email'], request.form['password']
        city, contact = request.form['city'], request.form['contact']
        password_hash = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        existing_user = cursor.execute('SELECT * FROM users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)', (username, email)).fetchone()

        if existing_user:
            flash('Пользователь с таким именем или email уже существует!', 'error')
        else:
            cursor.execute('INSERT INTO users (username, email, password, city, contact) VALUES (?, ?, ?, ?, ?)',
                           (username, email, password_hash, city, contact))
            conn.commit()
            flash('Регистрация успешна! Войдите в систему.', 'success')  # Это сообщение будет отображаться на странице логина
            return redirect(url_for('login'))
        conn.close()
    return render_template('register.html')


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    return render_template('index.html', items=items, logged_out=session.pop('logged_out', None))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session['logged_out'] = True
    flash("Вы успешно вышли из аккаунта.", 'info')  # Добавляем флеш-сообщение
    return redirect(url_for('index'))


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
        # Добавляем флеш-сообщение, чтобы подтвердить создание товара
        flash("Товар успешно создан!", 'info')

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

        flash("Товар отредактирован!", 'info')
        return redirect(url_for('index'))

    return render_template('edit_item.html', item=item)


@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = get_db()
    product = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    
    if product:  # Проверяем, существует ли товар
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
        flash('Товар успешно удален', 'success')

    conn.close()
    return redirect(url_for('index'))


# Восстановление пароля
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user:
            reset_token = serializer.dumps(email, salt='password-reset')
            reset_link = url_for('reset_password', token=reset_token, _external=True)
            msg = Message('Восстановление пароля', sender='your_email@gmail.com', recipients=[email])
            msg.body = f'Для восстановления пароля перейдите по ссылке: {reset_link}'
            try:
                mail.send(msg)
                flash('Письмо для сброса пароля отправлено.', 'info')
                return redirect(url_for('login'))
            except Exception as e:
                flash(f'Ошибка при отправке письма: {e}', 'error')
        else:
            flash("Email не найден.", 'error')
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Попытка расшифровать email из токена
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except (SignatureExpired, BadTimeSignature):
        flash("Ссылка недействительна или устарела", 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        # Логирование данных формы для отладки
        app.logger.debug(f"Request form: {request.form}")

        # Проверка наличия поля new_password
        if 'new_password' not in request.form:
            flash('Пароль не был передан.', 'error')
            return redirect(url_for('reset_password', token=token))

        # Хеширование нового пароля
        new_password_hash = generate_password_hash(request.form['new_password'])

        # Подключение к базе данных
        conn = get_db()
        conn.execute('UPDATE users SET password = ? WHERE email = ?', (new_password_hash, email))
        conn.commit()

        # Отправка сообщения об успешном изменении пароля
        flash("Пароль успешно изменен.", 'success')
        return redirect(url_for('login'))

    # Отображение страницы сброса пароля
    return render_template('reset_password.html')

if __name__ == '__main__':
    app.run(debug=True)


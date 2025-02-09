import sqlite3

def create_db():
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        city TEXT NOT NULL,
        contact TEXT NOT NULL
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        image_url TEXT,
        contact TEXT NOT NULL,
        city TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item1_id INTEGER NOT NULL,
        item2_id INTEGER NOT NULL,
        user1_id INTEGER NOT NULL,
        user2_id INTEGER NOT NULL,
        date_of_transaction DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item1_id) REFERENCES items(id),
        FOREIGN KEY (item2_id) REFERENCES items(id),
        FOREIGN KEY (user1_id) REFERENCES users(id),
        FOREIGN KEY (user2_id) REFERENCES users(id)
    );
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_db()

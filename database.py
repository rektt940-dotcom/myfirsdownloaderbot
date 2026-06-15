import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'uz',
            quality TEXT DEFAULT 'best'
        )
    ''')
    conn.commit()
    conn.close()

def get_user_settings(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT language, quality FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'language': result[0], 'quality': result[1]}
    else:
        set_user_settings(user_id, 'uz', 'best')
        return {'language': 'uz', 'quality': 'best'}

def set_user_settings(user_id, language=None, quality=None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        if language:
            cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        if quality:
            cursor.execute('UPDATE users SET quality = ? WHERE user_id = ?', (quality, user_id))
    else:
        cursor.execute('INSERT INTO users (user_id, language, quality) VALUES (?, ?, ?)',
                       (user_id, language or 'uz', quality or 'best'))
    conn.commit()
    conn.close()

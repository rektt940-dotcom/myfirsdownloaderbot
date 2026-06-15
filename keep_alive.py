from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

import os
import time
from threading import Thread

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def cleanup_old_files():
    """Har 1 soatda xotirani tekshiradi va qolib ketgan eski videolarni butunlay o'chiradi"""
    while True:
        try:
            if os.path.exists('downloads'):
                now = time.time()
                for f in os.listdir('downloads'):
                    filepath = os.path.join('downloads', f)
                    if os.path.isfile(filepath):
                        # 1 soatdan (3600 sekund) eski fayllarni tozalash
                        if os.stat(filepath).st_mtime < now - 3600:
                            os.remove(filepath)
        except:
            pass
        time.sleep(3600) # 1 soat kutadi

def keep_alive():
    t = Thread(target=run)
    t.start()
    
    cleaner = Thread(target=cleanup_old_files, daemon=True)
    cleaner.start()

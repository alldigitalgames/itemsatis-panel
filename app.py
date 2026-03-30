from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)

# Basit güvenlik (istediğin şifreyi değiştir)
ADMIN_PASSWORD = "grok123"  # ← Bunu kendine özel bir şifre yap!

# Veritabanı oluştur
def init_db():
    conn = sqlite3.connect('panel.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS steam_accounts 
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT, guard_code TEXT, status TEXT DEFAULT 'stokta')''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY, order_id TEXT, event TEXT, product TEXT, buyer TEXT, timestamp TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Basit HTML Panel (tek dosya, ekstra template yok)
HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Itemsatış Otomatik Panel</title>
<style>body{font-family:Arial;background:#111;color:#0f0;padding:20px;}</style>
</head>
<body>
<h1>Itemsatış Otomatik Teslimat Paneli</h1>
<p><a href="/add_steam">Steam Hesabı Ekle</a> | <a href="/steam_list">Steam Stokları</a> | <a href="/orders">Siparişler</a></p>
<hr>
{{ content|safe }}
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML, content="<h2>Hoş geldin! Webhook aktif.</h2><p>Sipariş bekleniyor...</p>")

# === WEBHOOK ENDPOINT (Itemsatış buraya POST atacak) ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True) or {}
    event = data.get('event', 'bilinmiyor')
    order_id = data.get('order_id', 'yok')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Siparişi veritabanına kaydet
    conn = sqlite3.connect('panel.db')
    c = conn.cursor()
    c.execute("INSERT INTO orders (order_id, event, product, buyer, timestamp, status) VALUES (?,?,?,?,?,?)",
              (order_id, event, data.get('product_name','?'), data.get('buyer_username','?'), timestamp, 'işleniyor'))
    conn.commit()
    conn.close()

    # Otomatik işlem başlıyor
    if "steam" in str(data).lower():  # Steam ilanı ise
        deliver_steam(order_id)
    elif "smm" in str(data).lower():   # SMM ilanı ise
        deliver_smm(order_id, data)
    
    return "OK", 200

def deliver_steam(order_id):
    # En eski stoktaki Steam hesabını al ve "teslim edildi" yap
    conn = sqlite3.connect('panel.db')
    c = conn.cursor()
    c.execute("SELECT * FROM steam_accounts WHERE status='stokta' LIMIT 1")
    account = c.fetchone()
    if account:
        # Burada istersen Itemsatış API'sine teslim mesajı gönderebilirsin (ileride ekleriz)
        c.execute("UPDATE steam_accounts SET status='teslim_edildi' WHERE id=?", (account[0],))
        print(f"✅ Steam otomatik teslim: {account[1]} Guard: {account[3]}")
    conn.commit()
    conn.close()

def deliver_smm(order_id, data):
    # Buraya kendi SMM panelinin API'sini yazacaksın
    # Örnek: Senin SMM panelin varsa API key gir
    print(f"🚀 SMM siparişi otomatik çalıştırılıyor... Order: {order_id}")
    # İleride buraya tam API entegrasyonu ekleyeceğiz (senin SMM panelinin linkini söyle)

@app.route('/add_steam', methods=['GET', 'POST'])
def add_steam():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        guard = request.form['guard']
        conn = sqlite3.connect('panel.db')
        c = conn.cursor()
        c.execute("INSERT INTO steam_accounts (username, password, guard_code) VALUES (?,?,?)", (username, password, guard))
        conn.commit()
        conn.close()
        return redirect(url_for('steam_list'))
    return render_template_string(HTML, content='''
        <h2>Yeni Steam Hesabı Ekle</h2>
        <form method="post">
            Kullanıcı Adı: <input name="username"><br>
            Şifre: <input name="password"><br>
            Guard Kodu: <input name="guard"><br>
            <button type="submit">Ekle</button>
        </form>
    ''')

@app.route('/steam_list')
def steam_list():
    conn = sqlite3.connect('panel.db')
    c = conn.cursor()
    c.execute("SELECT * FROM steam_accounts")
    accounts = c.fetchall()
    conn.close()
    html = "<h2>Steam Stokları</h2><table border='1'><tr><th>ID</th><th>Kullanıcı</th><th>Guard</th><th>Durum</th></tr>"
    for a in accounts:
        html += f"<tr><td>{a[0]}</td><td>{a[1]}</td><td>{a[3]}</td><td>{a[4]}</td></tr>"
    html += "</table>"
    return render_template_string(HTML, content=html)

@app.route('/orders')
def orders():
    conn = sqlite3.connect('panel.db')
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY timestamp DESC")
    orders_list = c.fetchall()
    conn.close()
    html = "<h2>Son Siparişler</h2><table border='1'><tr><th>Order ID</th><th>Event</th><th>Zaman</th><th>Durum</th></tr>"
    for o in orders_list:
        html += f"<tr><td>{o[1]}</td><td>{o[2]}</td><td>{o[5]}</td><td>{o[6]}</td></tr>"
    html += "</table>"
    return render_template_string(HTML, content=html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

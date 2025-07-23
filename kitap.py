from datetime import date
from flask import (Flask, render_template_string, request,
                   redirect, url_for, session, flash)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-please'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'kitap.db')
db = SQLAlchemy(app)

# ---------- MODELLER ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)

class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    read_date = db.Column(db.Date, default=date.today)
    pages_start = db.Column(db.Integer, nullable=False)
    pages_end = db.Column(db.Integer, nullable=False)

# ---------- HTML ŞABLONU ----------
TMPL = """
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>Kitap Takip</title>
<link rel="stylesheet"
 href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
<div class="container py-4">
  {% if not session.user_id %}
    <!-- GİRİŞ / KAYIT / ŞİFRE HATIRLATMA -->
    <h2 class="mb-3">Giriş</h2>
    <form method="post" action="{{ url_for('login') }}" class="mb-2">
      <input class="form-control mb-2" name="username" placeholder="Kullanıcı Adı" required>
      <input class="form-control mb-2" type="password" name="password" placeholder="Şifre" required>
      <button class="btn btn-primary">Giriş</button>
    </form>
    <form method="post" action="{{ url_for('register') }}" class="mb-2">
      <button class="btn btn-secondary">Kayıt Ol</button>
    </form>
    <form method="post" action="{{ url_for('forgot') }}">
      <button class="btn btn-warning">Şifremi Unuttum</button>
    </form>
    {% if m %}<div class="alert alert-info mt-2">{{ m }}</div>{% endif %}
  {% else %}
    <!-- ANA UYGULAMA -->
    <div class="d-flex justify-content-between mb-3">
      <h2>Merhaba, {{ session.username }}</h2>
      <a class="btn btn-danger" href="{{ url_for('logout') }}">Çıkış</a>
    </div>

    <!-- Kitap Ekle -->
    <h4>Kitap Ekle</h4>
    <form method="post" action="{{ url_for('add_book') }}" class="row g-2 mb-4">
      <div class="col-auto">
        <input class="form-control" name="name" placeholder="Kitap adı" required>
      </div>
      <div class="col-auto"><button class="btn btn-success">Ekle</button></div>
    </form>

    <!-- Okuma Kaydı Ekle -->
    <h4>Okuma Kaydı Ekle</h4>
    <form method="post" action="{{ url_for('add_reading') }}" class="row g-2 mb-4">
      <div class="col-auto">
        <select class="form-select" name="book_id" required>
          <option value="">Kitap seçin</option>
          {% for b in books %}
            <option value="{{ b.id }}">{{ b.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-auto"><input type="date" class="form-control" name="read_date" value="{{ today }}" required></div>
      <div class="col-auto"><input type="number" class="form-control" name="start" placeholder="Başlangıç sayfa" min="1" required></div>
      <div class="col-auto"><input type="number" class="form-control" name="end" placeholder="Bitiş sayfa" min="1" required></div>
      <div class="col-auto"><button class="btn btn-primary">Kaydet</button></div>
    </form>

    <!-- Kitap Listesi -->
    <h4>Kitaplarım</h4>
    <table class="table table-bordered align-middle">
      <thead class="table-light"><tr><th>Kitap</th><th>Toplam Okunan Sayfa</th><th>Son Sayfa</th><th>Sil</th></tr></thead>
      <tbody>
        {% for row in stats %}
          <tr>
            <td>{{ row.name }}</td>
            <td>{{ row.total }}</td>
            <td>{{ row.last or 0 }}</td>
            <td>
              <form method="post" action="{{ url_for('delete_book', book_id=row.id) }}" onsubmit="return confirm('Kitabı ve tüm okuma kayıtlarını silmek istediğinize emin misiniz?')">
                <button class="btn btn-sm btn-danger">Sil</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>

    <!-- Okuma Geçmişi -->
    <h4>Okuma Geçmişim</h4>
    <table class="table table-bordered align-middle">
      <thead class="table-light"><tr><th>Kitap</th><th>Tarih</th><th>Sayfa Aralığı</th><th>Sil</th></tr></thead>
      <tbody>
        {% for r in readings %}
          <tr>
            <td>{{ r.book.name }}</td>
            <td>{{ r.read_date }}</td>
            <td>{{ r.pages_start }}-{{ r.pages_end }}</td>
            <td>
              <form method="post" action="{{ url_for('delete_reading', rid=r.id) }}" onsubmit="return confirm('Bu okuma kaydını silmek istediğinize emin misiniz?')">
                <button class="btn btn-sm btn-warning">Sil</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% endif %}
</div>
</body>
</html>
"""

# ---------- ROUTELAR ----------
@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template_string(TMPL, m=None)

    user_id = session['user_id']
    books = Book.query.filter_by(user_id=user_id).all()

    # Toplam ve son sayfa verileri
    from sqlalchemy import func
    stats = (db.session.query(
                Book.id,
                Book.name,
                func.coalesce(func.sum(Reading.pages_end - Reading.pages_start + 1), 0).label('total'),
                func.coalesce(func.max(Reading.pages_end), 0).label('last'))
             .outerjoin(Reading, (Reading.book_id == Book.id) & (Reading.user_id == user_id))
             .filter(Book.user_id == user_id)
             .group_by(Book.id)
             .all())

    readings = (Reading.query
                .filter_by(user_id=user_id)
                .join(Book)
                .order_by(Reading.read_date.desc())
                .all())

    return render_template_string(TMPL, books=books, stats=stats,
                                  readings=readings, today=date.today())

# Kullanıcı işlemleri
@app.route('/register', methods=['POST'])
def register():
    u = request.form['username']
    p = request.form['password']
    if not u or not p:
        flash('Kullanıcı adı ve şifre boş olamaz.')
        return redirect(url_for('index'))
    if User.query.filter_by(username=u).first():
        flash('Kullanıcı zaten var.')
        return redirect(url_for('index'))
    db.session.add(User(username=u, password_hash=generate_password_hash(p)))
    db.session.commit()
    flash('Kayıt başarılı, giriş yapabilirsiniz.')
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    u = request.form['username']
    p = request.form['password']
    user = User.query.filter_by(username=u).first()
    if not user or not check_password_hash(user.password_hash, p):
        flash('Hatalı kullanıcı adı veya şifre.')
        return redirect(url_for('index'))
    session['user_id'] = user.id
    session['username'] = user.username
    return redirect(url_for('index'))

@app.route('/forgot', methods=['POST'])
def forgot():
    u = request.form.get('username') or request.form.get('username', '')
    user = User.query.filter_by(username=u).first()
    if not user:
        flash('Böyle bir kullanıcı bulunamadı.')
        return redirect(url_for('index'))
    # Güvenli değil, demo amaçlı
    flash(f'Sizin için sakladığımız şifre hash: {user.password_hash}')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Kitap/okuma CRUD
@app.route('/add_book', methods=['POST'])
def add_book():
    if 'user_id' not in session: return redirect(url_for('index'))
    n = request.form['name'].strip()
    if n:
        db.session.add(Book(user_id=session['user_id'], name=n))
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_reading', methods=['POST'])
def add_reading():
    if 'user_id' not in session: return redirect(url_for('index'))
    b = int(request.form['book_id'])
    d = request.form['read_date']
    s = int(request.form['start'])
    e = int(request.form['end'])
    if s > e:
        flash('Bitiş sayfası başlangıçtan büyük olmalı.')
        return redirect(url_for('index'))
    db.session.add(Reading(user_id=session['user_id'],
                           book_id=b,
                           read_date=d,
                           pages_start=s,
                           pages_end=e))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if 'user_id' not in session: return redirect(url_for('index'))
    Book.query.filter_by(id=book_id, user_id=session['user_id']).delete()
    Reading.query.filter_by(book_id=book_id, user_id=session['user_id']).delete()
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_reading/<int:rid>', methods=['POST'])
def delete_reading(rid):
    if 'user_id' not in session: return redirect(url_for('index'))
    Reading.query.filter_by(id=rid, user_id=session['user_id']).delete()
    db.session.commit()
    return redirect(url_for('index'))

# ---------- BAŞLAT ----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()   # ilk çalıştırmada tabloları oluştur
    app.run(debug=True)
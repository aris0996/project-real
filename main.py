from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keuangan.db'
db = SQLAlchemy(app)

# Model database
class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    jenis = db.Column(db.String(20), nullable=False)  # pemasukan/pengeluaran
    kategori = db.Column(db.String(50), nullable=False)
    jumlah = db.Column(db.Float, nullable=False)
    keterangan = db.Column(db.String(200))

@app.route('/')
def index():
    transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    
    # Kalkulasi total pemasukan dan pengeluaran
    total_pemasukan = sum(t.jumlah for t in transaksi if t.jenis == 'pemasukan')
    total_pengeluaran = sum(t.jumlah for t in transaksi if t.jenis == 'pengeluaran')
    saldo = total_pemasukan - total_pengeluaran
    
    return render_template('index.html', 
                         transaksi=transaksi,
                         total_pemasukan=total_pemasukan,
                         total_pengeluaran=total_pengeluaran,
                         saldo=saldo)

@app.route('/tambah', methods=['POST'])
def tambah_transaksi():
    jenis = request.form['jenis']
    kategori = request.form['kategori']
    jumlah = float(request.form['jumlah'])
    keterangan = request.form['keterangan']
    
    transaksi_baru = Transaksi(jenis=jenis, kategori=kategori, 
                              jumlah=jumlah, keterangan=keterangan)
    db.session.add(transaksi_baru)
    db.session.commit()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
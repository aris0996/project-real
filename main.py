from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import and_
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from io import BytesIO
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Konfigurasi database
if os.environ.get('VERCEL_ENV') == 'production':
    # Production database (PostgreSQL)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    # Development database (SQLite)
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'keuangan.db')

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rahasia')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

KATEGORI_PEMASUKAN = [
    'Gaji',
    'Bonus',
    'Investasi',
    'Penjualan',
    'Hadiah',
    'Lainnya'
]

KATEGORI_PENGELUARAN = [
    'Makanan & Minuman',
    'Transportasi',
    'Belanja',
    'Tagihan',
    'Hiburan',
    'Kesehatan',
    'Pendidikan',
    'Investasi',
    'Lainnya'
]

class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    jenis = db.Column(db.String(20), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    jumlah = db.Column(db.Float, nullable=False)
    keterangan = db.Column(db.String(200))

@app.route('/')
def index():
    try:
        # Ambil parameter filter
        filter_aktif = request.args.get('filter', 'semua')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Query dasar
        query = Transaksi.query

        # Terapkan filter
        if filter_aktif == 'hari':
            today = datetime.now().date()
            query = query.filter(
                and_(
                    Transaksi.tanggal >= today,
                    Transaksi.tanggal < today + timedelta(days=1)
                )
            )
        elif filter_aktif == 'minggu':
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            query = query.filter(
                and_(
                    Transaksi.tanggal >= start_of_week,
                    Transaksi.tanggal < start_of_week + timedelta(days=7)
                )
            )
        elif filter_aktif == 'bulan':
            today = datetime.now().date()
            start_of_month = today.replace(day=1)
            if today.month == 12:
                end_of_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                end_of_month = today.replace(month=today.month + 1, day=1)
            query = query.filter(
                and_(
                    Transaksi.tanggal >= start_of_month,
                    Transaksi.tanggal < end_of_month
                )
            )
        elif start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(
                and_(
                    Transaksi.tanggal >= start,
                    Transaksi.tanggal < end
                )
            )

        # Ambil data transaksi yang sudah difilter
        transaksi = query.order_by(Transaksi.tanggal.desc()).all()
        
        # Hitung total dan persentase
        total_pemasukan = sum(t.jumlah for t in transaksi if t.jenis == 'pemasukan')
        total_pengeluaran = sum(t.jumlah for t in transaksi if t.jenis == 'pengeluaran')
        total_keseluruhan = total_pemasukan + total_pengeluaran
        
        # Hitung persentase (hindari pembagian dengan nol)
        if total_keseluruhan > 0:
            pemasukan_persentase = (total_pemasukan / total_keseluruhan) * 100
            pengeluaran_persentase = (total_pengeluaran / total_keseluruhan) * 100
        else:
            pemasukan_persentase = 0
            pengeluaran_persentase = 0
        
        # Data untuk grafik kategori
        kategori_pemasukan = defaultdict(float)
        kategori_pengeluaran = defaultdict(float)
        
        for t in transaksi:
            if t.jenis == 'pemasukan':
                kategori_pemasukan[t.kategori] += t.jumlah
            else:
                kategori_pengeluaran[t.kategori] += t.jumlah
        
        # Urutkan kategori berdasarkan jumlah
        pemasukan_labels = sorted(kategori_pemasukan.keys(), 
                                key=lambda x: kategori_pemasukan[x], 
                                reverse=True)
        pemasukan_data = [kategori_pemasukan[k] for k in pemasukan_labels]
        
        pengeluaran_labels = sorted(kategori_pengeluaran.keys(), 
                                  key=lambda x: kategori_pengeluaran[x], 
                                  reverse=True)
        pengeluaran_data = [kategori_pengeluaran[k] for k in pengeluaran_labels]
        
        # Data untuk grafik tren
        labels = []
        pemasukan_bulanan = []
        pengeluaran_bulanan = []
        
        # Generate data 6 bulan terakhir
        for i in range(5, -1, -1):
            date = datetime.now() - timedelta(days=30*i)
            month_start = date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            month_trans = query.filter(
                and_(
                    Transaksi.tanggal >= month_start,
                    Transaksi.tanggal < month_end
                )
            ).all()
            
            labels.append(date.strftime('%b %Y'))
            pemasukan_bulanan.append(sum(t.jumlah for t in month_trans if t.jenis == 'pemasukan'))
            pengeluaran_bulanan.append(sum(t.jumlah for t in month_trans if t.jenis == 'pengeluaran'))

        return render_template('home.html',
            transaksi=transaksi,
            total_pemasukan=total_pemasukan,
            total_pengeluaran=total_pengeluaran,
            saldo=total_pemasukan - total_pengeluaran,
            pemasukan_persentase=pemasukan_persentase,
            pengeluaran_persentase=pengeluaran_persentase,
            labels=labels,
            pemasukan_bulanan=pemasukan_bulanan,
            pengeluaran_bulanan=pengeluaran_bulanan,
            pemasukan_labels=pemasukan_labels,
            pemasukan_data=pemasukan_data,
            pengeluaran_labels=pengeluaran_labels,
            pengeluaran_data=pengeluaran_data,
            filter_aktif=filter_aktif,
            start_date=start_date,
            end_date=end_date,
            colors=['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
                   '#858796', '#5a5c69', '#2e59d9', '#17a673', '#2c9faf']
        )

    except Exception as e:
        flash(str(e), 'error')
        return render_template('home.html',
            transaksi=[],
            total_pemasukan=0,
            total_pengeluaran=0,
            saldo=0,
            pemasukan_persentase=0,
            pengeluaran_persentase=0,
            labels=[],
            pemasukan_bulanan=[],
            pengeluaran_bulanan=[],
            pemasukan_labels=[],
            pemasukan_data=[],
            pengeluaran_labels=[],
            pengeluaran_data=[],
            filter_aktif='semua',
            start_date=None,
            end_date=None,
            colors=['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
                   '#858796', '#5a5c69', '#2e59d9', '#17a673', '#2c9faf']
        )

@app.route('/get_kategori/<jenis>')
def get_kategori(jenis):
    if jenis == 'pemasukan':
        return jsonify(KATEGORI_PEMASUKAN)
    else:
        return jsonify(KATEGORI_PENGELUARAN)

@app.route('/transaksi', methods=['GET', 'POST'])
def transaksi():
    if request.method == 'POST':
        try:
            # Ambil data dari form
            jenis = request.form['jenis']
            kategori = request.form['kategori']
            jumlah = float(request.form['jumlah'])
            keterangan = request.form['keterangan']
            
            # Buat transaksi baru
            transaksi = Transaksi(
                jenis=jenis,
                kategori=kategori,
                jumlah=jumlah,
                keterangan=keterangan
            )
            
            # Simpan ke database
            db.session.add(transaksi)
            db.session.commit()
            
            flash('Transaksi berhasil ditambahkan!', 'success')
            return redirect(url_for('transaksi'))
            
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'error')
            return redirect(url_for('transaksi'))
    
    # Ambil semua transaksi untuk ditampilkan
    transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    
    # Gabungkan kategori default dengan kategori yang sudah ada di database
    kategori_dari_db = set()
    for t in transaksi:
        kategori_dari_db.add(t.kategori)
    
    kategori_pemasukan = sorted(set(KATEGORI_PEMASUKAN) | {k for k in kategori_dari_db})
    kategori_pengeluaran = sorted(set(KATEGORI_PENGELUARAN) | {k for k in kategori_dari_db})
    
    return render_template('transaksi.html', 
                         transaksi=transaksi,
                         kategori_pemasukan=kategori_pemasukan,
                         kategori_pengeluaran=kategori_pengeluaran)

@app.route('/edit_transaksi/<int:id>', methods=['GET', 'POST'])
def edit_transaksi(id):
    transaksi = Transaksi.query.get_or_404(id)
    if request.method == 'POST':
        try:
            transaksi.jenis = request.form['jenis']
            transaksi.kategori = request.form['kategori']
            transaksi.jumlah = float(request.form['jumlah'])
            transaksi.keterangan = request.form['keterangan']
            
            db.session.commit()
            flash('Transaksi berhasil diupdate!', 'success')
            return redirect(url_for('transaksi'))
            
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'error')
            return redirect(url_for('transaksi'))
    
    return render_template('edit_transaksi.html', transaksi=transaksi)

@app.route('/hapus_transaksi/<int:id>')
def hapus_transaksi(id):
    try:
        transaksi = Transaksi.query.get_or_404(id)
        db.session.delete(transaksi)
        db.session.commit()
        flash('Transaksi berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
    
    return redirect(url_for('transaksi'))

@app.route('/unduh')
def unduh():
    try:
        # Buat workbook baru
        wb = Workbook()
        ws = wb.active
        ws.title = "Laporan Keuangan"

        # Definisikan style
        header_style = {
            'fill': PatternFill(start_color='366092', end_color='366092', fill_type='solid'),
            'font': Font(bold=True, color='FFFFFF'),
            'border': Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            ),
            'alignment': Alignment(horizontal='center', vertical='center')
        }

        data_style = {
            'border': Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            ),
            'alignment': Alignment(horizontal='left', vertical='center')
        }

        amount_style = {
            'border': Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            ),
            'alignment': Alignment(horizontal='right', vertical='center'),
            'number_format': '#,##0'
        }

        # Set lebar kolom
        ws.column_dimensions['A'].width = 15  # Tanggal
        ws.column_dimensions['B'].width = 15  # Jenis
        ws.column_dimensions['C'].width = 20  # Kategori
        ws.column_dimensions['D'].width = 20  # Jumlah
        ws.column_dimensions['E'].width = 40  # Keterangan

        # Header
        headers = ['Tanggal', 'Jenis', 'Kategori', 'Jumlah', 'Keterangan']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_style['fill']
            cell.font = header_style['font']
            cell.border = header_style['border']
            cell.alignment = header_style['alignment']

        # Data
        transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
        for row, t in enumerate(transaksi, 2):
            # Tanggal
            cell = ws.cell(row=row, column=1, value=t.tanggal)
            cell.border = data_style['border']
            cell.alignment = data_style['alignment']
            cell.number_format = 'DD/MM/YYYY HH:MM'

            # Jenis
            cell = ws.cell(row=row, column=2, value=t.jenis.title())
            cell.border = data_style['border']
            cell.alignment = data_style['alignment']
            cell.font = Font(color='008000' if t.jenis == 'pemasukan' else 'FF0000')

            # Kategori
            cell = ws.cell(row=row, column=3, value=t.kategori)
            cell.border = data_style['border']
            cell.alignment = data_style['alignment']

            # Jumlah
            cell = ws.cell(row=row, column=4, value=t.jumlah)
            cell.border = amount_style['border']
            cell.alignment = amount_style['alignment']
            cell.number_format = amount_style['number_format']
            cell.font = Font(color='008000' if t.jenis == 'pemasukan' else 'FF0000')

            # Keterangan
            cell = ws.cell(row=row, column=5, value=t.keterangan)
            cell.border = data_style['border']
            cell.alignment = data_style['alignment']

        # Tambah ringkasan di bawah
        row = len(transaksi) + 3
        
        # Total Pemasukan
        ws.cell(row=row, column=1, value='Total Pemasukan').font = Font(bold=True)
        total_pemasukan = sum(t.jumlah for t in transaksi if t.jenis == 'pemasukan')
        cell = ws.cell(row=row, column=4, value=total_pemasukan)
        cell.font = Font(bold=True, color='008000')
        cell.number_format = '#,##0'
        
        # Total Pengeluaran
        ws.cell(row=row+1, column=1, value='Total Pengeluaran').font = Font(bold=True)
        total_pengeluaran = sum(t.jumlah for t in transaksi if t.jenis == 'pengeluaran')
        cell = ws.cell(row=row+1, column=4, value=total_pengeluaran)
        cell.font = Font(bold=True, color='FF0000')
        cell.number_format = '#,##0'
        
        # Saldo
        ws.cell(row=row+2, column=1, value='Saldo').font = Font(bold=True)
        cell = ws.cell(row=row+2, column=4, value=total_pemasukan - total_pengeluaran)
        cell.font = Font(bold=True)
        cell.number_format = '#,##0'

        # Simpan ke BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'laporan_keuangan_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

    except Exception as e:
        flash(f'Terjadi kesalahan saat mengunduh: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    if os.environ.get('VERCEL_ENV') == 'production':
        app.run()
    else:
        app.run(debug=True)
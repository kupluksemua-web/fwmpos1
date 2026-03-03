from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Pelanggan(db.Model):
    __tablename__ = 'datapelanggan'

    id = db.Column(db.Integer, primary_key=True)
    nama_pelanggan = db.Column(db.Text, nullable=False)
    nomor_telepon = db.Column(db.Text)
    alamat = db.Column(db.Text)
    catatan_unik = db.Column(db.Text)
    
    # TAMBAHAN KOLOM BARU
    tanggal_input = db.Column(db.Date, default=lambda: datetime.now().date())

    transaksi = db.relationship('Transaksi', backref='pelanggan', lazy=True)

    def __repr__(self):
        return f'<Pelanggan {self.nama_pelanggan} - {self.nomor_telepon}>'


class Produk(db.Model):
    __tablename__ = 'dataproduk'

    id = db.Column(db.Integer, primary_key=True)
    nama_produk = db.Column(db.Text, nullable=False)
    kategori = db.Column(db.Text)
    satuan = db.Column(db.Text)
    harga = db.Column(db.Integer, nullable=False)
    
    # KOLOM BARU: Menyimpan lama hari pengerjaan (contoh: 1, 3, 5)
    waktu_pengerjaan = db.Column(db.Integer, nullable=False, default=1) 

    detail_transaksi = db.relationship('DetailTransaksi', backref='produk', lazy=True)

    def __repr__(self):
        return f'<Produk {self.nama_produk} - {self.waktu_pengerjaan} Hari>'


class Transaksi(db.Model):
    __tablename__ = 'datatransaksi'

    id = db.Column(db.String(50), primary_key=True)
    
    # UBAH: utcnow menjadi now, dan gunakan lambda agar waktu selalu real-time
    tanggal = db.Column(db.Date, default=lambda: datetime.now().date())
    waktu = db.Column(db.Time, default=lambda: datetime.now().time())
    
    diskon = db.Column(db.Integer, default=0)
    total_harga_transaksi = db.Column(db.Integer, nullable=False)
    
    # KOLOM BARU: Sesuai permintaan
    waktu_selesai = db.Column(db.DateTime)
    status = db.Column(db.Text, default='Menunggu')
    status_pembayaran = db.Column(db.Text, default='Belum bayar')

    # Perhatikan: ForeignKey sekarang merujuk ke datapelanggan.id (bukan pid lagi)
    pelanggan_id = db.Column(db.Integer, db.ForeignKey('datapelanggan.id'), nullable=False)
    detail_transaksi = db.relationship('DetailTransaksi', backref='transaksi', lazy=True)

    def __repr__(self):
        return f'<Transaksi #{self.id} | Status: {self.status} | Bayar: {self.status_pembayaran}>'


class DetailTransaksi(db.Model):
    __tablename__ = 'datadetailtransaksi'

    id = db.Column(db.String(50), primary_key=True)
    kuantitas = db.Column(db.Float, nullable=False)
    total_harga_produk = db.Column(db.Integer, nullable=False)

    # PERBAIKAN DI SINI: db.Integer diubah menjadi db.String(50)
    transaksi_id = db.Column(db.String(50), db.ForeignKey('datatransaksi.id'), nullable=False)
    produk_id = db.Column(db.Integer, db.ForeignKey('dataproduk.id'), nullable=False)

    def __repr__(self):
        return f'<Detail: {self.kuantitas}x (Produk ID: {self.produk_id})>'
    
# Tabel Asosiasi untuk Many-to-Many (menghubungkan User dan Role)
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('datauser.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('datarole.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'datarole'
    
    id = db.Column(db.Integer, primary_key=True)
    nama_role = db.Column(db.String(50), unique=True, nullable=False) # Contoh: 'Admin', 'Kasir', 'Owner'

    def __repr__(self):
        return f'<Role {self.nama_role}>'

class User(db.Model):
    __tablename__ = 'datauser'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    # Ubah nama kolom agar lebih deskriptif
    password_hash = db.Column(db.String(255), nullable=False) 

    # Relasi Many-to-Many ke Role
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
        backref=db.backref('users', lazy=True))

    # Fungsi untuk mengubah password teks biasa menjadi hash
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Fungsi untuk mengecek kecocokan password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
    
# Tambahkan model ini untuk merekam jejak status
class RiwayatStatusTransaksi(db.Model):
    __tablename__ = 'datariwayatstatus'

    id = db.Column(db.Integer, primary_key=True)
    
    # Kunci relasi ke Transaksi dan User
    transaksi_id = db.Column(db.String(50), db.ForeignKey('datatransaksi.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('datauser.id'), nullable=False)
    
    # Merekam perubahan
    status_sebelumnya = db.Column(db.Text)
    status_baru = db.Column(db.Text, nullable=False)
    
    # Menggunakan datetime.now agar mencatat jam dan menit spesifik
    waktu_perubahan = db.Column(db.DateTime, default=datetime.now)

    # Relasi balik (Backref) agar mudah memanggil data dari tabel lain
    user = db.relationship('User', backref=db.backref('riwayat_kerja', lazy=True))
    # Relasi transaksi sudah ada di class Transaksi, tapi bisa ditambahkan relasi langsung di sini jika perlu
    transaksi_rel = db.relationship('Transaksi', backref=db.backref('riwayat_status', lazy=True))

    def __repr__(self):
        return f'<Riwayat {self.transaksi_id}: {self.status_sebelumnya} -> {self.status_baru}>'
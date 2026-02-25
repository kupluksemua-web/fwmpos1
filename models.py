from app import db
from datetime import datetime

class Pelanggan(db.Model):
    __tablename__ = 'datapelanggan'

    # Sesuai permintaan: pid diubah menjadi id, name menjadi nama_pelanggan, dsb.
    id = db.Column(db.Integer, primary_key=True)
    nama_pelanggan = db.Column(db.Text, nullable=False)
    nomor_telepon = db.Column(db.Text)
    alamat = db.Column(db.Text)
    catatan_unik = db.Column(db.Text)

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

    id = db.Column(db.Integer, primary_key=True)
    
    # UBAH: utcnow menjadi now, dan gunakan lambda agar waktu selalu real-time
    tanggal = db.Column(db.Date, default=lambda: datetime.now().date())
    waktu = db.Column(db.Time, default=lambda: datetime.now().time())
    
    diskon = db.Column(db.Integer, default=0)
    total_harga_transaksi = db.Column(db.Integer, nullable=False)
    
    # KOLOM BARU: Sesuai permintaan
    waktu_selesai = db.Column(db.Date)
    status = db.Column(db.Text, default='Menunggu')
    status_pembayaran = db.Column(db.Text, default='Belum bayar')

    # Perhatikan: ForeignKey sekarang merujuk ke datapelanggan.id (bukan pid lagi)
    pelanggan_id = db.Column(db.Integer, db.ForeignKey('datapelanggan.id'), nullable=False)
    detail_transaksi = db.relationship('DetailTransaksi', backref='transaksi', lazy=True)

    def __repr__(self):
        return f'<Transaksi #{self.id} | Status: {self.status} | Bayar: {self.status_pembayaran}>'


class DetailTransaksi(db.Model):
    __tablename__ = 'datadetailtransaksi'

    id = db.Column(db.Integer, primary_key=True)
    kuantitas = db.Column(db.Integer, nullable=False)
    total_harga_produk = db.Column(db.Integer, nullable=False)

    transaksi_id = db.Column(db.Integer, db.ForeignKey('datatransaksi.id'), nullable=False)
    produk_id = db.Column(db.Integer, db.ForeignKey('dataproduk.id'), nullable=False)

    def __repr__(self):
        return f'<Detail: {self.kuantitas}x (Produk ID: {self.produk_id})>'
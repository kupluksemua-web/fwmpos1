# Tambahkan timedelta pada bagian import
from datetime import datetime, timedelta

from flask import render_template, request, redirect, url_for, jsonify
from models import Pelanggan, Produk, Transaksi, DetailTransaksi

def register_routes(app, db):
    def get_alphabet_id(n):
        result = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            result = chr(65 + remainder) + result
        return result
    
    @app.route('/')
    def index():
        hari_ini = datetime.now().date()
        
        # SESUAIKAN: waktu_transaksi diganti menjadi tanggal
        # Karena tipe datanya Date, kita bisa langsung menggunakan == (sama dengan)
        transaksi_hari_ini = Transaksi.query.filter(Transaksi.tanggal == hari_ini).all()
        
        return render_template('index.html', transaksi=transaksi_hari_ini)

    @app.route('/tambahcustomer', methods=['GET', 'POST'])
    def tambahcustomer():
        if request.method == 'POST':
            name = request.form.get('name')
            nomortelepon = request.form.get('nomortelepon')
            alamat = request.form.get('alamat')
            catatan = request.form.get('catatan')

            # Validasi Server-side
            if not nomortelepon or not nomortelepon.startswith('08') or not (10 <= len(nomortelepon) <= 13) or not nomortelepon.isdigit():
                return "Validasi Gagal: Nomor telepon harus diawali '08', hanya angka, dan berjumlah 10-13 karakter.", 400

            # SESUAIKAN: Nama parameter diubah mengikuti models (nama_pelanggan, nomor_telepon, catatan_unik)
            pelanggan_baru = Pelanggan(
            nama_pelanggan=name, 
            nomor_telepon=nomortelepon, 
            alamat=alamat, 
            catatan_unik=catatan,
            tanggal_input=datetime.now().date() # Opsional karena sudah ada default
            )
            db.session.add(pelanggan_baru)
            db.session.commit()
            
            return redirect(url_for('detailcustomer', id=pelanggan_baru.id))
        
        return render_template('tambahcustomer.html')

    @app.route('/tambahtransaksi', methods=['GET', 'POST'])
    def tambahtransaksi():
        if request.method == 'POST':
            data = request.get_json()
            pelanggan_id = data.get('pelanggan_id')
            diskon = int(data.get('diskon'))
            keranjang = data.get('keranjang')

            tanggal_sekarang = datetime.now()
            tanggal_hari_ini = tanggal_sekarang.date()
            str_tanggal = tanggal_sekarang.strftime('%Y%m%d')

            jumlah_hari_ini = Transaksi.query.filter(Transaksi.tanggal == tanggal_hari_ini).count()
            urutan_transaksi = jumlah_hari_ini + 1
            id_transaksi_kustom = f"INV/{str_tanggal}/{urutan_transaksi}"

            transaksi_baru = Transaksi(
                id=id_transaksi_kustom,
                pelanggan_id=pelanggan_id,
                tanggal=tanggal_hari_ini, 
                diskon=diskon,
                total_harga_transaksi=0 
            )
            
            total_belanja = 0
            maksimal_hari = 0

            for index, item in enumerate(keranjang, start=1):
                produk_id = item['produk_id']
                jumlah = float(item['jumlah'])
                harga_satuan = int(item['harga'])
                total_harga_produk = jumlah * harga_satuan
                total_belanja += total_harga_produk
                
                produk_db = Produk.query.get(produk_id)
                if produk_db.waktu_pengerjaan > maksimal_hari:
                    maksimal_hari = produk_db.waktu_pengerjaan

                id_detail_kustom = f"{id_transaksi_kustom}-{get_alphabet_id(index)}"

                detail = DetailTransaksi(
                    id=id_detail_kustom,
                    produk_id=produk_id,
                    kuantitas=jumlah,
                    total_harga_produk=total_harga_produk
                )
                transaksi_baru.detail_transaksi.append(detail)
            
            transaksi_baru.total_harga_transaksi = total_belanja - diskon
            transaksi_baru.waktu_selesai = tanggal_hari_ini + timedelta(days=maksimal_hari)

            db.session.add(transaksi_baru)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'redirect_url': url_for('detailtransaksi', id=transaksi_baru.id)
            })

        # --- TAMBAHAN BARIS DI BAWAH INI (UNTUK REQUEST GET) ---
        daftar_pelanggan = Pelanggan.query.all()
        daftar_produk = Produk.query.all()
        return render_template('tambahtransaksi.html', pelanggan=daftar_pelanggan, produk=daftar_produk)

    @app.route('/caricustomer', methods=['GET', 'POST'])
    def caricustomer():
        if request.method == 'POST':
            # SESUAIKAN: Variabel pid_terpilih diganti id_terpilih
            id_terpilih = request.form.get('pelanggan_id')
            
            # SESUAIKAN: URL for memanggil parameter id, bukan pid
            return redirect(url_for('detailcustomer', id=id_terpilih))
        
        semua_pelanggan = Pelanggan.query.all()
        return render_template('caricustomer.html', daftar_pelanggan=semua_pelanggan)
    
    # SESUAIKAN: URL diubah dari <pid> menjadi <id>
    @app.route('/detailcustomer/<path:id>')
    def detailcustomer(id): # Parameter fungsi juga jadi id
        
        # SESUAIKAN: Variabel pid di .get() diganti id
        data_pelanggan = Pelanggan.query.get(id)
        
        return render_template('detailcustomer.html', pelanggan=data_pelanggan)
    
    @app.route('/detailtransaksi/<path:id>')
    def detailtransaksi(id):
        data_transaksi = Transaksi.query.get(id)
        
        if not data_transaksi:
            return "Maaf, Transaksi tidak ditemukan.", 404
            
        return render_template('detailtransaksi.html', transaksi=data_transaksi)

    @app.route('/cetak/<path:id>')
    def cetaktransaksi(id):
        data_transaksi = Transaksi.query.get(id)
        
        if not data_transaksi:
            return "Maaf, Transaksi tidak ditemukan.", 404
            
        return render_template('cetak.html', transaksi=data_transaksi)
    
    @app.route('/editcustomer/<id>', methods=['GET', 'POST'])
    def editcustomer(id):
        pelanggan = Pelanggan.query.get(id)
        if not pelanggan:
            return "Customer tidak ditemukan", 404

        if request.method == 'POST':
            # Ambil data baru dari form
            pelanggan.nama_pelanggan = request.form.get('name')
            pelanggan.nomor_telepon = request.form.get('nomortelepon')
            pelanggan.alamat = request.form.get('alamat')
            pelanggan.catatan_unik = request.form.get('catatan')

            # Validasi nomor telepon (sama seperti saat tambah)
            if not pelanggan.nomor_telepon.startswith('08') or not (10 <= len(pelanggan.nomor_telepon) <= 13):
                return "Nomor telepon tidak valid", 400

            db.session.commit()
            return redirect(url_for('detailcustomer', id=pelanggan.id))

        return render_template('editcustomer.html', pelanggan=pelanggan)
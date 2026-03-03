# Tambahkan timedelta pada bagian import

import requests
import base64
import json
import pytz

from datetime import datetime, timedelta
from functools import wraps

from flask import render_template, request, redirect, url_for, jsonify, session, abort
from models import Pelanggan, Produk, Transaksi, DetailTransaksi, User, Role, RiwayatStatusTransaksi
from sqlalchemy import func, extract
from itsdangerous import URLSafeSerializer


def register_routes(app, db):
    tz_id = pytz.timezone('Asia/Jakarta')
    # Konfigurasi Midtrans (Gunakan Key dari Dashboard Midtrans kamu)
    MIDTRANS_SERVER_KEY = "Mid-server-uGXSrbnLivyH4HeK2iV0GKeZ"
    MIDTRANS_CLIENT_KEY = "Mid-client-CTuU2ZxX4CR0vpJW"
    # Gunakan URL Sandbox untuk testing
    MIDTRANS_SNAP_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions"

    def get_midtrans_snap_token(transaksi):
        # PASTIKAN KEY INI MENGGUNAKAN SERVER KEY SANDBOX MILIKMU
        MIDTRANS_SERVER_KEY = "Mid-server-uGXSrbnLivyH4HeK2iV0GKeZ"
        MIDTRANS_SNAP_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions"

        payload_auth = f"{MIDTRANS_SERVER_KEY}:"
        encoded_auth = base64.b64encode(payload_auth.encode()).decode()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

        # KITA HAPUS "item_details" AGAR TIDAK BENTROK DENGAN DISKON DAN FLOAT (KG)
        payload = {
            "transaction_details": {
                "order_id": transaksi.id,
                "gross_amount": int(transaksi.total_harga_transaksi)
            },
            "customer_details": {
                "first_name": transaksi.pelanggan.nama_pelanggan,
                "phone": transaksi.pelanggan.nomor_telepon
            }
        }

        try:
            response = requests.post(MIDTRANS_SNAP_URL, json=payload, headers=headers)
            if response.status_code == 201:
                return response.json().get('token')
            else:
                print(f"Midtrans Error: {response.text}")
                return None
        except Exception as e:
            print(f"Error Koneksi Midtrans: {e}")
            return None

    def get_alphabet_id(n):
        result = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            result = chr(65 + remainder) + result
        return result
    
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Jika tidak ada sesi 'user_id', lempar kembali ke halaman login
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('index'))

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            
            # Menggunakan check_password untuk memverifikasi hash
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                # Simpan daftar nama role milik user ini ke dalam session
                session['user_roles'] = [role.nama_role for role in user.roles]
                
                return redirect(url_for('index'))
            else:
                return "Validasi Gagal: Username atau Password salah.", 401
                
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        # Hapus data sesi saat logout
        session.pop('user_id', None)
        session.pop('username', None)
        return redirect(url_for('login'))

    # Decorator untuk mengecek spesifik role (bisa menerima lebih dari 1 role)
    def roles_required(*role_names):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    return redirect(url_for('login'))
                
                # Cek apakah user memiliki setidaknya satu dari role yang diizinkan
                user_roles = session.get('user_roles', [])
                if not any(role in user_roles for role in role_names):
                    # Jika tidak punya role yang sesuai, lempar error 403 Forbidden
                    abort(403) 
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    @app.route('/tambahuser', methods=['GET', 'POST'])
    @roles_required('Owner') # Sangat penting: Hanya Owner yang boleh menambah pegawai
    def tambahuser():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            # getlist digunakan karena input role berupa checkbox (bisa pilih lebih dari 1)
            role_ids = request.form.getlist('roles') 
            
            if not username or not password or not role_ids:
                return "Validasi Gagal: Semua kolom wajib diisi dan minimal pilih 1 peran.", 400
                
            # Cek apakah username sudah ada di database
            user_exist = User.query.filter_by(username=username).first()
            if user_exist:
                return "Username sudah terdaftar, silakan gunakan yang lain.", 400
                
            # Buat user baru dan hash password-nya
            user_baru = User(username=username)
            user_baru.set_password(password)
            
            # Tambahkan role ke user yang baru dibuat
            for r_id in role_ids:
                role_db = Role.query.get(r_id)
                if role_db:
                    user_baru.roles.append(role_db)
                    
            db.session.add(user_baru)
            db.session.commit()
            
            # Setelah berhasil, kembalikan ke beranda
            return redirect(url_for('index'))
            
        # UNTUK REQUEST GET: Tampilkan halaman form dan kirim semua role yang tersedia
        semua_role = Role.query.all()
        return render_template('tambahuser.html', daftar_role=semua_role)
    
    @app.route('/kelolauser', methods=['GET', 'POST'])
    @login_required
    @roles_required('Owner') # Hanya Owner yang bisa mereset password
    def kelolauser():
        if request.method == 'POST':
            # Menerima data dari form reset password
            user_id = request.form.get('user_id')
            password_baru = request.form.get('new_password')
            
            user_target = User.query.get(user_id)
            
            # Jika user ditemukan dan password baru diisi
            if user_target and password_baru:
                user_target.set_password(password_baru) # Hash password baru
                db.session.commit()
                # Kembali ke halaman kelola user setelah berhasil
                return redirect(url_for('kelolauser'))
            else:
                return "Gagal: User tidak ditemukan atau password kosong.", 400
                
        # Untuk metode GET: Tampilkan daftar semua pegawai
        semua_user = User.query.all()
        return render_template('kelolauser.html', users=semua_user)
    
    @app.route('/')
    @login_required
    def index():
        hari_ini = datetime.now(tz_id).date()
        
        # SESUAIKAN: waktu_transaksi diganti menjadi tanggal
        # Karena tipe datanya Date, kita bisa langsung menggunakan == (sama dengan)
        transaksi_hari_ini = Transaksi.query.filter(Transaksi.tanggal == hari_ini).all()
        
        return render_template('index.html', transaksi=transaksi_hari_ini)

    @app.route('/tambahcustomer', methods=['GET', 'POST'])
    @roles_required('Owner', 'Admin', 'Kasir')
    def tambahcustomer():
        if request.method == 'POST':
            name = request.form.get('nama')
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
            tanggal_input=datetime.now(tz_id).date() # Opsional karena sudah ada default
            )
            db.session.add(pelanggan_baru)
            db.session.commit()
            
            return redirect(url_for('detailcustomer', id=pelanggan_baru.id))
        
        return render_template('tambahcustomer.html')

    @app.route('/tambahtransaksi', methods=['GET', 'POST'])
    @roles_required('Owner', 'Admin', 'Kasir')
    def tambahtransaksi():
        if request.method == 'POST':
            data = request.get_json()
            pelanggan_id = data.get('pelanggan_id')
            diskon = int(data.get('diskon'))
            keranjang = data.get('keranjang')

            waktu_sekarang_tz = datetime.now(tz_id)
            # Hilangkan info zona waktunya agar SQLite tidak error saat membaca datanya nanti
            waktu_sekarang = waktu_sekarang_tz.replace(tzinfo=None) 

            tanggal_hari_ini = waktu_sekarang.date()
            str_tanggal = waktu_sekarang.strftime('%Y%m%d')
            waktu_masuk_spesifik = waktu_sekarang.time()

            jumlah_hari_ini = Transaksi.query.filter(Transaksi.tanggal == tanggal_hari_ini).count()
            urutan_transaksi = jumlah_hari_ini + 1
            id_transaksi_kustom = f"INV/{str_tanggal}/{urutan_transaksi}"

            # Simpan waktu masuk secara spesifik di sini untuk dicatat di database
            waktu_masuk_spesifik = waktu_sekarang.time()

            transaksi_baru = Transaksi(
                id=id_transaksi_kustom,
                pelanggan_id=pelanggan_id,
                tanggal=tanggal_hari_ini, 
                waktu=waktu_masuk_spesifik, # <-- Set waktu masuk spesifik (jam:menit)
                diskon=diskon,
                total_harga_transaksi=0,
                status='Antri Cuci'
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
            
            # --- LOGIKA BARU UNTUK ESTIMASI SELESAI (JAM & MENIT) ---
            # Menggunakan waktu_sekarang (datetime lengkap dengan jam/menit), bukan tanggal_hari_ini (Date murni)
            transaksi_baru.waktu_selesai = waktu_sekarang + timedelta(days=maksimal_hari)

            db.session.add(transaksi_baru)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'redirect_url': url_for('detailtransaksi', id=transaksi_baru.id)
            })

        daftar_pelanggan = Pelanggan.query.all()
        daftar_produk = Produk.query.all()
        return render_template('tambahtransaksi.html', pelanggan=daftar_pelanggan, produk=daftar_produk)

    @app.route('/caricustomer', methods=['GET', 'POST'])
    @roles_required('Owner', 'Admin', 'Kasir')
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
    @roles_required('Owner', 'Admin', 'Kasir')
    def detailcustomer(id): # Parameter fungsi juga jadi id
        
        # SESUAIKAN: Variabel pid di .get() diganti id
        data_pelanggan = Pelanggan.query.get(id)
        
        return render_template('detailcustomer.html', pelanggan=data_pelanggan)
    
    @app.route('/detailtransaksi/<path:id>')
    @roles_required('Owner', 'Admin', 'Kasir')
    def detailtransaksi(id):
        data_transaksi = Transaksi.query.get(id)
        
        if not data_transaksi:
            return "Maaf, Transaksi tidak ditemukan.", 404
            
        # Membuat Token Rahasia untuk link pelanggan
        # Menggunakan SECRET_KEY dari app.config agar enkripsinya aman
        s = URLSafeSerializer(app.config['SECRET_KEY'])
        token_rahasia = s.dumps(id)
        
        # Membuat URL lengkap (contoh: http://127.0.0.1:5000/cek_nota/xyz123...)
        link_publik = url_for('cek_nota', token=token_rahasia, _external=True)
            
        return render_template('detailtransaksi.html', transaksi=data_transaksi, link_publik=link_publik)

    @app.route('/cek_nota/<token>')
    def cek_nota(token):
        s = URLSafeSerializer(app.config['SECRET_KEY'])
        try:
            # Mencoba menerjemahkan token acak kembali menjadi ID Transaksi
            trx_id = s.loads(token)
        except:
            # Jika token ditebak-tebak atau diubah, akan gagal di sini
            return "Link tidak valid, kadaluarsa, atau rusak.", 400
            
        data_transaksi = Transaksi.query.get(trx_id)
        if not data_transaksi:
            return "Transaksi tidak ditemukan.", 404

        # --- TAMBAHAN UNTUK MIDTRANS ---
        snap_token = None
        
        # PENTING: Masukkan Client Key dari Dashboard Midtrans kamu di sini
        CLIENT_KEY_MIDTRANS = "Mid-client-CTuU2ZxX4CR0vpJW" 

        if data_transaksi.status_pembayaran == 'Belum bayar':
            # Memanggil fungsi request token yang sudah kita bahas sebelumnya
            snap_token = get_midtrans_snap_token(data_transaksi)
            
        # Mengirimkan 3 variabel ke HTML: transaksi, snap_token, dan midtrans_client_key
        return render_template('nota_publik.html', 
                               transaksi=data_transaksi,
                               snap_token=snap_token,
                               midtrans_client_key=CLIENT_KEY_MIDTRANS)
    
    @app.route('/bayar_transaksi', methods=['POST'])
    @roles_required('Owner', 'Admin', 'Kasir')
    def bayar_transaksi():
        data = request.get_json()
        trx_id = data.get('trx_id')
        
        transaksi = Transaksi.query.get(trx_id)
        if not transaksi:
            return jsonify({'status': 'error', 'message': 'Transaksi tidak ditemukan'}), 404
        
        # Ubah status pembayaran menjadi lunas
        transaksi.status_pembayaran = 'Lunas'
        db.session.commit()
        
        return jsonify({'status': 'success'})

    @app.route('/cetak/<path:id>')
    @roles_required('Owner', 'Admin', 'Kasir')
    def cetaktransaksi(id):
        data_transaksi = Transaksi.query.get(id)
        
        if not data_transaksi:
            return "Maaf, Transaksi tidak ditemukan.", 404
            
        return render_template('cetak.html', transaksi=data_transaksi)
    
    @app.route('/editcustomer/<id>', methods=['GET', 'POST'])
    @roles_required('Owner', 'Admin')
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

    @app.route('/updatestatus', methods=['GET', 'POST'])
    @roles_required('Owner', 'Admin', 'Kasir', 'Penyetrika', 'Pencuci', 'Packing')
    def updatestatus():
        if request.method == 'POST':
            data = request.get_json()
            trx_id = data.get('trx_id')
            
            transaksi = Transaksi.query.get(trx_id)
            if not transaksi:
                return jsonify({'status': 'error', 'message': 'Transaksi tidak ditemukan'}), 404
            
            status_lama = transaksi.status
            status_baru = status_lama
            
            # --- LOGIKA PINDAH TAHAP TRANSAKSI ---
            if status_lama == 'Antri Cuci' or status_lama == 'Menunggu':
                status_baru = 'Antri Setrika'
            elif status_lama == 'Antri Setrika':
                status_baru = 'Antri Packing'
            elif status_lama == 'Antri Packing':
                status_baru = 'Siap Diambil'
            elif status_lama == 'Siap Diambil' or status_lama == 'Diproses':
                status_baru = 'Selesai'
            
            # JIKA STATUS BENAR-BENAR BERUBAH, REKAM KE DATABASE
            if status_lama != status_baru:
                transaksi.status = status_baru
                
                # Buat rekam jejak baru
                user_id = session.get('user_id')
                riwayat_baru = RiwayatStatusTransaksi(
                    transaksi_id=transaksi.id,
                    user_id=user_id,
                    status_sebelumnya=status_lama,
                    status_baru=status_baru
                )
                
                db.session.add(riwayat_baru)
                db.session.commit()
                
            return jsonify({'status': 'success', 'new_status': transaksi.status})
            
        # UNTUK REQUEST GET (Menampilkan halaman pertama kali)
        semua_transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc(), Transaksi.waktu.desc()).all()
        return render_template('updatestatus.html', transaksi=semua_transaksi)
    
    @app.route('/profile')
    @login_required
    def profile():
        user_id = session.get('user_id')
        hari_ini = datetime.now(tz_id).date()
        
        # Mengambil batasan waktu dari jam 00:00 sampai 23:59 hari ini
        mulai_hari = tz_id.localize(datetime.combine(hari_ini, datetime.min.time()))
        akhir_hari = tz_id.localize(datetime.combine(hari_ini, datetime.max.time()))
        
        # Ambil semua riwayat milik user ini yang dikerjakan HARI INI
        riwayat_hari_ini = RiwayatStatusTransaksi.query.filter(
            RiwayatStatusTransaksi.user_id == user_id,
            RiwayatStatusTransaksi.waktu_perubahan >= mulai_hari,
            RiwayatStatusTransaksi.waktu_perubahan <= akhir_hari
        ).order_by(RiwayatStatusTransaksi.waktu_perubahan.desc()).all()
        
        # --- TAMBAHAN LOGIKA: Ambil Nama Pelanggan dan Total Kuantitas ---
        for r in riwayat_hari_ini:
            transaksi = Transaksi.query.get(r.transaksi_id)
            if transaksi:
                r.nama_pelanggan = transaksi.pelanggan.nama_pelanggan
                # Hitung total kuantitas item dalam 1 transaksi
                r.jumlah_item = sum(detail.kuantitas for detail in transaksi.detail_transaksi)
            else:
                r.nama_pelanggan = "Tidak Ditemukan"
                r.jumlah_item = 0
        
        # Pisahkan berdasarkan tahap
        rekap_cuci = [r for r in riwayat_hari_ini if r.status_baru == 'Antri Setrika']
        rekap_setrika = [r for r in riwayat_hari_ini if r.status_baru == 'Antri Packing']
        rekap_packing = [r for r in riwayat_hari_ini if r.status_baru == 'Siap Diambil']
        
        return render_template('profile.html', 
                               rekap_cuci=rekap_cuci, 
                               rekap_setrika=rekap_setrika, 
                               rekap_packing=rekap_packing)
    
    @app.route('/cetak_rekap/<tahap>')
    @roles_required('Owner', 'Admin', 'Kasir', 'Penyetrika', 'Pencuci', 'Packing')
    def cetak_rekap(tahap):
        user_id = session.get('user_id')
        username = session.get('username')
        hari_ini = datetime.now(tz_id).date()
        
        mulai_hari = tz_id.localize(datetime.combine(hari_ini, datetime.min.time()))
        akhir_hari = tz_id.localize(datetime.combine(hari_ini, datetime.max.time()))
        
        if tahap == 'cuci':
            target_status = 'Antri Setrika'
            nama_tahap = 'CUCI'
        elif tahap == 'setrika':
            target_status = 'Antri Packing'
            nama_tahap = 'SETRIKA'
        elif tahap == 'packing':
            target_status = 'Siap Diambil'
            nama_tahap = 'PACKING'
        else:
            return "Tahap tidak valid", 400

        riwayat_tugas = RiwayatStatusTransaksi.query.filter(
            RiwayatStatusTransaksi.user_id == user_id,
            RiwayatStatusTransaksi.status_baru == target_status,
            RiwayatStatusTransaksi.waktu_perubahan >= mulai_hari,
            RiwayatStatusTransaksi.waktu_perubahan <= akhir_hari
        ).order_by(RiwayatStatusTransaksi.waktu_perubahan.asc()).all()

        # --- TAMBAHAN LOGIKA: Kalkulasi Item untuk Cetakan ---
        total_semua_item = 0
        for r in riwayat_tugas:
            transaksi = Transaksi.query.get(r.transaksi_id)
            if transaksi:
                r.nama_pelanggan = transaksi.pelanggan.nama_pelanggan
                jml_item = sum(detail.kuantitas for detail in transaksi.detail_transaksi)
                r.jumlah_item = jml_item
                total_semua_item += jml_item
            else:
                r.nama_pelanggan = "Tidak Ditemukan"
                r.jumlah_item = 0

        return render_template('cetak_rekap.html', 
                               riwayat=riwayat_tugas, 
                               nama_tahap=nama_tahap, 
                               username=username, 
                               tanggal=hari_ini,
                               total_semua_item=total_semua_item) # Kirim total item ke template
    
    @app.route('/dashboard', methods=['GET'])
    @roles_required('Owner')
    def dashboard():
        hari_ini = datetime.now(tz_id).date()
        
        # Mengambil parameter tanggal dari URL (jika ada form filter yang di-submit)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Logika Penentuan Rentang Tanggal
        if start_date_str and end_date_str:
            # Jika user memilih tanggal
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            # Default: Dari tanggal 1 bulan ini sampai hari ini
            start_date = hari_ini.replace(day=1)
            end_date = hari_ini

        # 1. TOTAL OMSET (Semua transaksi yang dibuat nota, baik lunas maupun belum)
        total_omset = db.session.query(func.sum(Transaksi.total_harga_transaksi)).filter(
            Transaksi.tanggal >= start_date,
            Transaksi.tanggal <= end_date
        ).scalar() or 0

        # 2. PENDAPATAN LUNAS (Hanya transaksi yang sudah dibayar)
        pendapatan_lunas = db.session.query(func.sum(Transaksi.total_harga_transaksi)).filter(
            Transaksi.tanggal >= start_date,
            Transaksi.tanggal <= end_date,
            Transaksi.status_pembayaran == 'Lunas'
        ).scalar() or 0

        # 3. PIUTANG (Transaksi yang belum dibayar dalam rentang tanggal tersebut)
        piutang = db.session.query(func.sum(Transaksi.total_harga_transaksi)).filter(
            Transaksi.tanggal >= start_date,
            Transaksi.tanggal <= end_date,
            Transaksi.status_pembayaran == 'Belum bayar'
        ).scalar() or 0

        # 4. DATA UNTUK GRAFIK (Dinamis sesuai rentang tanggal)
        label_hari = []
        data_omset = []
        data_pendapatan = []

        # Menghitung selisih hari untuk perulangan grafik
        delta_hari = (end_date - start_date).days
        
        # Batasi maksimal 31 hari untuk grafik agar tampilan tidak terlalu padat
        if delta_hari > 31:
            delta_hari = 31 
            start_date = end_date - timedelta(days=31)

        for i in range(delta_hari + 1):
            tanggal_target = start_date + timedelta(days=i)
            label_hari.append(tanggal_target.strftime('%d %b'))

            # Omset per hari
            omset_harian = db.session.query(func.sum(Transaksi.total_harga_transaksi)).filter(
                Transaksi.tanggal == tanggal_target
            ).scalar() or 0
            data_omset.append(omset_harian)

            # Pendapatan Lunas per hari
            lunas_harian = db.session.query(func.sum(Transaksi.total_harga_transaksi)).filter(
                Transaksi.tanggal == tanggal_target,
                Transaksi.status_pembayaran == 'Lunas'
            ).scalar() or 0
            data_pendapatan.append(lunas_harian)

        return render_template('dashboard.html', 
                               start_date=start_date,
                               end_date=end_date,
                               total_omset=total_omset,
                               pendapatan_lunas=pendapatan_lunas,
                               piutang=piutang,
                               label_hari=label_hari,
                               data_omset=data_omset,
                               data_pendapatan=data_pendapatan)
from app import create_app, db
from models import User, Role

# Panggil fungsi create_app() untuk membuat instance aplikasi Flask
app = create_app()

def buat_data_awal():
    # Gunakan app_context agar database tahu aplikasi mana yang sedang berjalan
    with app.app_context():
        # Memastikan semua tabel sudah dibuat di database
        db.create_all()

        print("Memeriksa Role...")
        # Daftar role yang akan digunakan di FWM Laundry
        daftar_role = ['Owner', 'Admin', 'Kasir']
        
        for nama_role in daftar_role:
            role_exist = Role.query.filter_by(nama_role=nama_role).first()
            if not role_exist:
                role_baru = Role(nama_role=nama_role)
                db.session.add(role_baru)
                print(f"[-] Role '{nama_role}' berhasil ditambahkan.")
            else:
                print(f"[v] Role '{nama_role}' sudah ada.")
        
        # Simpan perubahan role ke database terlebih dahulu
        db.session.commit()

        print("\nMemeriksa Akun Owner...")
        # Cek apakah username 'admin_kiel' sudah ada
        user_exist = User.query.filter_by(username='admin_kiel').first()
        
        if not user_exist:
            # Membuat user baru
            user_baru = User(username='admin_kiel')
            # Menggunakan fungsi set_password dari Models.py untuk melakukan hashing
            user_baru.set_password('rahasialaundry123') 
            
            # Mengambil role 'Owner' dari database
            role_owner = Role.query.filter_by(nama_role='Owner').first()
            
            # Memasukkan role Owner ke dalam akun user_baru
            if role_owner:
                user_baru.roles.append(role_owner)
            
            db.session.add(user_baru)
            db.session.commit()
            print("[-] Akun Owner berhasil dibuat!")
            print("    Username : admin_kiel")
            print("    Password : rahasialaundry123")
        else:
            print("[v] Akun Owner sudah tersedia.")

if __name__ == '__main__':
    buat_data_awal()
    print("\nSetup selesai! Silakan jalankan server Flask dan coba login.")
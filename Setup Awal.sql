-- SQLite
INSERT INTO dataproduk (nama_produk, kategori, satuan, harga, waktu_pengerjaan)
VALUES 
    ('Cuci Setrika 3 Hari', 'Kiloan', 'Kg', 7500, 3),
    ('Cuci Setrika 2 Hari', 'Kiloan', 'Kg', 8500, 2),
    ('Cuci Setrika 24 Jam', 'Kiloan', 'Kg', 10500, 1),
    ('Cuci Setrika 8 Jam', 'Kiloan', 'Kg', 12500, 1),
    ('Cuci Lipat 3 Hari', 'Kiloan', 'Kg', 5500, 3),
    ('Cuci Lipat 2 Hari', 'Kiloan', 'Kg', 6500, 2),
    ('Cuci Lipat 24 Jam', 'Kiloan', 'Kg', 8500, 1),
    ('Cuci Lipat 8 Jam', 'Kiloan', 'Kg', 9000, 1),
    ('Setrika Aja 4 Hari', 'Kiloan', 'Kg', 4500, 4),
    ('Setrika Aja 3 Hari', 'Kiloan', 'Kg', 5500, 3),
    ('Setrika Aja 2 Hari', 'Kiloan', 'Kg', 6500, 2),
    ('Setrika Aja 24 Jam', 'Kiloan', 'Kg', 7500, 1),
    ('Setrika Aja 8 Jam', 'Kiloan', 'Kg', 9000, 1);

INSERT INTO dataproduk (nama_produk, kategori, satuan, harga, waktu_pengerjaan)
VALUES 
    ('SATUAN DUMMY', 'Satuan', 'Pcs', 10000, 3);

SELECT * FROM dataproduk;

DELETE FROM dataproduk;

DELETE FROM sqlite_sequence WHERE name='dataproduk';

INSERT INTO datarole (nama_role) 
VALUES 
    ('Penyetrika'), 
    ('Pencuci'), 
    ('Kurir'), 
    ('Packing');

SELECT * FROM datarole;
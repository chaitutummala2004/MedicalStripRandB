import sqlite3
import datetime
import csv

DB_NAME = "smart_pharmacy.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create Medicines Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            manufacturer TEXT,
            dosage TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')
    cursor.execute("PRAGMA table_info(medicines)")
    mcols = [row[1] for row in cursor.fetchall()]
    if 'discount' not in mcols:
        cursor.execute("ALTER TABLE medicines ADD COLUMN discount REAL DEFAULT 0.0")
    if 'mfg_date' not in mcols:
        cursor.execute("ALTER TABLE medicines ADD COLUMN mfg_date TEXT")
    if 'exp_date' not in mcols:
        cursor.execute("ALTER TABLE medicines ADD COLUMN exp_date TEXT")
    
    # Create Sales Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER,
            medicine_name TEXT,
            quantity INTEGER,
            total_price REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines (id)
        )
    ''')
    cursor.execute("PRAGMA table_info(sales)")
    scols = [row[1] for row in cursor.fetchall()]
    if 'discount' not in scols:
        cursor.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0.0")
    cursor.execute("PRAGMA table_info(sales)")
    scols = [row[1] for row in cursor.fetchall()]
    if 'mfg_date' not in scols:
        cursor.execute("ALTER TABLE sales ADD COLUMN mfg_date TEXT")
    cursor.execute("PRAGMA table_info(sales)")
    scols = [row[1] for row in cursor.fetchall()]
    if 'exp_date' not in scols:
        cursor.execute("ALTER TABLE sales ADD COLUMN exp_date TEXT")
    cursor.execute("PRAGMA table_info(sales)")
    scols = [row[1] for row in cursor.fetchall()]
    if 'batch_id' not in scols:
        cursor.execute("ALTER TABLE sales ADD COLUMN batch_id INTEGER")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL,
            stock INTEGER NOT NULL,
            mfg_date TEXT,
            exp_date TEXT,
            FOREIGN KEY (medicine_id) REFERENCES medicines (id)
        )
    ''')
    cursor.execute("PRAGMA table_info(batches)")
    bcols = [row[1] for row in cursor.fetchall()]
    if 'batch_code' not in bcols:
        cursor.execute("ALTER TABLE batches ADD COLUMN batch_code TEXT")

    # Receipts (Invoice) Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            payment_mode TEXT,
            total REAL DEFAULT 0.0,
            printed INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("PRAGMA table_info(receipts)")
    rcols = [row[1] for row in cursor.fetchall()]
    if 'customer_phone' not in rcols:
        cursor.execute("ALTER TABLE receipts ADD COLUMN customer_phone TEXT")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipt_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id INTEGER NOT NULL,
            medicine_id INTEGER,
            medicine_name TEXT,
            qty INTEGER,
            unit_price REAL,
            discount REAL,
            FOREIGN KEY (receipt_id) REFERENCES receipts (id)
        )
    ''')
    
    # Comprehensive List of Medicines for Detection
    seed_data = [
        # Pain & Fever
        ("Dolo 650", "Micro Labs", "650mg", 2.0, 1000, 5.0, "2024-01-01", "2026-01-01"),
        ("Paracetamol", "Generic", "500mg", 1.5, 2000),
        ("Crocin Pain Relief", "GSK", "650mg", 2.5, 500),
        ("Calpol", "GSK", "500mg", 1.8, 800),
        ("Combiflam", "Sanofi", "400mg", 3.0, 800),
        ("Nice", "Dr. Reddy's", "100mg", 4.0, 300),
        ("Sumo", "Alkem", "500mg", 3.5, 400),
        ("Meftal Spas", "Blue Cross", "500mg", 4.5, 600),
        ("Zerodol-P", "Ipca", "100mg", 5.0, 400),
        ("Disprin", "Reckitt", "325mg", 1.0, 1000),
        
        # Antibiotics
        ("Azithromycin", "Cipla", "500mg", 25.0, 500),
        ("Augmentin", "GSK", "625mg", 22.0, 300),
        ("Amoxyclav", "Abbott", "625mg", 18.0, 250),
        ("Ciprobid", "Zydus", "500mg", 10.0, 400),
        ("Norflox TZ", "Cipla", "400mg", 8.0, 300),
        ("Oflox", "Cipla", "200mg", 7.5, 400),
        ("Taxim-O", "Alkem", "200mg", 12.0, 200),
        ("Moxikind-CV", "Mankind", "625mg", 15.0, 300),
        
        # Gastric / Acidity
        ("Digene", "Abbott", "Tablet", 1.5, 1000),
        ("Gelusil", "Pfizer", "Tablet", 1.2, 800),
        ("Pan-D", "Alkem", "40mg", 10.0, 600),
        ("Omez", "Dr. Reddy's", "20mg", 6.0, 900),
        ("Rantac", "J.B. Chemicals", "150mg", 2.0, 1000),
        ("Pantocid", "Sun Pharma", "40mg", 9.0, 500),
        ("Eno", "GSK", "5g", 8.0, 2000),
        ("Pudin Hara", "Dabur", "Pearls", 2.0, 1500),
        
        # Cold, Cough & Allergy
        ("Vicks VapoRub", "P&G", "50g", 150.0, 100),
        ("Vicks Action 500", "P&G", "Tablet", 4.0, 500),
        ("Benadryl", "J&J", "100ml", 110.0, 200),
        ("Corex DX", "Pfizer", "100ml", 120.0, 150),
        ("Ascoril", "Glenmark", "100ml", 105.0, 200),
        ("Sinarest", "Centaur", "Tablet", 5.0, 800),
        ("Cheston Cold", "Cipla", "Tablet", 4.5, 600),
        ("Allegra", "Sanofi", "120mg", 15.0, 300),
        ("Cetzine", "GSK", "10mg", 4.0, 700),
        ("Montair-LC", "Cipla", "Tablet", 12.0, 400),
        ("Otrivin", "GSK", "Nasal Spray", 60.0, 150),
        ("Honitus", "Dabur", "100ml", 90.0, 200),
        
        # Vitamins & Supplements
        ("Becosules", "Pfizer", "Capsule", 3.0, 1200),
        ("Limcee", "Abbott", "500mg", 2.0, 1500),
        ("Shelcal 500", "Torrent", "500mg", 8.0, 600),
        ("Neurobion Forte", "P&G", "Tablet", 2.5, 800),
        ("Evion 400", "Merck", "400mg", 3.5, 900),
        ("Revital H", "Sun Pharma", "Capsule", 10.0, 500),
        ("Zincovit", "Apex", "Tablet", 5.0, 700),
        ("Gemful", "Tridoss", "Calcitriol+Calcium Carbonate+Zinc Soft Gelatin Capsules", 15.0, 400),
        
        # Chronic (Diabetes, BP, etc.)
        ("Glycomet", "USV", "500mg", 4.0, 1000),
        ("Telma 40", "Glenmark", "40mg", 8.0, 800),
        ("Amlodipine", "Generic", "5mg", 2.0, 1000),
        ("Atorva", "Zydus", "10mg", 7.0, 600),
        ("Ecosprin 75", "USV", "75mg", 0.5, 2000),
        ("Volini", "Sun Pharma", "Gel 30g", 85.0, 200, 10.0),
        ("Moov", "Reckitt", "Spray", 140.0, 150),
        ("Iodex", "GSK", "Balm", 40.0, 300),
        ("Betadine", "Win-Medicare", "Ointment", 50.0, 200),
        ("Dettol", "Reckitt", "Liquid", 60.0, 500),
        ("Savlon", "ITC", "Liquid", 55.0, 400),
        ("Soframycin", "Sanofi", "Cream", 45.0, 300),
        
        # Additional common prescription medicines
        ("Combiflam", "Sanofi", "Tablet", 3.0, 1000),
        ("Saridon", "Bayer", "Tablet", 2.5, 1200),
        ("Voveran", "Novartis", "50mg", 5.0, 800),
        ("Liv 52", "Himalaya", "Tablet", 2.0, 1500),
        ("Cystone", "Himalaya", "Tablet", 3.0, 1000),
        ("Septilin", "Himalaya", "Tablet", 2.5, 800),
        ("Gasex", "Himalaya", "Tablet", 1.5, 2000),
        ("Speman", "Himalaya", "Tablet", 4.0, 500),
        ("Confido", "Himalaya", "Tablet", 4.5, 600),
        ("Tentex Forte", "Himalaya", "Tablet", 6.0, 400),
        
        # User Requested Additions
        ("Azicip 500", "Cipla", "500mg", 15.0, 600), # Azithromycin
        ("Azicip 250", "Cipla", "250mg", 9.0, 600),
        ("Rabhucare", "Generic", "Tablet", 10.0, 500), # Assuming Rabeprazole
        ("Rabucare", "Generic", "Tablet", 10.0, 500),   # Adding corrected spelling just in case
        ("Amoxil 250", "Zydus", "250mg", 6.0, 800),    # From user image
        ("Amoxycillin", "Generic", "250mg", 4.0, 1000), # Generic fallback
        
        # Additional strip brands
        ("Amoxil 500", "Zydus", "500mg", 8.0, 800),
        ("Augmentin 625", "GSK", "625mg", 24.0, 400),
        ("Azithral 500", "Alembic", "500mg", 26.0, 300),
        ("Azee 500", "Cipla", "500mg", 25.0, 350),
        ("Zifi 200", "FDC", "200mg", 12.0, 500),
        ("Cepodem 200", "Ranbaxy", "200mg", 13.0, 300),
        ("Hifenac-P", "Intas", "Tablet", 6.0, 700),
        ("Diclofenac", "Generic", "50mg", 2.0, 1200),
        ("Ibuprofen", "Generic", "200mg", 2.5, 1200),
        ("Levocetirizine", "Generic", "5mg", 3.0, 800),
        ("Cetirizine", "Generic", "10mg", 2.0, 1200),
        ("Montair 10", "Cipla", "10mg", 9.0, 500),
        ("Pantop 40", "Sun Pharma", "40mg", 9.0, 500),
        ("Nexpro 40", "Torrent", "40mg", 10.0, 500),
        ("Rabeprazole 20", "Generic", "20mg", 7.0, 700),
        ("Omeprazole 20", "Generic", "20mg", 6.0, 900),
        
        # Labels from user image
        ("AB PHYLLINE", "Generic", "Capsule", 15.0, 500, 10.0),
        ("AB PHYLLINE SR 200", "Generic", "Tablet", 18.0, 400, 10.0),
        ("ABZORB POWDER", "Generic", "Powder", 12.0, 600, 10.0),
        ("ACCOF 100", "Generic", "Tablet", 8.0, 700, 10.0),
        ("ACELIFE 100", "Generic", "Tablet", 5.0, 1000, 10.0),
        ("ACELIFE P", "Generic", "Tablet", 6.0, 900, 10.0),
        ("ACELIFE SP", "Generic", "Tablet", 7.5, 800, 10.0),
        ("ACILOC 150", "Generic", "Tablet", 2.0, 2000, 10.0),
        ("ACILOC 300", "Generic", "Tablet", 3.5, 1500, 10.0),
        ("ACILOC RD", "Generic", "Tablet", 8.5, 1000, 10.0),
        ("ACIVIR 400", "Generic", "Tablet", 12.0, 500, 10.0),
        ("ACIVIR DT 200", "Generic", "Tablet", 10.0, 600, 10.0),
        ("ADELPHANE ESIDREX", "Generic", "Tablet", 14.0, 400, 10.0),
        ("ALCEE", "Generic", "Tablet", 4.0, 1200, 10.0),
        ("ALDAY", "Generic", "Tablet", 3.5, 1500, 10.0),
        ("ALDAY AM", "Generic", "Tablet", 5.5, 1000, 10.0),
        ("ALERID", "Generic", "Tablet", 4.5, 1200, 10.0),
        ("ALERID D", "Generic", "Tablet", 6.5, 800, 10.0),
        ("ALEX", "Generic", "Syrup", 10.0, 500, 10.0),
        ("ALEX P", "Generic", "Syrup", 12.0, 400, 10.0),
        ("ALKACITROL", "Generic", "Syrup", 15.0, 300, 10.0),
        ("ALKASOL", "Generic", "Syrup", 14.0, 400, 10.0),
        ("ALLEGRA 120", "Generic", "Tablet", 18.0, 500, 10.0),
        ("ALLEGRA 180", "Generic", "Tablet", 22.0, 400, 10.0),
        ("ALLEGRA M", "Generic", "Tablet", 25.0, 300, 10.0),
        ("ALMEC 20", "Generic", "Tablet", 10.0, 800, 10.0),
        ("ALMEC 40", "Generic", "Tablet", 15.0, 600, 10.0),
        ("ALMEC AM", "Generic", "Tablet", 18.0, 500, 10.0),
        ("ALMEC H", "Generic", "Tablet", 20.0, 400, 10.0),
        ("ALMEC MT", "Generic", "Tablet", 22.0, 300, 10.0),
        ("ALMEC TRIO", "Generic", "Tablet", 25.0, 200, 10.0),
        ("ALMEC TRIO 40", "Generic", "Tablet", 28.0, 150, 10.0),
        ("ALMEC TRIO 40 FORTE", "Generic", "Tablet", 32.0, 100, 10.0),
        ("ALPHADOPA 250", "Generic", "Tablet", 12.0, 500, 10.0),
        ("ALPHADOPA 500", "Generic", "Tablet", 20.0, 400, 10.0),
        ("ALPHANEXT", "Generic", "Tablet", 15.0, 300, 10.0),
        ("ALTHROCIN 250", "Generic", "Tablet", 14.0, 600, 10.0),
        ("ALTHROCIN 500", "Generic", "Tablet", 25.0, 400, 10.0),
        ("ALTHROCIN KID", "Generic", "Tablet", 10.0, 800, 10.0),
        ("ALTORET 10", "Generic", "Tablet", 8.0, 1000, 10.0),
        ("ALTORET 20", "Generic", "Tablet", 14.0, 800, 10.0),
        ("ALTORET 40", "Generic", "Tablet", 25.0, 500, 10.0),
        ("ALTORET 80", "Generic", "Tablet", 45.0, 200, 10.0),
        ("ALTORET ASP", "Generic", "Tablet", 15.0, 600, 10.0),
        ("ALTORET EZ", "Generic", "Tablet", 18.0, 500, 10.0),
        ("ALTORET F", "Generic", "Tablet", 20.0, 400, 10.0),
        ("AMARYL 1", "Generic", "Tablet", 10.0, 1000, 10.0),
        ("AMARYL 2", "Generic", "Tablet", 15.0, 800, 10.0),
        ("AMARYL M 1", "Generic", "Tablet", 12.0, 900, 10.0),
        ("AMARYL M 2", "Generic", "Tablet", 18.0, 700, 10.0),
        ("AMARYL MV 1", "Generic", "Tablet", 15.0, 800, 10.0),
        ("AMARYL MV 2", "Generic", "Tablet", 20.0, 600, 10.0),
        ("AMITOP 10", "Generic", "Tablet", 8.0, 1000, 10.0),
        ("AMITOP 25", "Generic", "Tablet", 14.0, 800, 10.0),
        ("AMLODAC 2.5", "Generic", "Tablet", 5.0, 1200, 10.0),
        ("AMLODAC 5", "Generic", "Tablet", 8.0, 1000, 10.0),
        ("AMLODAC AT", "Generic", "Tablet", 12.0, 800, 10.0),
        ("AMLODAC L", "Generic", "Tablet", 10.0, 900, 10.0),
        ("AMLODAC M", "Generic", "Tablet", 15.0, 700, 10.0),
        ("AMLOKIND 2.5", "Generic", "Tablet", 4.0, 1500, 10.0),
        ("AMLOKIND 5", "Generic", "Tablet", 7.0, 1200, 10.0),
        ("AMLOKIND AT", "Generic", "Tablet", 10.0, 1000, 10.0),
        ("AMLOKIND L", "Generic", "Tablet", 9.0, 1100, 10.0),
        ("AMLOKIND M", "Generic", "Tablet", 14.0, 900, 10.0),
        ("AMLONG 2.5", "Generic", "Tablet", 6.0, 1200, 10.0),
        ("AMLONG 5", "Generic", "Tablet", 9.0, 1000, 10.0),
        ("AMLONG A", "Generic", "Tablet", 12.0, 800, 10.0),
        ("AMLONG MT 25", "Generic", "Tablet", 15.0, 700, 10.0),
        ("AMLONG MT 50", "Generic", "Tablet", 20.0, 500, 10.0),
        ("AMOROLFINE", "Generic", "Cream", 25.0, 300, 10.0),
        ("AMPILOX", "Generic", "Capsule", 12.0, 600, 10.0),
        ("AMTAS 10", "Generic", "Tablet", 18.0, 500, 10.0),
        ("AMTAS 2.5", "Generic", "Tablet", 7.0, 1000, 10.0),
        ("AMTAS 5", "Generic", "Tablet", 12.0, 800, 10.0),
        ("AMTAS AT", "Generic", "Tablet", 15.0, 700, 10.0),
        ("AMTAS M 25", "Generic", "Tablet", 18.0, 600, 10.0),
        ("AMTAS M 50", "Generic", "Tablet", 25.0, 400, 10.0),
        ("ANAFRANIL 25", "Generic", "Tablet", 20.0, 300, 10.0),
        ("ANGLIZIDE 5", "Generic", "Tablet", 10.0, 800, 10.0),
        ("ANGLIZIDE M", "Generic", "Tablet", 15.0, 600, 10.0),
        ("ANXIT 0.25", "Generic", "Tablet", 5.0, 1500, 10.0),
        ("ANXIT 0.5", "Generic", "Tablet", 8.0, 1200, 10.0),
        ("APIXABID 2.5", "Generic", "Tablet", 35.0, 400, 10.0),
        ("APIXABID 5", "Generic", "Tablet", 65.0, 300, 10.0),
        ("ARKAMIN", "Generic", "Tablet", 12.0, 600, 10.0),
        ("ARVAST 10", "Generic", "Tablet", 15.0, 800, 10.0),
        ("ARVAST 20", "Generic", "Tablet", 25.0, 600, 10.0),
        ("ARVAST 5", "Generic", "Tablet", 10.0, 1000, 10.0),
        ("ARVAST CF", "Generic", "Tablet", 22.0, 500, 10.0),
        ("ARVAST F 10", "Generic", "Tablet", 28.0, 400, 10.0),
        ("ASALIN", "Generic", "Tablet", 8.0, 1000, 10.0),
        ("ASCORIL D", "Generic", "Syrup", 12.0, 800, 10.0),
        ("ASCORIL LS", "Generic", "Syrup", 15.0, 600, 10.0),
        ("ASCORIL PLUS", "Generic", "Syrup", 18.0, 500, 10.0),
        ("ASOMEX 2.5", "Generic", "Tablet", 12.0, 800, 10.0),
        ("ASOMEX 5", "Generic", "Tablet", 20.0, 600, 10.0),
        ("ASOMEX D", "Generic", "Tablet", 25.0, 400, 10.0),
        ("ASOMEX LT", "Generic", "Tablet", 28.0, 300, 10.0),
        ("ATARAX 10", "Generic", "Tablet", 15.0, 600, 10.0),
        ("ATARAX 25", "Generic", "Tablet", 25.0, 400, 10.0),
        ("ATEN 25", "Generic", "Tablet", 8.0, 1200, 10.0),
        ("ATEN 50", "Generic", "Tablet", 14.0, 1000, 10.0),
        ("ATEN AM", "Generic", "Tablet", 18.0, 800, 10.0),
        ("ATIVAN 1", "Generic", "Tablet", 12.0, 900, 10.0),
        ("ATIVAN 2", "Generic", "Tablet", 20.0, 700, 10.0),
        ("ATOMOT 10", "Generic", "Tablet", 25.0, 400, 10.0),
        ("ATOMOT 18", "Generic", "Tablet", 35.0, 300, 10.0),
        ("ATOMOT 25", "Generic", "Tablet", 45.0, 200, 10.0),
        ("ATORVA 10", "Generic", "Tablet", 15.0, 1000, 10.0),
        ("ATORVA 20", "Generic", "Tablet", 25.0, 800, 10.0),
        ("ATORVA 40", "Generic", "Tablet", 45.0, 500, 10.0),
        ("ATORVA 5", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("ATORVA 80", "Generic", "Tablet", 85.0, 200, 10.0),
        ("ATORVA ASP", "Generic", "Tablet", 20.0, 600, 10.0),
        ("ATORVA EZ", "Generic", "Tablet", 22.0, 500, 10.0),
        ("ATORVA F 10", "Generic", "Tablet", 28.0, 400, 10.0),
        ("ATORVA TG", "Generic", "Tablet", 30.0, 300, 10.0),
        ("ATORVA TG 20", "Generic", "Tablet", 45.0, 200, 10.0),
        ("ATROVENT", "Generic", "Inhaler", 150.0, 100, 10.0),
        ("AUGMENTIN 1.2", "Generic", "Injection", 120.0, 100, 10.0),
        ("AUGMENTIN 375", "Generic", "Tablet", 25.0, 500, 10.0),
        ("AUGMENTIN 625 DUO", "Generic", "Tablet", 45.0, 400, 10.0),
        ("AUGMENTIN DDS", "Generic", "Syrup", 35.0, 300, 10.0),
        ("AUGMENTIN DUO", "Generic", "Syrup", 30.0, 400, 10.0),
        ("AVAMYS", "Generic", "Nasal Spray", 350.0, 50, 10.0),
        ("AVAS 10", "Generic", "Tablet", 12.0, 1000, 10.0),
        ("AVAS 20", "Generic", "Tablet", 22.0, 800, 10.0),
        ("AVAS 40", "Generic", "Tablet", 42.0, 500, 10.0),
        ("AVAS 5", "Generic", "Tablet", 8.0, 1200, 10.0),
        ("AVAS 80", "Generic", "Tablet", 75.0, 200, 10.0),
        ("AVAS F 10", "Generic", "Tablet", 25.0, 400, 10.0),
        ("AVIL", "Generic", "Tablet", 5.0, 2000, 10.0),
        ("AVIL 25", "Generic", "Tablet", 6.0, 1500, 10.0),
        ("AVIL 50", "Generic", "Tablet", 10.0, 1000, 10.0),
        ("AVIL NU", "Generic", "Tablet", 12.0, 800, 10.0),
        ("AVOMINE", "Generic", "Tablet", 15.0, 600, 10.0),
        ("AZI 500", "Generic", "Tablet", 25.0, 500, 10.0),
        ("AZITHRAL 250", "Generic", "Tablet", 15.0, 800, 10.0),
        ("AZITHRAL 500", "Generic", "Tablet", 28.0, 600, 10.0),
        ("AZITHRAL KID", "Generic", "Tablet", 10.0, 1000, 10.0),
        ("AZITHRAL STAT", "Generic", "Syrup", 35.0, 400, 10.0),
        ("AZODINE", "Generic", "Tablet", 12.0, 600, 10.0),
        ("AZOR 20", "Generic", "Tablet", 18.0, 800, 10.0),
        ("AZOR 40", "Generic", "Tablet", 32.0, 500, 10.0),
        ("AZOR AM", "Generic", "Tablet", 25.0, 400, 10.0),
        ("AZOR F", "Generic", "Tablet", 28.0, 300, 10.0),
        ("AZOR H", "Generic", "Tablet", 30.0, 250, 10.0),
        ("AZOR M", "Generic", "Tablet", 32.0, 200, 10.0),
        ("AZOR MT", "Generic", "Tablet", 35.0, 150, 10.0),
        ("AZOR TRIO", "Generic", "Tablet", 45.0, 100, 10.0),
        ("AZTO 10", "Generic", "Tablet", 15.0, 1000, 10.0),
        ("AZTO 20", "Generic", "Tablet", 25.0, 800, 10.0),
        ("AZTO 40", "Generic", "Tablet", 45.0, 500, 10.0),
        ("AZTO 5", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("AZTO 80", "Generic", "Tablet", 85.0, 200, 10.0),
        ("AZTO ASP", "Generic", "Tablet", 20.0, 600, 10.0),
        ("AZTO EZ", "Generic", "Tablet", 22.0, 500, 10.0),
        ("AZTO F 10", "Generic", "Tablet", 28.0, 400, 10.0),
        ("AZULIX 1", "Generic", "Tablet", 8.0, 1500, 10.0),
        ("AZULIX 1 MF", "Generic", "Tablet", 12.0, 1200, 10.0),
        ("AZULIX 1 MF FORTE", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("AZULIX 2", "Generic", "Tablet", 14.0, 1200, 10.0),
        ("AZULIX 2 MF", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("AZULIX 2 MF FORTE", "Generic", "Tablet", 25.0, 800, 10.0),
        ("AZULIX 3", "Generic", "Tablet", 20.0, 800, 10.0),
        ("AZULIX 3 MF", "Generic", "Tablet", 25.0, 600, 10.0),
        ("AZULIX 3 MF FORTE", "Generic", "Tablet", 32.0, 500, 10.0),
        ("AZULIX 4", "Generic", "Tablet", 28.0, 600, 10.0),
        ("AZULIX 4 MF", "Generic", "Tablet", 35.0, 400, 10.0),
        ("AZULIX 4 MF FORTE", "Generic", "Tablet", 45.0, 300, 10.0),
        ("BACOFOAM", "Generic", "Cream", 45.0, 200, 10.0),
        ("BANOCIDE FORTE", "Generic", "Tablet", 12.0, 800, 10.0),
        ("BANOCIDE PLUS", "Generic", "Tablet", 15.0, 600, 10.0),
        ("BAREON 10", "Generic", "Tablet", 15.0, 1000, 10.0),
        ("BAREON 20", "Generic", "Tablet", 25.0, 800, 10.0),
        ("BAREON 40", "Generic", "Tablet", 45.0, 500, 10.0),
        ("BAREON 5", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BAREON 80", "Generic", "Tablet", 85.0, 200, 10.0),
        ("BAREON ASP", "Generic", "Tablet", 20.0, 600, 10.0),
        ("BAREON EZ", "Generic", "Tablet", 22.0, 500, 10.0),
        ("BAREON F 10", "Generic", "Tablet", 28.0, 400, 10.0),
        ("BECOSULES", "Generic", "Capsule", 5.0, 2000, 10.0),
        ("BECOSULES Z", "Generic", "Capsule", 6.5, 1500, 10.0),
        ("BENADRYL", "Generic", "Syrup", 110.0, 500, 10.0),
        ("BENADRYL DR", "Generic", "Syrup", 120.0, 400, 10.0),
        ("BENADRYL PLUS", "Generic", "Syrup", 135.0, 300, 10.0),
        ("BENADRYL SARE", "Generic", "Syrup", 145.0, 200, 10.0),
        ("BENALIS", "Generic", "Tablet", 12.0, 1000, 10.0),
        ("BENALIS AM", "Generic", "Tablet", 18.0, 800, 10.0),
        ("BENALIS H", "Generic", "Tablet", 20.0, 700, 10.0),
        ("BENALIS MT", "Generic", "Tablet", 22.0, 600, 10.0),
        ("BENALIS TRIO", "Generic", "Tablet", 25.0, 500, 10.0),
        ("BENALIS TRIO 40", "Generic", "Tablet", 32.0, 400, 10.0),
        ("BENALIS TRIO 40 FORTE", "Generic", "Tablet", 45.0, 300, 10.0),
        ("BENIT 4", "Generic", "Tablet", 10.0, 1000, 10.0),
        ("BENIT 8", "Generic", "Tablet", 18.0, 800, 10.0),
        ("BENIT AM", "Generic", "Tablet", 22.0, 600, 10.0),
        ("BENIT H", "Generic", "Tablet", 25.0, 500, 10.0),
        ("BENIT MT", "Generic", "Tablet", 28.0, 400, 10.0),
        ("BENIT TRIO", "Generic", "Tablet", 32.0, 300, 10.0),
        ("BENIT TRIO 40", "Generic", "Tablet", 45.0, 200, 10.0),
        ("BENIT TRIO 40 FORTE", "Generic", "Tablet", 55.0, 100, 10.0),
        ("BENODON", "Generic", "Tablet", 12.0, 1000, 10.0),
        ("BENODON 4", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BENODON 8", "Generic", "Tablet", 18.0, 900, 10.0),
        ("BENODON AM", "Generic", "Tablet", 22.0, 700, 10.0),
        ("BENODON H", "Generic", "Tablet", 25.0, 600, 10.0),
        ("BENODON MT", "Generic", "Tablet", 28.0, 500, 10.0),
        ("BENODON TRIO", "Generic", "Tablet", 32.0, 400, 10.0),
        ("BENODON TRIO 40", "Generic", "Tablet", 45.0, 300, 10.0),
        ("BENODON TRIO 40 FORTE", "Generic", "Tablet", 55.0, 200, 10.0),
        ("BENZEE", "Generic", "Tablet", 12.0, 1000, 10.0),
        ("BENZEE 4", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BENZEE 8", "Generic", "Tablet", 18.0, 900, 10.0),
        ("BENZEE AM", "Generic", "Tablet", 22.0, 700, 10.0),
        ("BENZEE H", "Generic", "Tablet", 25.0, 600, 10.0),
        ("BENZEE MT", "Generic", "Tablet", 28.0, 500, 10.0),
        ("BENZEE TRIO", "Generic", "Tablet", 32.0, 400, 10.0),
        ("BENZEE TRIO 40", "Generic", "Tablet", 45.0, 300, 10.0),
        ("BENZEE TRIO 40 FORTE", "Generic", "Tablet", 55.0, 200, 10.0),
        ("BENZIT 4", "Generic", "Tablet", 10.0, 1000, 10.0),
        ("BENZIT 8", "Generic", "Tablet", 18.0, 800, 10.0),
        ("BENZIT AM", "Generic", "Tablet", 22.0, 600, 10.0),
        ("BENZIT H", "Generic", "Tablet", 25.0, 500, 10.0),
        ("BENZIT MT", "Generic", "Tablet", 28.0, 400, 10.0),
        ("BENZIT TRIO", "Generic", "Tablet", 32.0, 300, 10.0),
        ("BENZIT TRIO 40", "Generic", "Tablet", 45.0, 200, 10.0),
        ("BENZIT TRIO 40 FORTE", "Generic", "Tablet", 55.0, 100, 10.0),
        ("BERI 4", "Generic", "Tablet", 10.0, 1000, 10.0),
        ("BERI 8", "Generic", "Tablet", 18.0, 800, 10.0),
        ("BERI AM", "Generic", "Tablet", 22.0, 600, 10.0),
        ("BERI H", "Generic", "Tablet", 25.0, 500, 10.0),
        ("BERI MT", "Generic", "Tablet", 28.0, 400, 10.0),
        ("BERI TRIO", "Generic", "Tablet", 32.0, 300, 10.0),
        ("BERI TRIO 40", "Generic", "Tablet", 45.0, 200, 10.0),
        ("BERI TRIO 40 FORTE", "Generic", "Tablet", 55.0, 100, 10.0),
        ("BETACAP", "Generic", "Tablet", 12.0, 1000, 10.0),
        ("BETACAP TR 40", "Generic", "Capsule", 18.0, 800, 10.0),
        ("BETACAP TR 60", "Generic", "Capsule", 25.0, 600, 10.0),
        ("BETACAP TR 80", "Generic", "Capsule", 35.0, 400, 10.0),
        ("BETADINE", "Generic", "Ointment", 65.0, 500, 10.0),
        ("BETADINE POWDER", "Generic", "Powder", 85.0, 300, 10.0),
        ("BETALOC 25", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BETALOC 50", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("BETALOC AM 25", "Generic", "Tablet", 22.0, 800, 10.0),
        ("BETALOC AM 50", "Generic", "Tablet", 28.0, 600, 10.0),
        ("BETALOC H 25", "Generic", "Tablet", 25.0, 700, 10.0),
        ("BETALOC H 50", "Generic", "Tablet", 32.0, 500, 10.0),
        ("BETALOC MT 25", "Generic", "Tablet", 20.0, 900, 10.0),
        ("BETALOC MT 50", "Generic", "Tablet", 35.0, 700, 10.0),
        ("BETALOC TRIO", "Generic", "Tablet", 45.0, 500, 10.0),
        ("BETALOC TRIO 25", "Generic", "Tablet", 42.0, 600, 10.0),
        ("BETALOC TRIO 50", "Generic", "Tablet", 55.0, 400, 10.0),
        ("BETALOC TRIO 50 FORTE", "Generic", "Tablet", 75.0, 200, 10.0),
        ("BETNOVATE", "Generic", "Cream", 25.0, 1000, 10.0),
        ("BETNOVATE C", "Generic", "Cream", 35.0, 800, 10.0),
        ("BETNOVATE GM", "Generic", "Cream", 45.0, 600, 10.0),
        ("BETNOVATE N", "Generic", "Cream", 30.0, 900, 10.0),
        ("BETNOVATE S", "Generic", "Cream", 40.0, 700, 10.0),
        ("BEZID 1", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BEZID 2", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("BEZID 3", "Generic", "Tablet", 25.0, 800, 10.0),
        ("BEZID 4", "Generic", "Tablet", 32.0, 600, 10.0),
        ("BEZID M 1", "Generic", "Tablet", 15.0, 1000, 10.0),
        ("BEZID M 2", "Generic", "Tablet", 25.0, 800, 10.0),
        ("BEZID M 3", "Generic", "Tablet", 35.0, 600, 10.0),
        ("BEZID M 4", "Generic", "Tablet", 45.0, 400, 10.0),
        ("BEZID MV 1", "Generic", "Tablet", 20.0, 800, 10.0),
        ("BEZID MV 2", "Generic", "Tablet", 32.0, 600, 10.0),
        ("BEZID MV 3", "Generic", "Tablet", 45.0, 400, 10.0),
        ("BEZID MV 4", "Generic", "Tablet", 55.0, 300, 10.0),
        ("BICOMP", "Generic", "Tablet", 12.0, 1000, 10.0),
        ("BICOMP 10", "Generic", "Tablet", 15.0, 1200, 10.0),
        ("BICOMP 20", "Generic", "Tablet", 25.0, 1000, 10.0),
        ("BICOMP 40", "Generic", "Tablet", 45.0, 800, 10.0),
        ("BICOMP 5", "Generic", "Tablet", 10.0, 1500, 10.0),
        ("BICOMP 80", "Generic", "Tablet", 85.0, 500, 10.0),
        ("BICOMP ASP", "Generic", "Tablet", 22.0, 800, 10.0),
        ("BICOMP EZ", "Generic", "Tablet", 25.0, 700, 10.0),
        ("BICOMP F 10", "Generic", "Tablet", 32.0, 600, 10.0),
        ("BILAXTEN 20", "Generic", "Tablet", 15.0, 1000, 10.0),
        ("BILAXTEN M", "Generic", "Tablet", 18.0, 800, 10.0),
        ("BILAXTEN M 20", "Generic", "Tablet", 22.0, 700, 10.0),
        ("BILAXTEN MT", "Generic", "Tablet", 25.0, 600, 10.0),
        ("BILAXTEN TRIO", "Generic", "Tablet", 32.0, 500, 10.0),
        ("BILAXTEN TRIO 20", "Generic", "Tablet", 35.0, 400, 10.0),
        ("BILAXTEN TRIO 40", "Generic", "Tablet", 45.0, 300, 10.0),
        ("BILAXTEN TRIO 40 FORTE", "Generic", "Tablet", 55.0, 200, 10.0),
        ("BILAXTEN TRIO 80", "Generic", "Tablet", 75.0, 150, 10.0),
        ("BILAXTEN TRIO 80 FORTE", "Generic", "Tablet", 95.0, 100, 10.0),
        ("BINOD 4", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BINOD 8", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("BINOD AM", "Generic", "Tablet", 22.0, 800, 10.0),
        ("BINOD H", "Generic", "Tablet", 25.0, 700, 10.0),
        ("BINOD MT", "Generic", "Tablet", 28.0, 600, 10.0),
        ("BINOD TRIO", "Generic", "Tablet", 32.0, 500, 10.0),
        ("BINOD TRIO 40", "Generic", "Tablet", 45.0, 400, 10.0),
        ("BINOD TRIO 40 FORTE", "Generic", "Tablet", 55.0, 300, 10.0),
        ("BISACODYL", "Generic", "Tablet", 5.0, 2000, 10.0),
        ("BISALIS 4", "Generic", "Tablet", 12.0, 1000, 10.0),
        ("BISALIS 8", "Generic", "Tablet", 20.0, 800, 10.0),
        ("BISALIS AM", "Generic", "Tablet", 25.0, 700, 10.0),
        ("BISALIS H", "Generic", "Tablet", 28.0, 600, 10.0),
        ("BISALIS MT", "Generic", "Tablet", 32.0, 500, 10.0),
        ("BISALIS TRIO", "Generic", "Tablet", 35.0, 400, 10.0),
        ("BISALIS TRIO 40", "Generic", "Tablet", 48.0, 300, 10.0),
        ("BISALIS TRIO 40 FORTE", "Generic", "Tablet", 58.0, 200, 10.0),
        ("BISODON 4", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BISODON 8", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("BISODON AM", "Generic", "Tablet", 22.0, 800, 10.0),
        ("BISODON H", "Generic", "Tablet", 25.0, 700, 10.0),
        ("BISODON MT", "Generic", "Tablet", 28.0, 600, 10.0),
        ("BISODON TRIO", "Generic", "Tablet", 32.0, 500, 10.0),
        ("BISODON TRIO 40", "Generic", "Tablet", 45.0, 400, 10.0),
        ("BISODON TRIO 40 FORTE", "Generic", "Tablet", 55.0, 300, 10.0),
        ("BISOZEE 4", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BISOZEE 8", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("BISOZEE AM", "Generic", "Tablet", 22.0, 800, 10.0),
        ("BISOZEE H", "Generic", "Tablet", 25.0, 700, 10.0),
        ("BISOZEE MT", "Generic", "Tablet", 28.0, 600, 10.0),
        ("BISOZEE TRIO", "Generic", "Tablet", 32.0, 500, 10.0),
        ("BISOZEE TRIO 40", "Generic", "Tablet", 45.0, 400, 10.0),
        ("BISOZEE TRIO 40 FORTE", "Generic", "Tablet", 55.0, 300, 10.0),
        ("BISZIT 4", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BISZIT 8", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("BISZIT AM", "Generic", "Tablet", 22.0, 800, 10.0),
        ("BISZIT H", "Generic", "Tablet", 25.0, 700, 10.0),
        ("BISZIT MT", "Generic", "Tablet", 28.0, 600, 10.0),
        ("BISZIT TRIO", "Generic", "Tablet", 32.0, 500, 10.0),
        ("BISZIT TRIO 40", "Generic", "Tablet", 45.0, 400, 10.0),
        ("BISZIT TRIO 40 FORTE", "Generic", "Tablet", 55.0, 300, 10.0),
        ("BITOCARD 25", "Generic", "Tablet", 10.0, 1500, 10.0),
        ("BITOCARD 50", "Generic", "Tablet", 18.0, 1200, 10.0),
        ("BITOCARD AM 25", "Generic", "Tablet", 22.0, 1000, 10.0),
        ("BITOCARD AM 50", "Generic", "Tablet", 28.0, 800, 10.0),
        ("BITOCARD H 25", "Generic", "Tablet", 25.0, 900, 10.0),
        ("BITOCARD H 50", "Generic", "Tablet", 32.0, 700, 10.0),
        ("BITOCARD MT 25", "Generic", "Tablet", 20.0, 1100, 10.0),
        ("BITOCARD MT 50", "Generic", "Tablet", 35.0, 900, 10.0),
        ("BITOCARD TRIO", "Generic", "Tablet", 45.0, 700, 10.0),
        ("BITOCARD TRIO 25", "Generic", "Tablet", 42.0, 800, 10.0),
        ("BITOCARD TRIO 50", "Generic", "Tablet", 55.0, 600, 10.0),
        ("BITOCARD TRIO 50 FORTE", "Generic", "Tablet", 75.0, 400, 10.0),
        ("BIZID 1", "Generic", "Tablet", 10.0, 1200, 10.0),
        ("BIZID 2", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("BIZID 3", "Generic", "Tablet", 25.0, 800, 10.0),
        ("BIZID 4", "Generic", "Tablet", 32.0, 600, 10.0),
        ("BIZID M 1", "Generic", "Tablet", 15.0, 1000, 10.0),
        ("BIZID M 2", "Generic", "Tablet", 25.0, 800, 10.0),
        ("BIZID M 3", "Generic", "Tablet", 35.0, 600, 10.0),
        ("BIZID M 4", "Generic", "Tablet", 45.0, 400, 10.0),
        ("BIZID MV 1", "Generic", "Tablet", 20.0, 800, 10.0),
        ("BIZID MV 2", "Generic", "Tablet", 32.0, 600, 10.0),
        ("BIZID MV 3", "Generic", "Tablet", 45.0, 400, 10.0),
        ("BIZID MV 4", "Generic", "Tablet", 55.0, 300, 10.0),
        ("BRILINTA 60", "Generic", "Tablet", 45.0, 500, 10.0),
        ("BRILINTA 90", "Generic", "Tablet", 65.0, 400, 10.0),
        ("BRIVAZ 100", "Generic", "Tablet", 25.0, 1000, 10.0),
        ("BRIVAZ 25", "Generic", "Tablet", 10.0, 2000, 10.0),
        ("BRIVAZ 50", "Generic", "Tablet", 15.0, 1500, 10.0),
        ("BRIVAZ 75", "Generic", "Tablet", 20.0, 1200, 10.0),
        ("BRIVAZ CR 100", "Generic", "Tablet", 30.0, 800, 10.0),
        ("BRIVAZ CR 50", "Generic", "Tablet", 18.0, 1200, 10.0),
        ("BRIVAZ CR 75", "Generic", "Tablet", 22.0, 1000, 10.0),
        ("BRIVAZ M 100", "Generic", "Tablet", 28.0, 800, 10.0),
        ("BRIVAZ M 50", "Generic", "Tablet", 18.0, 1000, 10.0),
        ("BRIVAZ M 75", "Generic", "Tablet", 22.0, 900, 10.0),
        ("BRIVAZ MV 100", "Generic", "Tablet", 32.0, 700, 10.0),
        ("BRIVAZ MV 50", "Generic", "Tablet", 20.0, 900, 10.0),
        ("BRIVAZ MV 75", "Generic", "Tablet", 25.0, 800, 10.0),
        ("BRIVAZ TRIO", "Generic", "Tablet", 45.0, 600, 10.0),
        ("BRIVAZ TRIO 100", "Generic", "Tablet", 42.0, 700, 10.0),
        ("BRIVAZ TRIO 50", "Generic", "Tablet", 28.0, 1000, 10.0),
        ("BRIVAZ TRIO 75", "Generic", "Tablet", 35.0, 800, 10.0),
        ("BRIVAZ TRIO 75 FORTE", "Generic", "Tablet", 48.0, 600, 10.0),
        ("BRO-ZEDEX", "Generic", "Syrup", 105.0, 500, 10.0),
        ("BRO-ZEDEX LS", "Generic", "Syrup", 115.0, 400, 10.0),
        ("BRUFEN 200", "Generic", "Tablet", 2.0, 2000, 10.0),
        ("BRUFEN 400", "Generic", "Tablet", 3.5, 1500, 10.0),
        ("BRUFEN 600", "Generic", "Tablet", 5.0, 1200, 10.0),
        ("BRUFEN ACTIVE", "Generic", "Gel", 85.0, 300, 10.0),
        ("BRUFEN P", "Generic", "Syrup", 45.0, 600, 10.0),
        ("BUDEZ CR 3", "Generic", "Capsule", 35.0, 400, 10.0)
    ]

    # Augment seed data to include discount and explicit dates when missing
    default_discount = 10.0
    default_mfg = "2024-01-01"
    default_exp = "2026-01-01"
    augmented = []
    for med in seed_data:
        if len(med) == 5:
            augmented.append(med + (default_discount, default_mfg, default_exp))
        elif len(med) == 6:
            augmented.append(med + (default_mfg, default_exp))
        elif len(med) >= 8:
            augmented.append(med)
        else:
            augmented.append(med)
    seed_data = augmented

    count_added = 0
    for med in seed_data:
        cursor.execute("SELECT id, stock FROM medicines WHERE name = ?", (med[0],))
        existing = cursor.fetchone()
        if not existing:
            if len(med) >= 6:
                if len(med) >= 8:
                    cursor.execute('''
                        INSERT INTO medicines (name, manufacturer, dosage, price, stock, discount, mfg_date, exp_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (med[0], med[1], med[2], med[3], med[4], med[5], med[6], med[7]))
                    cursor.execute("SELECT id, stock FROM medicines WHERE name = ?", (med[0],))
                    mid, stk = cursor.fetchone()
                    cursor.execute("INSERT INTO batches (medicine_id, stock, mfg_date, exp_date, batch_code) VALUES (?, ?, ?, ?, ?)", (mid, stk, med[6], med[7], None))
                else:
                    cursor.execute('''
                        INSERT INTO medicines (name, manufacturer, dosage, price, stock, discount)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', med)
            else:
                cursor.execute('''
                    INSERT INTO medicines (name, manufacturer, dosage, price, stock)
                    VALUES (?, ?, ?, ?, ?)
                ''', med)
            count_added += 1
            print(f"Added new medicine: {med[0]}")
        else:
            if len(med) >= 6:
                cursor.execute("UPDATE medicines SET discount = ? WHERE name = ?", (med[5], med[0]))
            if len(med) >= 8:
                cursor.execute("UPDATE medicines SET mfg_date = ?, exp_date = ? WHERE name = ?", (med[6], med[7], med[0]))
                mid, stk = existing
                cursor.execute("SELECT id FROM batches WHERE medicine_id = ?", (mid,))
                b = cursor.fetchone()
                if b:
                    cursor.execute("UPDATE batches SET mfg_date = ?, exp_date = ? WHERE id = ?", (med[6], med[7], b[0]))
                else:
                    cursor.execute("INSERT INTO batches (medicine_id, stock, mfg_date, exp_date) VALUES (?, ?, ?, ?)", (mid, stk, med[6], med[7]))
    
    if count_added > 0:
        print(f"Database updated. Added {count_added} new medicines.")
    else:
        print("Database already up to date.")
    
    # Ensure Volini has explicit batch dates and discount
    cursor.execute("SELECT id, stock FROM medicines WHERE name = ?", ("Volini",))
    vrow = cursor.fetchone()
    if vrow:
        mid, stk = vrow
        cursor.execute("UPDATE medicines SET discount = ? WHERE id = ?", (10.0, mid))
        cursor.execute("SELECT id FROM batches WHERE medicine_id = ?", (mid,))
        b = cursor.fetchone()
        today = datetime.date.today()
        mfg = (today - datetime.timedelta(days=180)).isoformat()
        exp = (today + datetime.timedelta(days=720)).isoformat()
        if b:
            cursor.execute("UPDATE batches SET mfg_date = ?, exp_date = ? WHERE id = ?", (mfg, exp, b[0]))
        else:
            cursor.execute("INSERT INTO batches (medicine_id, stock, mfg_date, exp_date, batch_code) VALUES (?, ?, ?, ?, ?)", (mid, stk, mfg, exp, None))

    conn.commit()
    
    # Normalize all medicines with uniform discount and dates similar to Dolo 650
    uniform_discount = 10.0
    uniform_mfg = "2024-01-01"
    uniform_exp = "2026-01-01"
    cursor.execute("SELECT id, stock FROM medicines")
    for mid, stk in cursor.fetchall():
        cursor.execute("UPDATE medicines SET discount = ?, mfg_date = ?, exp_date = ? WHERE id = ?", (uniform_discount, uniform_mfg, uniform_exp, mid))
        cursor.execute("SELECT id FROM batches WHERE medicine_id = ?", (mid,))
        b = cursor.fetchone()
        if b:
            cursor.execute("UPDATE batches SET mfg_date = ?, exp_date = ? WHERE id = ?", (uniform_mfg, uniform_exp, b[0]))
        else:
            cursor.execute("INSERT INTO batches (medicine_id, stock, mfg_date, exp_date, batch_code) VALUES (?, ?, ?, ?, ?)", (mid, stk or 0, uniform_mfg, uniform_exp, None))
    
    conn.commit()
    cursor.execute("UPDATE batches SET batch_code = COALESCE(batch_code, 'B' || id)")
    conn.close()

def create_receipt(number=None, customer_name=None, payment_mode=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO receipts (number, customer_name, payment_mode, total, printed)
        VALUES (?, ?, ?, 0.0, 0)
    ''', (number, customer_name, payment_mode))
    conn.commit()
    cursor.execute('SELECT last_insert_rowid()')
    rid = cursor.fetchone()[0]
    conn.close()
    return rid

def update_receipt_meta(receipt_id, number=None, customer_name=None, customer_phone=None, payment_mode=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE receipts SET number = ?, customer_name = ?, customer_phone = ?, payment_mode = ? WHERE id = ?",
        (number, customer_name, customer_phone, payment_mode, receipt_id)
    )
    conn.commit()
    conn.close()

def add_receipt_item(receipt_id, medicine_id, medicine_name, qty, unit_price, discount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO receipt_items (receipt_id, medicine_id, medicine_name, qty, unit_price, discount)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (receipt_id, medicine_id, medicine_name, qty, unit_price, discount or 0.0))
    conn.commit()
    conn.close()

def get_receipt_items(receipt_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, medicine_id, medicine_name, qty, unit_price, discount
        FROM receipt_items WHERE receipt_id = ?
    ''', (receipt_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def finalize_receipt_and_reduce_stock(receipt_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, medicine_id, medicine_name, qty, unit_price, discount
        FROM receipt_items WHERE receipt_id = ?
    ''', (receipt_id,))
    items = cursor.fetchall()
    total = 0.0
    detailed = []
    for it in items:
        _, mid, name, qty, unit_price, discount = it
        allocations = reduce_stock_fefo(mid, qty)
        for a in allocations:
            part_total = unit_price * a['qty'] * (1 - (discount or 0.0)/100.0)
            total += part_total
            record_sale_extended(mid, name, a['qty'], part_total, discount or 0.0, a['mfg_date'], a['exp_date'], a.get('batch_id'))
            detailed.append({
                'medicine': name,
                'qty': a['qty'],
                'unit_price': unit_price,
                'discount': discount or 0.0,
                'amount': part_total,
                'batch_id': a.get('batch_id'),
                'batch_code': a.get('batch_code'),
                'mfg_date': a.get('mfg_date'),
                'exp_date': a.get('exp_date')
            })
    cursor.execute('UPDATE receipts SET total = ?, printed = 1 WHERE id = ?', (total, receipt_id))
    conn.commit()
    conn.close()
    return total, detailed

def list_receipts(limit=20):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, number, customer_name, customer_phone, payment_mode, total, printed, timestamp
        FROM receipts ORDER BY timestamp DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_medicine_by_name(name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Simple partial match or exact match. Let's do case insensitive partial.
    cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE", ('%' + name + '%',))
    result = cursor.fetchone()
    conn.close()
    return result

def get_medicine_by_id(mid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines WHERE id = ?", (mid,))
    result = cursor.fetchone()
    conn.close()
    return result

def create_medicine(name, manufacturer="Unknown", dosage="", price=10.0, stock=100, discount=10.0, mfg_date=None, exp_date=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if not mfg_date:
        mfg_date = "2024-01-01"
    if not exp_date:
        exp_date = "2026-01-01"
    cursor.execute(
        """
        INSERT INTO medicines (name, manufacturer, dosage, price, stock, discount, mfg_date, exp_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, manufacturer, dosage, price, stock, discount, mfg_date, exp_date),
    )
    conn.commit()
    cursor.execute("SELECT id, stock FROM medicines WHERE name = ?", (name,))
    mid, stk = cursor.fetchone()
    cursor.execute(
        "INSERT INTO batches (medicine_id, stock, mfg_date, exp_date, batch_code) VALUES (?, ?, ?, ?, ?)",
        (mid, stk, mfg_date, exp_date, None),
    )
    conn.commit()
    cursor.execute("SELECT * FROM medicines WHERE id = ?", (mid,))
    result = cursor.fetchone()
    conn.close()
    return result

def ensure_medicine(name):
    existing = get_medicine_by_name(name)
    if existing:
        return existing
    return create_medicine(name)

def update_stock(medicine_id, quantity_sold):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE medicines SET stock = stock - ? WHERE id = ?", (quantity_sold, medicine_id))
    conn.commit()
    conn.close()

def record_sale(medicine_id, medicine_name, quantity, total_price):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sales (medicine_id, medicine_name, quantity, total_price)
        VALUES (?, ?, ?, ?)
    ''', (medicine_id, medicine_name, quantity, total_price))
    conn.commit()
    conn.close()

def record_sale_extended(medicine_id, medicine_name, quantity, total_price, discount=0.0, mfg_date=None, exp_date=None, batch_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sales (medicine_id, medicine_name, quantity, total_price, discount, mfg_date, exp_date, batch_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (medicine_id, medicine_name, quantity, total_price, discount, mfg_date, exp_date, batch_id))
    conn.commit()
    conn.close()

def get_all_medicines():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines")
    items = cursor.fetchall()
    conn.close()
    return items

def get_recent_sales(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, medicine_name, quantity, total_price, timestamp FROM sales ORDER BY timestamp DESC LIMIT ?", (limit,))
    items = cursor.fetchall()
    conn.close()
    return items

def ensure_default_batch(medicine_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM batches WHERE medicine_id = ?", (medicine_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT stock FROM medicines WHERE id = ?", (medicine_id,))
        rs = cursor.fetchone()
        base_stock = rs[0] if rs else 0
        if base_stock > 0:
            today = datetime.date.today()
            mfg = (today - datetime.timedelta(days=180)).isoformat()
            exp = (today + datetime.timedelta(days=720)).isoformat()
            cursor.execute("INSERT INTO batches (medicine_id, stock, mfg_date, exp_date, batch_code) VALUES (?, ?, ?, ?, ?)", (medicine_id, base_stock, mfg, exp, None))
            conn.commit()
    conn.close()

def reduce_stock_fefo(medicine_id, quantity):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM medicines WHERE id = ?", (medicine_id,))
    if not cursor.fetchone():
        conn.close()
        return []
    ensure_default_batch(medicine_id)
    cursor = conn.cursor()
    cursor.execute("SELECT id, stock, mfg_date, exp_date, COALESCE(batch_code, 'B' || id) FROM batches WHERE medicine_id = ? ORDER BY CASE WHEN exp_date IS NULL THEN 1 ELSE 0 END, exp_date ASC", (medicine_id,))
    rows = cursor.fetchall()
    allocations = []
    remaining = quantity
    for b in rows:
        if remaining <= 0:
            break
        bid, bstock, mfg, exp, bcode = b
        if bstock <= 0:
            continue
        take = min(remaining, bstock)
        cursor.execute("UPDATE batches SET stock = stock - ? WHERE id = ?", (take, bid))
        allocations.append({'batch_id': bid, 'batch_code': bcode, 'qty': take, 'mfg_date': mfg, 'exp_date': exp})
        remaining -= take
    if allocations:
        total_taken = sum(a['qty'] for a in allocations)
        cursor.execute("UPDATE medicines SET stock = stock - ? WHERE id = ?", (total_taken, medicine_id))
    conn.commit()
    conn.close()
    return allocations

def upsert_medicine(name, manufacturer, dosage, price, stock, discount=0.0, mfg_date=None, exp_date=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM medicines WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not mfg_date:
        mfg_date = "2024-01-01"
    if not exp_date:
        exp_date = "2026-01-01"
    if row:
        mid = row[0]
        cursor.execute(
            "UPDATE medicines SET manufacturer = ?, dosage = ?, price = ?, stock = ?, discount = ?, mfg_date = ?, exp_date = ? WHERE id = ?",
            (manufacturer, dosage, price, stock, discount, mfg_date, exp_date, mid),
        )
    else:
        cursor.execute(
            "INSERT INTO medicines (name, manufacturer, dosage, price, stock, discount, mfg_date, exp_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, manufacturer, dosage, price, stock, discount, mfg_date, exp_date),
        )
        cursor.execute("SELECT id FROM medicines WHERE name = ?", (name,))
        mid = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM batches WHERE medicine_id = ?", (mid,))
    b = cursor.fetchone()
    if b:
        cursor.execute("UPDATE batches SET stock = ?, mfg_date = ?, exp_date = ? WHERE id = ?", (stock, mfg_date, exp_date, b[0]))
    else:
        cursor.execute("INSERT INTO batches (medicine_id, stock, mfg_date, exp_date, batch_code) VALUES (?, ?, ?, ?, ?)", (mid, stock, mfg_date, exp_date, None))
    conn.commit()
    conn.close()

def delete_medicine(medicine_id=None, name=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    mid = None
    if medicine_id:
        mid = medicine_id
    elif name:
        cursor.execute("SELECT id FROM medicines WHERE name = ?", (name,))
        row = cursor.fetchone()
        mid = row[0] if row else None
    if not mid:
        conn.close()
        return False
    cursor.execute("DELETE FROM batches WHERE medicine_id = ?", (mid,))
    cursor.execute("DELETE FROM medicines WHERE id = ?", (mid,))
    conn.commit()
    conn.close()
    return True

def import_csv_text(text):
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        name = row.get('name') or row.get('Name')
        manufacturer = row.get('manufacturer') or row.get('Manufacturer') or 'Unknown'
        dosage = row.get('dosage') or row.get('Dosage') or ''
        price = float(row.get('price') or row.get('Price') or 0)
        stock = int(row.get('stock') or row.get('Stock') or 0)
        discount = float(row.get('discount') or row.get('Discount') or 0.0)
        mfg_date = row.get('mfg_date') or row.get('MFG') or row.get('manufacture_date')
        exp_date = row.get('exp_date') or row.get('EXP') or row.get('expiry_date')
        if not name:
            continue
        upsert_medicine(name, manufacturer, dosage, price, stock, discount, mfg_date, exp_date)

def get_inventory_report():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, stock FROM medicines")
    stock_rows = cursor.fetchall()
    cursor.execute("SELECT medicine_name, SUM(quantity) FROM sales GROUP BY medicine_name")
    sold_rows = cursor.fetchall()
    sold_map = {r[0]: r[1] for r in sold_rows}
    report = []
    for name, stock in stock_rows:
        sold = sold_map.get(name, 0) or 0
        report.append((name, stock, sold))
    conn.close()
    return report

def get_batches_report():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.name, b.stock, b.mfg_date, b.exp_date, COALESCE(m.discount, 0.0), b.id
        FROM batches b
        JOIN medicines m ON m.id = b.medicine_id
        ORDER BY m.name ASC, b.exp_date ASC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()

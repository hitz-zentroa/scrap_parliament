import sqlite3

def get_conn(db_path):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute('PRAGMA journal_mode = WAL;') # Modo concurrente
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

def init_db(conn):
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS legislatura (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num INTEGER NOT NULL UNIQUE,
        name TEXT NOT NULL,
        pleno_url TEXT NOT NULL,
        comisiones_url TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS organo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        legislatura_id INTEGER NOT NULL,
        num INTEGER NOT NULL,
        name TEXT,
        xml_url TEXT,
        xml_filepath TEXT,
        UNIQUE (legislatura_id, num),
        CHECK (num >= 0),
        FOREIGN KEY (legislatura_id) REFERENCES legislatura(id) ON DELETE CASCADE
    );


    CREATE TABLE IF NOT EXISTS sesion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organo_id INTEGER NOT NULL,               
        num INTEGER NOT NULL,
        start_datetime TEXT,
        end_datetime TEXT,         
        pdf_url TEXT,
        pdf_filepath TEXT,        
        is_processed INTEGER DEFAULT NULL, -- NULL = not processed, 1 = processed, 0 = can't be processed
        UNIQUE (organo_id, num),
        FOREIGN KEY (organo_id) REFERENCES organo(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS media_url (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sesion_id INTEGER NOT NULL,      
        stream_url TEXT,
        m3u8_url TEXT,
        audio_filepath TEXT,  
        is_ok INTEGER DEFAULT NULL, -- NULL = not checked, 1 = ok, 0 = not ok               
        UNIQUE (sesion_id, stream_url, m3u8_url),
        FOREIGN KEY (sesion_id) REFERENCES sesion(id) ON DELETE CASCADE
    );
    """)

    conn.commit()

def get_or_create_legislatura(conn, num: int, name: str, pleno_url: str, comisiones_url: str):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO legislatura (num, name, pleno_url, comisiones_url)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(num) DO UPDATE SET
            name = excluded.name,
            pleno_url = excluded.pleno_url,
            comisiones_url = excluded.comisiones_url
    """, (num, name, pleno_url, comisiones_url))
    conn.commit()
    cur.execute("SELECT id FROM legislatura WHERE num = ?", (num,))
    return cur.fetchone()[0]

def get_or_create_organo(conn, legislatura_id: int, num: int, name: str, xml_url: str, xml_filepath: str):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO organo (legislatura_id, num, name, xml_url, xml_filepath)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(legislatura_id, num) DO UPDATE SET
            name = excluded.name,
            xml_url = excluded.xml_url
    """, (legislatura_id, num, name, xml_url, xml_filepath))
    conn.commit()
    cur.execute("SELECT id FROM organo WHERE legislatura_id = ? AND num = ?", (legislatura_id, num))
    return cur.fetchone()[0]

def get_or_create_sesion(conn, organo_id: int, num: int, start_datetime: str, end_datetime: str, pdf_url: str=None):
    cur = conn.cursor()
    status = 0 if not pdf_url else None
    cur.execute("""
        INSERT INTO sesion (organo_id, num, start_datetime, end_datetime, pdf_url, is_processed)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(organo_id, num) DO UPDATE SET
            start_datetime = excluded.start_datetime,
            end_datetime = excluded.end_datetime,
            pdf_url = excluded.pdf_url,
            -- PROTECTION: Only update status if it's currently NULL. 
            -- If it's 1 (done) or 0 (failed), we don't touch it.
            is_processed = COALESCE(sesion.is_processed, excluded.is_processed)
    """, (organo_id, num, start_datetime, end_datetime, pdf_url, status))
    conn.commit()
    cur.execute("SELECT id FROM sesion WHERE organo_id = ? AND num = ?", (organo_id, num))
    return cur.fetchone()[0]

def upsert_media_info(conn, sesion_id: int, stream_url: str, m3u8_url: str, audio_filepath: str= None, is_ok: int = None):
    cur = conn.cursor()
    is_ok = 0 if not m3u8_url else None
    cur.execute("""
        INSERT INTO media_url (sesion_id, stream_url, m3u8_url, audio_filepath, is_ok)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(sesion_id, stream_url, m3u8_url) 
        DO UPDATE SET
            m3u8_url = excluded.m3u8_url,
            -- PROTECTION: COALESCE keeps the existing value if it's NOT NULL.
            -- This prevents overwriting a '1' (downloaded) with a 'NULL'.
            is_ok = COALESCE(media_url.is_ok, excluded.is_ok),
            audio_filepath = COALESCE(media_url.audio_filepath, excluded.audio_filepath)
    """, (sesion_id, stream_url, m3u8_url, audio_filepath, is_ok))
    conn.commit()

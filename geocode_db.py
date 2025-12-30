import sqlite3
import requests
import time
from pathlib import Path

# --- AYARLAR ---
DB_FILE = 'tatil_karar_destek.db'
TABLE_NAME = 'tatil_verileri'

def geocode_place(query):
    """Nominatim API kullanarak bir yerin koordinatlarını bulur."""
    url = 'https://nominatim.openstreetmap.org/search'
    headers = {'User-Agent': 'TatilKDS_Projesi/1.0'}
    params = {'q': f"{query}, Turkey", 'format': 'json', 'limit': 1}
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"⚠️ Sorgu hatası ({query}): {e}")
    return None, None

def konumlari_guncelle():
    if not Path(DB_FILE).exists():
        print(f"❌ {DB_FILE} bulunamadı! Önce Step 1'i tamamlayın.")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Önce Enlem ve Boylam sütunları var mı kontrol et, yoksa ekle
    cur.execute(f"PRAGMA table_info({TABLE_NAME})")
    cols = [r[1] for r in cur.fetchall()]
    if 'Enlem' not in cols:
        cur.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN Enlem REAL")
    if 'Boylam' not in cols:
        cur.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN Boylam REAL")
    conn.commit()

    # Koordinatı eksik olan kayıtları çek
    # Sizin DB yapınıza göre 'Alt_Bölge' ve 'Bölge' sütunlarını kullanıyoruz
    cur.execute(f"SELECT rowid, Alt_Bölge, Bölge FROM {TABLE_NAME} WHERE Enlem IS NULL OR Boylam IS NULL")
    rows = cur.fetchall()

    if not rows:
        print("✅ Tüm kayıtların koordinatları zaten mevcut.")
        conn.close()
        return

    print(f"🔄 {len(rows)} adet yer için koordinat aranıyor...")

    for rowid, alt_bolge, bolge in rows:
        sorgu = f"{alt_bolge} {bolge}"
        lat, lon = geocode_place(sorgu)
        
        if lat and lon:
            cur.execute(f"UPDATE {TABLE_NAME} SET Enlem = ?, Boylam = ? WHERE rowid = ?", (lat, lon, rowid))
            conn.commit()
            print(f"📍 Bulundu: {alt_bolge} -> {lat}, {lon}")
        else:
            print(f"❓ Bulunamadı: {alt_bolge}")
        
        # API'yi yormamak için kısa bir bekleme (Zorunlu)
        time.sleep(1.2)

    conn.close()
    print("✅ Konum güncelleme işlemi tamamlandı.")

if __name__ == "__main__":
    konumlari_guncelle()
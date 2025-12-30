import pandas as pd
import sqlite3

# Excel dosya yolu
excel_dosya = r"C:\Users\Ömer Güler\OneDrive - Bartın Üniversitesi\Masaüstü\PROJE_SON_VE_NET.xlsx"

# SQLite veritabanı adı
sqlite_db = "tatil_karar_destek.db"

# Excel oku
df = pd.read_excel(excel_dosya)

# SQLite bağlantısı
conn = sqlite3.connect(sqlite_db)

# Excel'deki tabloyu SQLite'a yaz
# tablo_adi istediğin isim olabilir
df.to_sql(
    name="tatil_verileri",
    con=conn,
    if_exists="replace",  # tablo varsa silip yeniden oluşturur
    index=False
)

conn.close()

print("✅ Excel verisi başarıyla SQLite veritabanına aktarıldı.")
import pandas as pd
import streamlit as st
import numpy as np
import requests
import sqlite3

# --- 1. AYARLAR VE API ---
DB_FILE_NAME = 'tatil_karar_destek.db'
SQL_TABLE_NAME = 'tatil_verileri'     
YOUR_OPENWEATHERMAP_API_KEY = "826a84de005d412fd4a232deeae712ea"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Kriterler
criteria_map = {
    'Ortalama_Gecelik_Fiyat_TL': {'tip': 0, 'açıklama': 'Maliyet Hassasiyeti'},
    'Deniz_Puani': {'tip': 1, 'açıklama': 'Deniz ve Plaj Kalitesi'},
    'Eglence_Imkanlari': {'tip': 1, 'açıklama': 'Eğlence ve Aktivite'},
    'Yemek_Puani': {'tip': 1, 'açıklama': 'Yemek ve Restoran Kalitesi'},
    'Hizmet_Kalitesi': {'tip': 1, 'açıklama': 'Hizmet Standartı'},
    'Gürültü_Kirliligi_Puani': {'tip': 0, 'açıklama': 'Sessizlik ve Huzur'},
    'Yesil_Alan_Orani': {'tip': 1, 'açıklama': 'Doğa ve Yeşil Alan'},
    'Ulasim_Kolayligi': {'tip': 1, 'açıklama': 'Ulaşım İmkanları'},
    'Havaalani_Yakinligi': {'tip': 1, 'açıklama': 'Havaalanına Yakınlık'},
    'Tarihi_Kulturel_Zenginlik': {'tip': 1, 'açıklama': 'Tarihi ve Kültürel Yapı'},
    'Alisveris_Imkanlari': {'tip': 1, 'açıklama': 'Alışveriş Olanakları'}
}
criteria_names = list(criteria_map.keys())

# Gezilecek Yerler Rehberi
gezilecek_yerler_rehberi = {
    "Kaş": "Kaputaş Plajı, Antiphellos Antik Tiyatro, Kekova Tekne Turu",
    "Bodrum": "Bodrum Kalesi, Sualtı Arkeoloji Müzesi, Zeki Müren Müzesi",
    "Fethiye": "Ölüdeniz, Kelebekler Vadisi, Kayaköy, Saklıkent Kanyonu",
    "Marmaris": "Marmaris Kalesi, Kleopatra Adası, Kızkumu Plajı",
    "Datça": "Eski Datça Sokakları, Knidos Antik Kenti, Palamutbükü",
    "Çeşme": "Alaçatı Değirmenleri, Çeşme Kalesi, Ilıca Plajı",
    "Antalya": "Kaleiçi, Düden Şelalesi, Konyaaltı Plajı, Aspendos",
    "Kapadokya": "Peribacaları, Göreme Açık Hava Müzesi, Balon Turu",
    "Trabzon": "Sümela Manastırı, Uzungöl, Atatürk Köşkü",
    "Rize": "Ayder Yaylası, Zilkale, Fırtına Deresi, Pokut Yaylası",
    "Diyarbakır": "Diyarbakır Surları, Hevsel Bahçeleri, On Gözlü Köprü",
    "Mardin": "Dara Antik Kenti, Zinciriye Medresesi, Tarihi Çarşı",
    "İstanbul": "Ayasofya, Topkapı Sarayı, Galata Kulesi, Kapalıçarşı",
    "Bursa": "Uludağ, Cumalıkızık Köyü, Yeşil Türbe, Ulu Camii",
    "Van": "Akdamar Adası, Van Kalesi, Muradiye Şelalesi"
}

# --- 2. FONKSİYONLAR ---

def clean_column_name(col):
    col = str(col).strip()
    replacements = {
        'Alt_Bölge': 'Alt_Bolge', 'Bölge': 'Bolge', 'Otel_Adi': 'Otel_Adi',
        'Fiyat': 'Ortalama_Gecelik_Fiyat_TL', 'Eğlence': 'Eglence_Imkanlari',
        'Gürültü': 'Gürültü_Kirliligi_Puani', 'Yeşil': 'Yesil_Alan_Orani',
        'Ulaşım': 'Ulasim_Kolayligi', 'Havaalanı': 'Havaalani_Yakinligi',
        'Tarihi': 'Tarihi_Kulturel_Zenginlik', 'Alışveriş': 'Alisveris_Imkanlari',
        'Hizmet': 'Hizmet_Kalitesi'
    }
    for key in sorted(replacements.keys(), key=len, reverse=True):
        if key in col: return replacements[key]
    return col.replace(' ', '_').replace('(', '').replace(')', '')

def get_attractions(alt_bolge):
    if not isinstance(alt_bolge, str): return "Şehir merkezini gezebilirsiniz."
    for sehir, yerler in gezilecek_yerler_rehberi.items():
        if sehir.lower() in alt_bolge.lower(): return yerler
    return "Şehir merkezindeki tarihi ve turistik noktaları gezebilirsiniz."

def load_data():
    try:
        conn = sqlite3.connect(DB_FILE_NAME)
        try: df = pd.read_sql_query(f"SELECT * FROM {SQL_TABLE_NAME}", conn)
        except: df = pd.read_sql_query("SELECT * FROM oteller", conn)
        conn.close()
        df.columns = [clean_column_name(c) for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()].copy()
        num_cols = ['Enlem', 'Boylam', 'Ortalama_Gecelik_Fiyat_TL'] + criteria_names
        for c in num_cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df
    except: return pd.DataFrame()



def topsis_calculate(df_criteria, weights, impacts): #weight kullanıcı sectiği değerler
    X = np.nan_to_num(df_criteria.values.astype(float))
    norm = np.sqrt(np.sum(X**2, axis=0)) #Amacı: Fiyat (30.000) ile Puanı (8) aynı ölçeğe getirmektir. 0-1 arasına getircez tüm sutunları 0 ve 1 e donusturelimki işlemlerimizi daha rahat yapalım
    R = X / (norm + 1e-9) #Her değeri norma böler. (Sıfıra bölünme hatası olmasın diye minik bir sayı 1e-9 ekledik).
    #normalize ettik

   #agırlıklandırılmıs karar matrisi
    V = R * np.array(weights).astype(float)  #Normalize değerleri, kullanıcının seçtiği ağırlıklarla (slider puanları) çarpar. mesela Kullanıcı 'Deniz benim için çok önemli' dediyse, deniz puanını matematiksel olarak büyütüyo. ağırlıklandırılmış otel puanları (V tablosu) oldu bunlar



   
    A_plus = np.array([np.max(V[:, j]) if impacts[j] == 1 else np.min(V[:, j]) for j in range(V.shape[1])])   
     #"Pozitif İdeal Çözüm" (Positive Ideal Solution).
    #SONUÇ (A_plus Listesi):  [ 0.20, 0.95, 0.90 ] (Dikkat et: Bu, tek bir otel değil. A'nın fiyatını, B'nin denizini, C'nin yemeğini aldı.) en iyilerre fayda ise max maliyetr ise min
    #O tablonun içinden seçilmiş "En İyiler"den oluşan Tek Satırlık Liste.
    
    #range(V.shape[1]): "Sütun sayısı kadar dön" demektir.
    #Eğer 10 kriterin varsa (Fiyat, Deniz, Yemek...), bu döngü 0'dan 9'a kadar tek tek sayar. j sutun numarası
    #daha sonra Bilgisayar o an Fiyat sütunundaysa, V[:, j] komutuyla o sütundaki tüm otellerin fiyatlarını eline alır. tum satır otel o anki sutun alır yani
    #impacts da Bilgisayar şu an 0. sütunda (Fiyat) olsun. (j=0)--> maliyet olur sonra karar olarakmaliyetse else ksımına gitmeliyim der
    #kısaca fayda sutunların en iyilerini, maliyet sutunların en kötülerini alır. 
    #Sutun 1,  e bakar fiyat için en uygnu hangisi 1000 otel a dan alndı
    #sutun 2 , denizden  en iyi  hangisi 10 puan mesela otel b den alındı mesela

   
    #listedeki tüm otellerin özelliklerini tarar, 
    #Eğer özellik Fayda (1) ise (Örn: Deniz): Listedeki EN YÜKSEK puanı alır
    #Eğer özellik Maliyet (0) ise (Örn: Fiyat): Listedeki EN DÜŞÜK (en ucuz) fiyatı alır.
    #negatif ideal cozum
    A_minus = np.array([np.min(V[:, j]) if impacts[j] == 1 else np.max(V[:, j]) for j in range(V.shape[1])])
    #O tablonun içinden seçilmiş "En Kötüler"den oluşan Tek Satırlık Liste.

    #Negatif İdeal Çözüm bu sefer ozelliklerin en kotulerını toplar
    #eger fayda 1 ise listededien dusuk puanı alır, maliyet ise listediki en yuksek puanu alır
    # bu seki her oteliçin otel yatrattık

    #(Yayma/Dağıtma) denir. Python o tek satırlık A_plus listesini alır, sanki bir kaşe/damga gibi tablodaki 100 otelin üzerine tek tek basar.
    #ideal uzaklıklrını hesaplıyoruz değerlerin



    S_plus = np.sqrt(np.sum((V - A_plus)**2, axis=1)) 
    #Her bir otel için elinde sadece TEK BİR sayı kalacak. her otelin pozitif ideal çözüme uzaklık
    #Her bir otelin, o iyi olan yarattığımız "Mükemmel Otel"e ne kadar uzak olduğunu hesaplar. #S_plus: Mükemmele olan uzaklık (Küçük olması iyi).   surun sutun turun yana yana toplar kereini alur karekokunu alır toplam 1 sayı

    #negatif ideal çözume uzaklık
    S_minus = np.sqrt(np.sum((V - A_minus)**2, axis=1))#Kabusa Olan Uzaklık)   #S_minus: Berbat olana olan uzaklık (Büyük olması iyi).
    return S_minus / (S_minus + S_plus + 1e-9) #kotuye uzaklık/kotuye uzaklık + iyiye uzaklık  
    #Bir otel "Mükemmel"e yapışık, "Kötü"den çok uzaksa skor 1'e yaklaşır (En iyi). 

    #yani pozitif uzaklıkga en yakın olan negatif uzaklıga en uzak olan oteller en yuksek skoru alacak.

    #amac: bu satırlarda; sanal bir 'En İyi' ve 'En Kötü' senaryo oluşturup, her otelin bu senaryolara olan geometrik uzaklığını ölçerek 0 ile 1 arasında bir başarı puanı veriyoruz."






def get_weather(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return "N/A", "Konum Yok"
    try:
        params = {'lat': lat, 'lon': lon, 'appid': YOUR_OPENWEATHERMAP_API_KEY, 'units': 'metric', 'lang': 'tr'}
        r = requests.get(BASE_URL, params=params, timeout=3)
        if r.status_code == 200:
            d = r.json()
            return f"{d['main']['temp']}°C", d['weather'][0]['description'].capitalize()
    except: pass
    return "N/A", "Hata"

# --- 3. ARAYÜZ ---
def main():
    st.set_page_config(layout="wide", page_title="NereyeGitsek | Akıllı Karar Sistemi") #Sitenin sekme adını ve geniş ekran olacağını ayarlar.
    st.markdown("""<style>.big-font { font-size:20px !important; }</style>""", unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.error("Veritabanı yüklenemedi!")
        return

    st.title("🌴 NereyeGitsek: Akıllı Tatil Planlayıcısı")
    st.markdown("---")

    col_input1, col_input2 = st.columns([1, 3])  #Ekranı 1'e 3 oranında ikiye böler (Sol dar, sağ geniş).
    with col_input1:
        st.subheader("💰 Bütçe Ayarı")
        gun = st.slider("Tatil Süresi", 1, 15, 5)
        toplam_butce = st.number_input("Toplam Bütçe (TL)", 5000, 500000, 30000, step=1000)
        max_gunluk = toplam_butce / gun
        st.info(f"Günlük Limit: **{max_gunluk:,.0f} TL**")
        
        st.divider()
        if 'Bolge' in df.columns:
            bolgeler = ["Tümü"] + list(df['Bolge'].unique())
            secilen_bolge = st.selectbox("Bölge Filtrele", bolgeler)

    with col_input2:
        st.subheader("🎯 Tercihleriniz (1-10 Puan)")
        w_cols = st.columns(4)
        weights = []
        active_crits = [c for c in criteria_names if c in df.columns]
        for i, crit in enumerate(active_crits):
            with w_cols[i % 4]:
                w = st.slider(criteria_map[crit]['açıklama'], 1, 10, 5, key=crit)
                weights.append(w)

    st.markdown("---")

#butona basinca
    if st.button("🚀 EN UYGUN TATİLİ ANALİZ ET", type="primary", use_container_width=True):
        fiyat_col = 'Ortalama_Gecelik_Fiyat_TL'
        filtered_df = df[df[fiyat_col] <= max_gunluk].copy() #Önce bütçesi yetmeyen otelleri eler.
        
        if 'Bolge' in df.columns and secilen_bolge != "Tümü":
            filtered_df = filtered_df[filtered_df['Bolge'] == secilen_bolge]  #Eğer bölge seçildiyse (Ege vb.), o bölge dışındakileri eler.
        
        if not filtered_df.empty:
            impacts = [criteria_map[c]['tip'] for c in active_crits]
            filtered_df['Skor'] = topsis_calculate(filtered_df[active_crits], weights, impacts) ##Kalan otelleri TOPSIS fonksiyonuna yollar, her otele bir puan verir.
            results = filtered_df.sort_values('Skor', ascending=False).head(5) #Puanı en yüksekten düşüğe sıralar, ilk 5 tanesini alır.
            
            # --- 1. HAVA DURUMU (5 KUTU YAN YANA - SABİT) ---
            st.subheader("☀️ Önerilen Şehirlerde Hava Durumu")
            weather_cols = st.columns(5) #Yan yana 5 kutu yeri açar.
            for i, (idx, row) in enumerate(results.iterrows()):  #İlk 5 otel için tek tek döner, hava durumunu çeker ve kutulara yazar.
                lat = row.get('Enlem')
                lon = row.get('Boylam')
                temp, desc = get_weather(lat, lon)
                
                with weather_cols[i]:
                    sehir = row.get('Alt_Bolge', row.get('Bolge', 'Bilinmiyor'))
                    st.success(f"**{sehir}**")
                    st.write(f"{temp} | {desc}")
            
            st.markdown("---")

            # --- 2. KAZANAN KARTI ---
            en_iyi = results.iloc[0]
            st.subheader(f"🏆 Kazanan: {en_iyi['Otel_Adi']}")
            st.info(f"📍 **Konum:** {en_iyi.get('Alt_Bolge', '')} | 🎒 **Gezilecek Yerler:** {get_attractions(en_iyi.get('Alt_Bolge', ''))}")

            # --- 3. TABLO (ORTALANMIŞ VE GENİŞ) ---
            st.subheader("📊 Analiz Sonuçları")
            
            cols_to_show = ['Bolge', 'Alt_Bolge', 'Otel_Adi', fiyat_col, 'Skor']
            final_cols = [c for c in cols_to_show if c in results.columns]
            
            # use_container_width=True sayesinde tablo ekranı kaplar ve ortalı görünür
            st.dataframe(results[final_cols], hide_index=True, use_container_width=True)

            # --- 4. HARİTA (EN ALTTA VE BÜYÜK) ---
            st.markdown("---")
            st.subheader("🗺️ Konum Haritası")
            
            map_data = results.dropna(subset=['Enlem', 'Boylam']).copy()
            if not map_data.empty:
                map_data['Enlem'] = pd.to_numeric(map_data['Enlem'])
                map_data['Boylam'] = pd.to_numeric(map_data['Boylam'])
                # Harita da artık tam ekran genişliğinde
                st.map(map_data, latitude='Enlem', longitude='Boylam', zoom=5, use_container_width=True)
            else:
                st.warning("Koordinat verisi eksik.")

        else:
            st.error(f"😔 Bütçenize ({max_gunluk:,.0f} TL/Gün) uygun otel bulunamadı.")

if __name__ == "__main__":
    main()


   #calsıtırmcak için ısraylagirbunları erminale
    # cd Kdsproje
    # & "C:\Users\muham\AppData\Local\Programs\Python\Python313\python.exe" -m streamlit run app.py

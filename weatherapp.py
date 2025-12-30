import pandas as pd
import streamlit as st
import numpy as np
import requests  #Hava durumu sitesine (OpenWeatherMap) bağlanıp veri çekmek için.
import time 
import os   #API anahtarını güvenli bir şekilde sistemden okumak için.

# --- 1. SABİT TANIMLAMALAR ve AYARLAR ---
CSV_FILE_NAME = 'destinations_final.csv'
# Öncelikle çevre değişkeninden almaya çalışalım, yoksa placeholder kalır
YOUR_OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY', "SİZİN_API_ANAHTARINIZI_BURAYA_GİRİN")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Kriterler ve TOPSIS Tipi (Fayda: 1, Maliyet: 0)
criteria_map = {
    'Ortalama_Gecelik_Fiyat_TL': {'tip': 0, 'açıklama': 'Maliyet hassasiyeti (Ne kadar az, o kadar iyi)'},
    'Deniz_Puani': {'tip': 1, 'açıklama': 'Deniz ve plaj kalitesi'},
    'Eğlence_İmkanları': {'tip': 1, 'açıklama': 'Gece hayatı, aktivite ve sosyal imkanlar'},
    'Yemek_Puani': {'tip': 1, 'açıklama': 'Gastronomi ve restoran kalitesi'},
    'Yeşil_Alan_Oranı': {'tip': 1, 'açıklama': 'Doğa, orman ve park yoğunluğu'},
    'Gürültü_Kirliliği_Puanı': {'tip': 0, 'açıklama': 'Sakinlik (Ne kadar az gürültü, o kadar iyi)'},
    'Su_Sıcaklığı_Mevsimlik': {'tip': 1, 'açıklama': 'Su sıcaklığı (Yüksek, yüzmek için daha iyi)'},
    'Ulaşım_Kolaylığı': {'tip': 1, 'açıklama': 'Şehir içi/şehirlerarası ulaşım kolaylığı'},
    'Havaalanı_Yakınlığı': {'tip': 1, 'açıklama': 'Havaalanına erişim kolaylığı'},
    'Tarihi_Kültürel_Zenginlik': {'tip': 1, 'açıklama': 'Müzeler, ören yerleri ve tarihi doku'},
    'Alışveriş_İmkanları': {'tip': 1, 'açıklama': 'Pazar, AVM ve butik imkanları'},
    'İnternet_Kalitesi': {'tip': 1, 'açıklama': 'Wi-Fi ve mobil internet hızı/çekim gücü'}
}
criteria_names = list(criteria_map.keys())

# --- 2. FONKSİYONLAR ---

def load_data():
    """CSV dosyasını okur, sütunları temizler."""
    try:
        # 'utf-8-sig' ile Türkçe karakterleri ve BOM'u sorunsuz okumaya çalışıyoruz.
        df = pd.read_csv(CSV_FILE_NAME, encoding='utf-8-sig') 
        
        # Sütun adlarını kodda kullanıma uygun hale getirme
        def clean_column_name(col):
            return col.strip().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
        
        df.columns = [clean_column_name(col) for col in df.columns]
        
        # Gerekli sütunların varlığını kontrol etme
        required_cols = ['Ortalama_Gecelik_Fiyat_TL', 'Deniz_Puani', 'Enlem', 'Boylam']
        if not all(col in df.columns for col in required_cols):
             st.error(f"HATA: CSV dosyasında beklenen kritik sütunlar eksik. Eksik olanlardan bazıları: {required_cols}")
             return pd.DataFrame()
            
        return df

    except FileNotFoundError:
        st.error(f"HATA: '{CSV_FILE_NAME}' dosyası bulunamadı. Lütfen dosyanın projenin ana dizininde olduğundan emin olun.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"VERİ OKUMA HATASI: CSV dosyasını okurken bir hata oluştu: {e}. Lütfen Türkçe karakterleri ve virgül/noktalı virgül ayrımını kontrol edin.")
        return pd.DataFrame()


def topsis_calculate(df_criteria, weights, impacts):
    """TOPSIS (Çok Kriterli Karar Verme) Algoritması."""
    # Algoritma içeriği önceki kodla aynıdır
    X = df_criteria.values.astype(float)
    norm = np.sqrt(np.sum(X**2, axis=0))
    R = X / norm 
    W_array = np.array(weights).astype(float)
    V = R * W_array
    
    A_plus = np.zeros(V.shape[1])
    A_minus = np.zeros(V.shape[1])
    
    for j in range(V.shape[1]):
        if impacts[j] == 1:
            A_plus[j] = np.max(V[:, j])
            A_minus[j] = np.min(V[:, j])
        else:
            A_plus[j] = np.min(V[:, j])
            A_minus[j] = np.max(V[:, j])
            
    S_plus = np.sqrt(np.sum((V - A_plus)**2, axis=1)) 
    S_minus = np.sqrt(np.sum((V - A_minus)**2, axis=1))
    
    C_i = S_minus / (S_minus + S_plus)
    return C_i

def get_weather(lat, lon, api_key=None):
    """OpenWeatherMap API'den güncel hava durumunu çeker ve karar desteği sunar.

    Args:
        lat (float): Enlem
        lon (float): Boylam
        api_key (str|None): Eğer verilirse bu anahtar kullanılır; yoksa ortam değişkeni okunur.

    Returns:
        tuple: (sıcaklık_str, açıklama, uyarı_metni, has_warning_bool)
    """
    key = api_key or os.getenv('OPENWEATHERMAP_API_KEY') or YOUR_OPENWEATHERMAP_API_KEY

    if not key or key == "SİZİN_API_ANAHTARINIZI_BURAYA_GİRİN":
        return "25.0 °C", "Güneşli (Simülasyon)", "API Anahtarı eksik. Hava durumu simüle ediliyor. ☀️", True

    try:
        params = {
            'lat': lat,
            'lon': lon,
            'appid': key,
            'units': 'metric',
            'lang': 'tr'
        }
        response = requests.get(BASE_URL, params=params, timeout=6)
        response.raise_for_status()
        data = response.json()

        temp = data.get('main', {}).get('temp')
        weather_item = (data.get('weather') or [None])[0]
        description = (weather_item.get('description') if weather_item else 'Bilgi yok')
        main_weather = (weather_item.get('main', '').lower() if weather_item else '')

        has_warning = False
        if any(k in main_weather for k in ('rain', 'storm', 'drizzle', 'snow', 'thunderstorm')):
            uyari = "UYARI: Yağış/Şiddetli hava bekleniyor. Planlarınızı gözden geçirin. 🌧️"
            has_warning = True
        else:
            uyari = "Hava durumu güzel. Tatil için uygun! ☀️"

        if temp is None:
            return "API HATASI", description.capitalize(), "Hava verisi alınamadı.", True

        return f"{temp:.1f} °C", description.capitalize(), uyari, has_warning

    except requests.exceptions.RequestException as e:
        return "API HATASI", "Bilgi yok", f"Hata: Bağlantı/API Anahtarı hatası. ({e})", True
    except Exception as e:
        return "API HATASI", "Bilgi yok", f"Bilinmeyen bir hata oluştu. ({e})", True


# --- 3. STREAMLIT ANA FONKSİYON (ARAYÜZ) ---
def main():
    st.set_page_config(layout="wide", page_title="✈️ Akıllı Tatil KDS", initial_sidebar_state="collapsed")
    df = load_data()

    if df.empty:
        return

    st.title("Türkiye'nin En Akıllı Tatil Planlayıcısı ☀️ 🏖️")
    st.markdown("### Çok Kriterli Karar Verme Sistemi (MCDM - TOPSIS)")
    st.markdown("---")

    # BÜTÇE ve SÜRE GİRDİLERİ
    st.subheader("1. 💰 Bütçe ve Süre Planı")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tatil_suresi = st.slider("📅 Tatil Süresi (Gün)", 1, 30, 7)
    with col2:
        toplam_butce = st.number_input("💰 Toplam Bütçeniz (TL)", min_value=1000, value=20000, step=1000)
    with col3:
        max_gunluk_butce = round(toplam_butce / tatil_suresi, 0)
        st.metric("Maksimum Günlük Bütçe (Ort.)", f"{max_gunluk_butce:,.0f} TL")

    st.markdown("---")
    
    # KRİTER AĞIRLIKLARI (14 KRİTER)
    st.subheader("2. ✨ Tatil Tercihleri ve Ağırlıklandırma")
    
    weights_dict = {}
    
    with st.expander("Tüm Kriterleri Aç/Kapat (1: En Az, 5: En Çok Önemli)", expanded=True):
        cols = st.columns(4)
        for i, name in enumerate(criteria_names):
            col_index = i % 4
            with cols[col_index]:
                weights_dict[name] = st.slider(
                    f"**{name.replace('_', ' ').split('(')[0].strip()}**", 
                    1, 5, 3, help=criteria_map[name]['açıklama']
                )

    st.markdown("---")
    
    # --- TOPSIS ve SONUÇ BUTONU ---
    if st.button("🚀 KDS Analizini Başlat ve En Uygun Yeri Bul", type="primary", use_container_width=True):
        st.session_state['run_analysis'] = True
    else:
         st.session_state['run_analysis'] = False

    # Analiz çalıştırıldıysa
    if st.session_state.get('run_analysis', False):
        
        # Animasyon Başlangıcı
        progress_text = "MCDM Analizi yapılıyor... En uygun destinasyonlar hesaplanıyor..."
        my_bar = st.progress(0, text=progress_text)
        
        for percent_complete in range(100):
            time.sleep(0.01)
            my_bar.progress(percent_complete + 1, text=progress_text)
        my_bar.empty()
        # Animasyon Bitişi
        
        st.header("🏆 Analiz Sonuçları ve Mükemmel Önerimiz")
        st.markdown("---")
        
        # --- 4. VERİ FİLTRELEME ---
        filtered_df = df[df['Ortalama_Gecelik_Fiyat_TL'] <= max_gunluk_butce].copy()
        
        if filtered_df.empty:
            st.error(f"😔 Üzgünüz, bütçeniz olan {max_gunluk_butce:,.0f} TL günlük maliyeti karşılayacak destinasyon bulunamadı. Lütfen bütçenizi artırın.")
            return

        # --- 5. TOPSIS UYGULAMASI ---
        criteria_df = filtered_df[criteria_names]
        weights_list = [weights_dict[c] for c in criteria_names]
        criteria_types = [criteria_map[c]['tip'] for c in criteria_names]
        
        topsis_scores = topsis_calculate(criteria_df, weights_list, criteria_types)
        filtered_df['TOPSIS_Skoru'] = topsis_scores
        
        ranked_df = filtered_df.sort_values(by='TOPSIS_Skoru', ascending=False).head(5)
        
        # --- 6. EN İYİ SEÇENEĞİ VE HAVA DURUMUNU GÖSTERME ---
        
        best_choice = ranked_df.iloc[0]
        
        # Hava Durumu Entegrasyonu (Daha belirgin kutu)
        sicaklik, durum, uyari, has_warning = get_weather(best_choice['Enlem'], best_choice['Boylam'])
        
        if has_warning:
            col_box = st.columns([1])
            with col_box[0]:
                st.warning(f"🚨 KARAR DESTEK UYARISI: {uyari}")
        else:
            col_box = st.columns([1])
            with col_box[0]:
                st.success(f"✅ KARAR DESTEK ONAYI: {uyari}")
        
        # Detaylı Sonuç Kutucukları
        col_res1, col_res2, col_res3 = st.columns(3)
        
        with col_res1:
            st.metric(f"🥇 En İyi Seçim Uyum Skoru", f"{best_choice['TOPSIS_Skoru']:.3f}", help="Skor ne kadar 1'e yakınsa, tercihlerinize o kadar uygundur.")
            st.subheader(f"📍 **{best_choice['Alt_Bolge']}**")
            st.write(f"Bölge: {best_choice['Bölge']}")
            st.write(f"**Önerilen Otel:** {best_choice['Otel_Adi']} ({best_choice['Otel_Konsepti']})")

        with col_res2:
            st.info("💸 Bütçe Detayı")
            total_cost_estimate = best_choice['Ortalama_Gecelik_Fiyat_TL'] * tatil_suresi
            remaining_budget = toplam_butce - total_cost_estimate
            
            st.write(f"Konaklama Maliyeti ({tatil_suresi} Gün): **{total_cost_estimate:,.0f} TL**")
            st.metric("Kalan Bütçe", f"{remaining_budget:,.0f} TL")
            
            if remaining_budget < 0:
                st.error(f"Bu destinasyon bütçenizi aşıyor. Fark: {abs(remaining_budget):,.0f} TL.")

        with col_res3:
            st.info("☁️ Hava Durumu Detayı")
            st.metric("Sıcaklık", sicaklik)
            st.write(f"Durum: **{durum}**")
            
            if "API Anahtarı eksik" in uyari:
                 st.caption("Lütfen hava durumu için API Anahtarınızı girin.")
            
        st.markdown("---")

        # --- SIRALAMA TABLOSU ---
        st.subheader("✨ Sizin İçin Seçilen Diğer Alternatifler (TOPSIS Sıralaması)")
        display_cols = ['Alt_Bolge', 'Otel_Konsepti', 'Ortalama_Gecelik_Fiyat_TL', 'Deniz_Puani', 'Yemek_Puani', 'Tarihi_Kültürel_Zenginlik', 'TOPSIS_Skoru', 'Otel_Adi']
        
        def format_results(df_in):
            df_out = df_in[display_cols].copy()
            df_out.rename(columns={'Alt_Bolge': 'Destinasyon', 'Ortalama_Gecelik_Fiyat_TL': 'Fiyat (Günlük)', 'Otel_Konsepti': 'Konsept', 'Tarihi_Kültürel_Zenginlik': 'Tarih'}, inplace=True)
            df_out['Fiyat (Günlük)'] = df_out['Fiyat (Günlük)'].apply(lambda x: f"{x:,.0f} TL")
            df_out['TOPSIS_Skoru'] = df_out['TOPSIS_Skoru'].apply(lambda x: f"{x:.3f}")
            return df_out

        st.dataframe(format_results(ranked_df), use_container_width=True)
        
        # Harita görselleştirmesi
        st.markdown("---")
        st.subheader("Harita Üzerinde En İyi 5 Konum 🗺️")
        
        map_data = ranked_df[['Enlem', 'Boylam', 'Alt_Bolge']].copy()
        
        if not map_data.empty:
            st.map(map_data, latitude='Enlem', longitude='Boylam', zoom=5)


if __name__ == "__main__":
    if 'run_analysis' not in st.session_state:
        st.session_state['run_analysis'] = False
    
    main()
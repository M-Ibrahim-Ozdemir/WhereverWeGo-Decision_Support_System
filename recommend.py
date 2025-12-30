from app import load_data, topsis_calculate, criteria_names, criteria_map
import pandas as pd
import argparse
import json

#Olay şu: Bu satırlar bir hesaplama yapmıyor, sadece "Önem Puanı" (Ağırlık) belirliyor. İşte bu PRESETS kısmı, kullanıcı tek tek eliyle ayar yapmasın diye hazırlanmış Hazır Paketlerdir.

"""
'budget': "Bütçe Dostu / Öğrenci İşi" Modu.
'family': "Aile Tatili" Modu.
'romantic': "Romantik / Balayı" Modu."""

#Kodun amacı şu: "Sen bana hangi modda olduğunu söyle, ben senin yerine hangi özelliğin kaç puan (önemli) olduğunu otomatik ayarlayayım."

#Yani bu kod, TOPSIS Skoru hesaplamaz. TOPSIS skorunu hesaplamadan önce, kullanıcının yerine "Neye ne kadar önem vereceğini" otomatik ayarlar. 🚀
PRESETS = {
    #eger Bütçe Dostu Mod ('budget') modda isek
    #Eğer kriterin adı 'Fiyat' ise ona 10 Puan (Aşırı Önemli) ver. Geriye kalan diğer her şeye (Deniz, Hizmet, Yemek vb.) sadece 3 Puan (Az Önemli) ver.
    'budget': {c: (10 if c == 'Ortalama_Gecelik_Fiyat_TL' else 3) for c in criteria_names},
    #Aile Modu ('family')
    #Eğer kriter şunlardan biriyse: Eğlence, Yemek, Alışveriş veya Hizmet; bunlara 8 Puan (Çok Önemli) ver. Geriye kalanlara (Fiyat, Doğa vb.) 4 Puan ver.
    'family': {c: (8 if c in ['Eglence_Imkanlari','Yemek_Puani','Alisveris_Imkanlari','Hizmet_Kalitesi'] else 4) for c in criteria_names},
    #Romantik Mod ('romantic')
    #Eğer kriter şunlardan biriyse: Hizmet, Yeşil Alan veya Gürültü (Sessizlik); bunlara 9 Puan (Kritik Önemli) ver. Diğerlerine 4 Puan ver.
    'romantic': {c: (9 if c in ['Hizmet_Kalitesi','Yesil_Alan_Orani','G�r�lt�_Kirliligi_Puani'] else 4) for c in criteria_names}
}

#Hocam, şu anki arayüzümüzde (app.py) kullanıcıya tam özgürlük verdik, her kriteri kendi eliyle ayarlıyor (Manuel Mod).

#Ancak recommend.py dosyasında, projemin gelişime açık olduğunu göstermek için 'Hazır Profiller' (Backend Logic) altyapısını kurdum. İstersek arayüze tek bir buton ekleyerek 'Aile Modu'nu aktif edebiliriz. Bu kod, o otomatikleştirme mantığının hazır olduğunu gösteriyor."



#dışarıdan emir alır ve en iyi oteli bulup getirir.
#weights_dict: Hangi özellik kaç puan? (Örn: Deniz=5, Fiyat=3).
#max_daily_budget: Günlük harcama limitin ne?
#top_n: Kaç tane otel önereyim? (Varsayılan 5).
def recommend(weights_dict=None, max_daily_budget=None, top_n=5):
    df = load_data()
    if df.empty:
        print('Veri yüklenemedi.')
        return pd.DataFrame()


    #Eğer kullanıcı hiçbir tercih belirtmediyse, sistem "Her şey orta derecede (5 puan) önemlidir" der.
    if weights_dict is None:
        weights_dict = {c:5 for c in criteria_names}

    #Eğer bütçe limiti girilmediyse, sistem veritabanındaki en pahalı otelin fiyatını limit kabul eder. Yani "Para sorun değil, hepsini getir" der.
    if max_daily_budget is None:
        max_daily_budget = df['Ortalama_Gecelik_Fiyat_TL'].max()


    #Filtreleme: Bütçeyi aşan otelleri listeden siler. Geriye hiç otel kalmazsa "Uygun kayıt yok" der.
    filtered = df[df['Ortalama_Gecelik_Fiyat_TL'] <= max_daily_budget].copy()
    if filtered.empty:
        print('Bütçeye uygun kayıt yok.')
        return pd.DataFrame()

#TOPSIS Hazırlığı:
    criteria_df = filtered[criteria_names]  #Sadece puanlanacak sütunları (Deniz, Fiyat vb.) alır. sadece sayısalverileri ayırdık
    weights_list = [weights_dict.get(c,5) for c in criteria_names]  #Kullanıcının verdiği puanları (3, 5, 8...) sıraya dizer.
    #Kullanıcının verdiği puanları (yoksa 5'i) sıraya dizdik. -> [10, 8, 3...]
    impacts = [criteria_map[c]['tip'] for c in criteria_names]
    #dan gelen bilgiyle hangisi Fayda (1), hangisi Maliyet (0) belirler.



    scores = topsis_calculate(criteria_df, weights_list, impacts)#Matematiği konuşturur ve skorları üretir.
    filtered['TOPSIS_Skoru'] = scores  #TOPSIS_Skoru adında yeni bir sütun ekler.
    ranked = filtered.sort_values('TOPSIS_Skoru', ascending=False).head(top_n)  #En yüksek puandan en düşüğe sıralar. İlk 5 (veya istenen kadar) oteli alır ve geri gönderir.
    return ranked

if __name__ == '__main__':
    # Örnek: tüm kriterlere eşit ağırlık, günlük bütçe 10000 TL
    example_weights = {c:5 for c in criteria_names}
    res = recommend(weights_dict=example_weights, max_daily_budget=10000, top_n=5)
    if not res.empty:
        display_cols = ['Alt_Bolge','Otel_Adi','Otel_Konsepti','Ortalama_Gecelik_Fiyat_TL','TOPSIS_Skoru']
        print(res[display_cols].to_string(index=False))
    else:
        print('Öneri bulunamadı.')

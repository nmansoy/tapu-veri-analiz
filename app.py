import streamlit as st
import os
import zipfile
import csv
import sqlite3
import pandas as pd
from io import BytesIO

# Sayfa Ayarları
st.set_page_config(page_title="Tapu Veri Merkezi", layout="wide")
st.title("📂 Tapu Veri İşleme Merkezi v7 (Web)")

# --- YARDIMCI FONKSİYONLAR ---

def ayrac_bul(file_obj):
    """Dosya nesnesinden ayıracı bulur."""
    try:
        sample = file_obj.read(1024).decode("utf-8-sig", errors="ignore")
        file_obj.seek(0)
        adaylar = {'|': sample.count('|'), ';': sample.count(';'), ',': sample.count(',')}
        return max(adaylar, key=adaylar.get)
    except:
        return ','

def to_csv_download(df):
    """Pandas DataFrame'i indirilebilir CSV formatına çevirir."""
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- ANA AKIŞ ---

# Yan Menü (Sidebar)
st.sidebar.header("İşlem Seçimi")
secim = st.sidebar.radio("Hangi Aşamayı Çalıştırmak İstersiniz?", 
    ["1. Hazırlık (ZIP -> Birleştirme)", 
     "2. Genel Filtre (BBZeminid)", 
     "3. Özel Rapor (KiKm)", 
     "4. Mimari Durum"])

# --- AŞAMA 1: HAZIRLIK ---
if secim == "1. Hazırlık (ZIP -> Birleştirme)":
    st.header("1. Aşama: ZIP Dosyalarından Tek CSV'ye")
    
    uploaded_files = st.file_uploader("ZIP Dosyalarını Yükleyin", type="zip", accept_multiple_files=True)
    
    if st.button("İşlemi Başlat") and uploaded_files:
        all_dataframes = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, zip_file in enumerate(uploaded_files):
            status_text.text(f"İşleniyor: {zip_file.name}")
            with zipfile.ZipFile(zip_file) as z:
                for filename in z.namelist():
                    if filename.endswith('.csv'):
                        with z.open(filename) as f:
                            # Ayraç tespiti ve okuma
                            sep = ayrac_bul(f)
                            try:
                                # Pandas ile okumak daha güvenli ve hızlıdır
                                df = pd.read_csv(f, sep=sep, encoding="utf-8-sig", on_bad_lines='skip', engine='python')
                                all_dataframes.append(df)
                            except Exception as e:
                                st.error(f"Hata ({filename}): {e}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
            
        if all_dataframes:
            status_text.text("Dosyalar birleştiriliyor...")
            final_df = pd.concat(all_dataframes, ignore_index=True)
            
            st.success(f"✅ İşlem Tamam! Toplam Satır: {len(final_df)}")
            
            csv_data = to_csv_download(final_df)
            st.download_button(
                label="📥 Birleştirilmiş Dosyayı İndir",
                data=csv_data,
                file_name="Birlestirilmis_Sonuc.csv",
                mime="text/csv"
            )

# --- GENEL SQL FONKSİYONU ---
def sql_islem(uploaded_file, query, output_name):
    if uploaded_file:
        try:
            # Dosyayı belleğe (SQLite) yükle
            conn = sqlite3.connect(":memory:")
            # Pandas ile yüklemek SQL insert'ten çok daha hızlıdır
            df = pd.read_csv(uploaded_file, encoding="utf-8-sig", on_bad_lines='skip')
            
            # Kolon isimlerindeki boşlukları temizle (SQL hatası olmasın diye)
            df.columns = [c.strip() for c in df.columns]
            
            df.to_sql("veriler", conn, index=False, if_exists="replace")
            
            # Sorguyu çalıştır
            result_df = pd.read_sql_query(query, conn)
            conn.close()
            
            st.write(f"Bulunan Kayıt: {len(result_df)}")
            st.dataframe(result_df.head()) # İlk 5 satırı göster
            
            csv_data = to_csv_download(result_df)
            st.download_button(
                label=f"📥 {output_name} İndir",
                data=csv_data,
                file_name=f"{output_name}.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"SQL Hatası: {e}")

# --- AŞAMA 2: GENEL FİLTRE ---
elif secim == "2. Genel Filtre (BBZeminid)":
    st.header("2. Aşama: BBZeminid Filtresi")
    st.info("Sorgu: BBZeminid değeri '0' olmayanları getirir.")
    
    csv_file = st.file_uploader("Birleştirilmiş CSV Dosyasını Seçin", type="csv")
    if csv_file:
        query = 'SELECT * FROM veriler WHERE "BBZeminid" != "0"'
        sql_islem(csv_file, query, "Genel_Filtreli_Sonuc")

# --- AŞAMA 3: ÖZEL RAPOR ---
elif secim == "3. Özel Rapor (KiKm)":
    st.header("3. Aşama: KiKm Raporu")
    
    csv_file = st.file_uploader("Filtreli CSV Dosyasını Seçin", type="csv")
    if csv_file:
        query = """
            SELECT DISTINCT 
                AtZeminid, IlAd, IlceAd, MahalleAd, AdaNo, ParselNo, 
                MimariProjeDurumu, MimariProjeSayisi 
            FROM veriler
        """
        sql_islem(csv_file, query, "KiKm_Kurulu_Parseller")

# --- AŞAMA 4: MİMARİ DURUM ---
elif secim == "4. Mimari Durum":
    st.header("4. Aşama: Mimari Proje Kontrolü")
    st.info("Sorgu: MimariProjeDurumu = 'Yok' olanları getirir.")
    
    csv_file = st.file_uploader("CSV Dosyasını Seçin", type="csv")
    if csv_file:
        query = "SELECT * FROM veriler WHERE MimariProjeDurumu = 'Yok'"
        sql_islem(csv_file, query, "Mimari_Projesi_Olmayanlar")
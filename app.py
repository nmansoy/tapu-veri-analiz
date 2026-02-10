import streamlit as st
import zipfile
import sqlite3
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Tapu Veri Merkezi", layout="wide")
st.title("📂 Tapu Veri İşleme Merkezi v7 (Otomatik Akış)")

# --- 1. HAFIZA YÖNETİMİ (SESSION STATE) ---
# Eğer hafızada veri yoksa boş bir alan açıyoruz
if 'aktif_veri' not in st.session_state:
    st.session_state['aktif_veri'] = None
if 'dosya_adi' not in st.session_state:
    st.session_state['dosya_adi'] = ""

# --- 2. YARDIMCI FONKSİYONLAR ---

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

def hafiza_bilgisi_goster():
    """Şu an hafızada ne olduğunu gösterir."""
    if st.session_state['aktif_veri'] is not None:
        df = st.session_state['aktif_veri']
        st.info(f"🧠 **Hafızadaki Veri:** {st.session_state['dosya_adi']} | **Satır Sayısı:** {len(df)}")
        
        # Önizleme butonu
        with st.expander("👀 Hafızadaki Veriyi Gör"):
            st.dataframe(df.head())
    else:
        st.warning("⚠️ Hafızada henüz veri yok. Lütfen 1. Aşamadan başlayın veya dosya yükleyin.")

def sql_calistir(df, query, yeni_dosya_adi):
    """Verilen DataFrame üzerinde SQL çalıştırır ve hafızayı günceller."""
    try:
        conn = sqlite3.connect(":memory:")
        # Kolon isimlerini temizle
        df.columns = [c.strip() for c in df.columns]
        df.to_sql("veriler", conn, index=False, if_exists="replace")
        
        # Sorguyu çalıştır
        sonuc_df = pd.read_sql_query(query, conn)
        conn.close()
        
        return sonuc_df
    except Exception as e:
        st.error(f"SQL Hatası: {e}")
        return None

# --- 3. YAN MENÜ ---
st.sidebar.header("İşlem Seçimi")
secim = st.sidebar.radio("Adımlar:", 
    ["1. Hazırlık (ZIP -> Birleştir)", 
     "2. Genel Filtre (BBZeminid)", 
     "3. Özel Rapor (KiKm)", 
     "4. Mimari Durum"])

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Hafızayı Temizle"):
    st.session_state['aktif_veri'] = None
    st.session_state['dosya_adi'] = ""
    st.rerun()

# --- 4. ANA AKIŞ ---

# ==========================================
# AŞAMA 1: HAZIRLIK
# ==========================================
if secim == "1. Hazırlık (ZIP -> Birleştir)":
    st.header("1. Aşama: Dosya Hazırlığı")
    st.markdown("ZIP dosyalarını yükleyin, sistem bunları birleştirip hafızaya alacaktır.")
    
    uploaded_files = st.file_uploader("ZIP Dosyalarını Seçin", type="zip", accept_multiple_files=True)
    
    if st.button("🚀 Birleştir ve Hafızaya Al") and uploaded_files:
        all_dataframes = []
        bar = st.progress(0)
        
        for i, zip_file in enumerate(uploaded_files):
            with zipfile.ZipFile(zip_file) as z:
                for filename in z.namelist():
                    if filename.endswith('.csv'):
                        with z.open(filename) as f:
                            sep = ayrac_bul(f)
                            try:
                                df = pd.read_csv(f, sep=sep, encoding="utf-8-sig", on_bad_lines='skip', engine='python')
                                all_dataframes.append(df)
                            except: pass
            bar.progress((i + 1) / len(uploaded_files))
            
        if all_dataframes:
            final_df = pd.concat(all_dataframes, ignore_index=True)
            
            # HAFIZAYA KAYDET
            st.session_state['aktif_veri'] = final_df
            st.session_state['dosya_adi'] = "Birlestirilmis_Ham_Veri"
            
            st.success(f"✅ İşlem Tamam! {len(final_df)} satır hafızaya alındı.")
            st.info("👉 Şimdi soldaki menüden 2. Aşamaya geçebilirsiniz.")
            
            # İndirme Opsiyonu
            st.download_button("📥 İstersen İndir (CSV)", to_csv_download(final_df), "Birlestirilmis.csv", "text/csv")

# ==========================================
# GENEL SQL ŞABLONU (Aşama 2, 3, 4 için)
# ==========================================
else:
    # Başlıkları ve Sorguları Tanımla
    if secim == "2. Genel Filtre (BBZeminid)":
        baslik = "2. Aşama: BBZeminid Filtresi"
        aciklama = "BBZeminid değeri '0' olmayanları ayıklar."
        query = 'SELECT * FROM veriler WHERE "BBZeminid" != "0"'
        yeni_ad = "Filtreli_Veri"
        
    elif secim == "3. Özel Rapor (KiKm)":
        baslik = "3. Aşama: KiKm Raporu"
        aciklama = "KiKm için özel kolonları seçer ve tekilleştirir (Distinct)."
        query = """
            SELECT DISTINCT AtZeminid, IlAd, IlceAd, MahalleAd, AdaNo, ParselNo, 
            MimariProjeDurumu, MimariProjeSayisi FROM veriler
        """
        yeni_ad = "KiKm_Raporu"
        
    elif secim == "4. Mimari Durum":
        baslik = "4. Aşama: Mimari Kontrol"
        aciklama = "MimariProjeDurumu 'Yok' olanları listeler."
        query = "SELECT * FROM veriler WHERE MimariProjeDurumu = 'Yok'"
        yeni_ad = "Mimari_Yok_Listesi"

    # Arayüzü Çiz
    st.header(baslik)
    st.markdown(aciklama)
    hafiza_bilgisi_goster()
    
    st.markdown("---")
    
    # KULLANICI SEÇİMİ: Hafızadaki mi, Yeni Dosya mı?
    kaynak = st.radio("Hangi veriyi kullanmak istersiniz?", ["🧠 Hafızadaki Veriyi Kullan", "📂 Yeni Dosya Yükle"])
    
    df_to_process = None
    
    if kaynak == "📂 Yeni Dosya Yükle":
        uploaded = st.file_uploader("CSV Yükle", type="csv")
        if uploaded:
            df_to_process = pd.read_csv(uploaded, encoding="utf-8-sig", on_bad_lines='skip')
    else:
        # Hafızayı Kullan
        if st.session_state['aktif_veri'] is not None:
            df_to_process = st.session_state['aktif_veri']
    
    # İŞLEM BUTONU
    if st.button(f"⚙️ {yeni_ad} Oluştur"):
        if df_to_process is not None:
            sonuc = sql_calistir(df_to_process, query, yeni_ad)
            
            if sonuc is not None:
                st.success(f"✅ İşlem Başarılı! {len(sonuc)} satır bulundu.")
                
                # HAFIZAYI GÜNCELLEME SEÇENEĞİ
                st.session_state['aktif_veri'] = sonuc
                st.session_state['dosya_adi'] = yeni_ad
                st.info("💾 Sonuç hafızaya kaydedildi. Bir sonraki aşamada bu veriyi kullanabilirsiniz.")
                
                # İndirme Butonu
                st.download_button(f"📥 {yeni_ad} İndir", to_csv_download(sonuc), f"{yeni_ad}.csv", "text/csv")
        else:
            st.error("❌ İşlenecek veri bulunamadı!")

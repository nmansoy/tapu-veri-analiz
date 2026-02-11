import streamlit as st
import pandas as pd
import zipfile
import csv
import io
import time

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Tapu Analiz v12 (Web)",
    page_icon="📂",
    layout="wide"
)

# --- STİL VE BAŞLIK ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .success-box { padding:10px; background-color:#d4edda; color:#155724; border-radius:5px; margin-bottom:10px; }
    .warning-box { padding:10px; background-color:#fff3cd; color:#856404; border-radius:5px; margin-bottom:10px; }
    </style>
""", unsafe_allow_html=True)

st.title("📂 Tapu Veri Merkezi (Kayıpsız Mod - v12)")
st.markdown("**Özellik:** `QUOTE_NONE` modu aktiftir. Tırnak işaretlerinden kaynaklı satır kayıplarını engeller.")

# --- SESSION STATE (HAFIZA) BAŞLATMA ---
if 'data_asama1' not in st.session_state: st.session_state['data_asama1'] = None
if 'data_asama2' not in st.session_state: st.session_state['data_asama2'] = None
if 'data_asama3' not in st.session_state: st.session_state['data_asama3'] = None
if 'data_asama4' not in st.session_state: st.session_state['data_asama4'] = None
if 'loglar' not in st.session_state: st.session_state['loglar'] = []

# --- YARDIMCI FONKSİYONLAR ---

def log_ekle(mesaj):
    """Logları sisteme ekler."""
    zaman = time.strftime("%H:%M:%S")
    st.session_state['loglar'].insert(0, f"[{zaman}] {mesaj}")

def csv_indir_hazirla(df):
    """DataFrame'i indirilebilir CSV formatına çevirir."""
    return df.to_csv(index=False, sep=',', encoding='utf-8-sig').encode('utf-8-sig')

def smart_load_dataframe(file_obj):
    """
    KRİTİK: Veri kaybını önleyen özel okuyucu.
    csv.QUOTE_NONE kullanarak tırnak hatalarını yoksayar.
    """
    try:
        # Dosyanın başına sar
        file_obj.seek(0)
        
        # 1. Ayıraç Tespiti
        sample_line = file_obj.readline()
        if isinstance(sample_line, bytes):
            sample_line = sample_line.decode('utf-8', errors='ignore')
        file_obj.seek(0) # Tekrar başa sar

        delimiters = ['|', ';', ',']
        counts = {d: sample_line.count(d) for d in delimiters}
        detected_sep = max(counts, key=counts.get)
        if counts[detected_sep] == 0: detected_sep = ','

        # 2. Pandas Okuma (Lossless Mode)
        df = pd.read_csv(
            file_obj,
            sep=detected_sep,
            dtype=str,                 # Tüm verileri string al (Tip hatası önler)
            quoting=csv.QUOTE_NONE,    # Tırnakları yoksay (Kayıpsız modun sırrı burası)
            on_bad_lines='warn',       # Hatalı satırları logla ama okumaya çalış
            encoding='utf-8-sig',
            encoding_errors='replace',
            engine='python'            # Python motoru daha esnektir
        )

        # 3. Sütun Temizliği
        df.columns = df.columns.str.strip().str.replace('"', '').str.replace('\ufeff', '')
        
        return df

    except Exception as e:
        log_ekle(f"Okuma Hatası: {e}")
        return None

# --- YAN PANEL (LOGLAR) ---
with st.sidebar:
    st.header("📋 İşlem Logları")
    if st.button("Logları Temizle"):
        st.session_state['loglar'] = []
    
    log_text = "\n".join(st.session_state['loglar'])
    st.text_area("Sistem Mesajları", value=log_text, height=400)

# --- ARAYÜZ DÜZENİ ---

# AŞAMA 1: YÜKLEME VE BİRLEŞTİRME
st.header("1️⃣ AŞAMA 1: ZIP/CSV Yükle ve Birleştir")
col1, col2 = st.columns([2, 1])

with col1:
    uploaded_files = st.file_uploader("ZIP veya CSV dosyalarını seçin", type=['zip', 'csv'], accept_multiple_files=True)

with col2:
    if st.button("⚙️ Birleştir ve Hazırla", key="btn1"):
        if uploaded_files:
            with st.spinner("Dosyalar okunuyor ve birleştiriliyor (Kayıpsız Mod)..."):
                dfs = []
                for uploaded_file in uploaded_files:
                    # ZIP İŞLEME
                    if uploaded_file.name.endswith('.zip'):
                        with zipfile.ZipFile(uploaded_file) as z:
                            for fn in z.namelist():
                                if fn.endswith('.csv'):
                                    with z.open(fn) as f:
                                        log_ekle(f"Okunuyor: {fn} (ZIP içinden)")
                                        df = smart_load_dataframe(f)
                                        if df is not None: dfs.append(df)
                    # CSV İŞLEME
                    else:
                        log_ekle(f"Okunuyor: {uploaded_file.name}")
                        df = smart_load_dataframe(uploaded_file)
                        if df is not None: dfs.append(df)

                if dfs:
                    full_df = pd.concat(dfs, ignore_index=True)
                    st.session_state['data_asama1'] = full_df
                    log_ekle(f"✅ AŞAMA 1 TAMAM: Toplam {len(full_df)} satır yüklendi.")
                    st.success(f"Toplam Veri: {len(full_df)} Satır")
                else:
                    st.error("Hiç veri okunamadı!")
        else:
            st.warning("Lütfen önce dosya seçin.")

if st.session_state['data_asama1'] is not None:
    with st.expander("🔍 Aşama 1 Verisini Önizle"):
        st.dataframe(st.session_state['data_asama1'].head())
    st.download_button("💾 Aşama 1 Sonucunu İndir", csv_indir_hazirla(st.session_state['data_asama1']), "Asama1_HamVeri.csv", "text/csv")

st.markdown("---")

# AŞAMA 2: TEMİZLİK
st.header("2️⃣ AŞAMA 2: Temizlik (BBZeminid Filtresi)")
st.info("Kural: `BBZeminid` değeri '0' olmayan satırlar alınır.")

if st.button("⚙️ Temizliği Başlat", key="btn2"):
    if st.session_state['data_asama1'] is not None:
        df = st.session_state['data_asama1']
        if 'BBZeminid' in df.columns:
            res = df[df['BBZeminid'] != '0']
            st.session_state['data_asama2'] = res
            log_ekle(f"✅ AŞAMA 2 TAMAM: {len(res)} satır kaldı.")
            st.success(f"İşlem Başarılı! Kalan Veri: {len(res)}")
        else:
            st.error("Hata: 'BBZeminid' sütunu bulunamadı!")
            log_ekle("Hata: BBZeminid sütunu yok.")
    else:
        st.warning("Lütfen önce Aşama 1'i tamamlayın.")

if st.session_state['data_asama2'] is not None:
    st.download_button("💾 Aşama 2 Sonucunu İndir", csv_indir_hazirla(st.session_state['data_asama2']), "Asama2_TemizVeri.csv", "text/csv")

st.markdown("---")

# AŞAMA 3 VE 4 YANYANA
col3, col4 = st.columns(2)

# AŞAMA 3: KİKM RAPORU
with col3:
    st.header("3️⃣ AŞAMA 3: KiKm Raporu")
    st.info("Benzersiz (Distinct) Parsel Listesi")
    
    if st.button("⚙️ Rapor Oluştur", key="btn3"):
        if st.session_state['data_asama2'] is not None:
            df = st.session_state['data_asama2']
            target_cols = ["AtZeminid", "IlAd", "IlceAd", "MahalleAd", "AdaNo", "ParselNo", "MimariProjeDurumu", "MimariProjeSayisi"]
            
            # Var olan sütunları seç
            available_cols = [c for c in df.columns if c in target_cols]
            
            res = df[available_cols].drop_duplicates()
            st.session_state['data_asama3'] = res
            log_ekle(f"✅ AŞAMA 3 TAMAM: {len(res)} benzersiz kayıt.")
            st.success(f"Rapor Hazır: {len(res)} Satır")
        else:
            st.warning("Önce Aşama 2'yi tamamlayın.")

    if st.session_state['data_asama3'] is not None:
         st.download_button("💾 KiKm Raporunu İndir", csv_indir_hazirla(st.session_state['data_asama3']), "Asama3_KiKmRaporu.csv", "text/csv")

# AŞAMA 4: MİMARİ YOK
with col4:
    st.header("4️⃣ AŞAMA 4: Mimari 'Yok'")
    st.info("MimariProjeDurumu = 'Yok' olanlar")
    
    if st.button("⚙️ Analiz Et", key="btn4"):
        if st.session_state['data_asama2'] is not None:
            df = st.session_state['data_asama2']
            if 'MimariProjeDurumu' in df.columns:
                res = df[df['MimariProjeDurumu'] == 'Yok']
                st.session_state['data_asama4'] = res
                log_ekle(f"✅ AŞAMA 4 TAMAM: {len(res)} adet projesi olmayan bulundu.")
                st.success(f"Bulunan: {len(res)} Satır")
            else:
                st.error("'MimariProjeDurumu' sütunu yok.")
        else:
            st.warning("Önce Aşama 2'yi tamamlayın.")

    if st.session_state['data_asama4'] is not None:
         st.download_button("💾 Mimari Yok Listesini İndir", csv_indir_hazirla(st.session_state['data_asama4']), "Asama4_MimariYok.csv", "text/csv")

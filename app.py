import streamlit as st
import pandas as pd
import zipfile
import csv
import io
import time

# --- SAYFA VE TASARIM AYARLARI ---
st.set_page_config(
    page_title="Tapu Veri Merkezi Pro",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS İLE GÖRSEL GÜZELLEŞTİRME ---
st.markdown("""
    <style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #f4f6f9;
    }
    
    /* Kart Görünümü (Beyaz Kutular) */
    .css-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* Başlık Stili */
    h1 {
        color: #1a237e;
        font-family: 'Segoe UI', sans-serif;
    }
    h2, h3 {
        color: #283593;
    }
    
    /* Butonlar */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Metrik Kutuları */
    div[data-testid="stMetric"] {
        background-color: #e8eaf6;
        padding: 10px;
        border-radius: 8px;
        border-left: 5px solid #3949ab;
    }
    
    /* Uyarı ve Başarı Mesajları */
    .stAlert {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE BAŞLATMA ---
if 'data_asama1' not in st.session_state: st.session_state['data_asama1'] = None
if 'data_asama2' not in st.session_state: st.session_state['data_asama2'] = None
if 'data_asama3' not in st.session_state: st.session_state['data_asama3'] = None
if 'data_asama4' not in st.session_state: st.session_state['data_asama4'] = None
if 'loglar' not in st.session_state: st.session_state['loglar'] = []

# --- MANTIK FONKSİYONLARI (DEĞİŞMEDİ) ---

def log_ekle(mesaj):
    zaman = time.strftime("%H:%M:%S")
    st.session_state['loglar'].insert(0, f"[{zaman}] {mesaj}")

def csv_indir_hazirla(df):
    return df.to_csv(index=False, sep=',', encoding='utf-8-sig').encode('utf-8-sig')

def smart_load_dataframe(file_obj):
    try:
        file_obj.seek(0)
        sample_line = file_obj.readline()
        if isinstance(sample_line, bytes):
            sample_line = sample_line.decode('utf-8', errors='ignore')
        file_obj.seek(0)

        delimiters = ['|', ';', ',']
        counts = {d: sample_line.count(d) for d in delimiters}
        detected_sep = max(counts, key=counts.get)
        if counts[detected_sep] == 0: detected_sep = ','

        df = pd.read_csv(
            file_obj,
            sep=detected_sep,
            dtype=str,
            quoting=csv.QUOTE_NONE,
            on_bad_lines='warn',
            encoding='utf-8-sig',
            encoding_errors='replace',
            engine='python'
        )
        df.columns = df.columns.str.strip().str.replace('"', '').str.replace('\ufeff', '')
        return df
    except Exception as e:
        log_ekle(f"Hata: {e}")
        return None

# --- YAN MENÜ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830155.png", width=100) # Sembolik İkon
    st.title("İşlem Merkezi")
    st.markdown("---")
    
    st.info("💡 **İpucu:** Dosyalar işlenirken 'Kayıpsız Mod' aktiftir. Tırnak işaretleri veriyi bölmez.")
    
    st.markdown("---")
    st.header("📋 Sistem Logları")
    if st.button("🗑️ Logları Temizle", help="Log geçmişini siler"):
        st.session_state['loglar'] = []
    
    log_container = st.container()
    with log_container:
        for log in st.session_state['loglar'][:10]: # Son 10 log
            st.caption(f"🔹 {log}")

# --- ANA EKRAN ---

st.title("🏢 Tapu Veri Analiz Platformu")
st.markdown("##### v12.0 - Profesyonel Veri İşleme Arayüzü")
st.markdown("---")

# ==========================================
# 1. KART: YÜKLEME VE BİRLEŞTİRME
# ==========================================
with st.container():
    st.markdown("### 📥 1. Aşama: Veri Yükleme")
    
    col_upload, col_action = st.columns([2, 1])
    
    with col_upload:
        uploaded_files = st.file_uploader(
            "ZIP veya CSV dosyalarını buraya sürükleyin", 
            type=['zip', 'csv'], 
            accept_multiple_files=True,
            help="Birden fazla dosya seçebilirsiniz."
        )

    with col_action:
        st.write("") # Boşluk
        st.write("") 
        if st.button("🚀 Verileri Birleştir ve Yükle", type="primary"):
            if uploaded_files:
                with st.spinner("Dosyalar analiz ediliyor..."):
                    dfs = []
                    start_time = time.time()
                    for uploaded_file in uploaded_files:
                        if uploaded_file.name.endswith('.zip'):
                            with zipfile.ZipFile(uploaded_file) as z:
                                for fn in z.namelist():
                                    if fn.endswith('.csv'):
                                        with z.open(fn) as f:
                                            df = smart_load_dataframe(f)
                                            if df is not None: dfs.append(df)
                        else:
                            df = smart_load_dataframe(uploaded_file)
                            if df is not None: dfs.append(df)

                    if dfs:
                        full_df = pd.concat(dfs, ignore_index=True)
                        st.session_state['data_asama1'] = full_df
                        elapsed = round(time.time() - start_time, 2)
                        log_ekle(f"Aşama 1 Tamamlandı. Süre: {elapsed}sn")
                        st.balloons()
                    else:
                        st.error("Veri okunamadı!")
            else:
                st.warning("Lütfen dosya seçin.")

    # Sonuç Gösterimi (Metrik)
    if st.session_state['data_asama1'] is not None:
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Satır", f"{len(st.session_state['data_asama1']):,}")
        m2.metric("Sütun Sayısı", f"{len(st.session_state['data_asama1'].columns)}")
        m3.download_button("💾 Ham Veriyi İndir", csv_indir_hazirla(st.session_state['data_asama1']), "1_HamVeri.csv", "text/csv")

# ==========================================
# 2. KART: TEMİZLİK
# ==========================================
st.markdown("### 🧹 2. Aşama: Veri Temizliği")
with st.expander("Detayları ve İşlemi Göster", expanded=True):
    col_filter_info, col_filter_btn = st.columns([3, 1])
    
    with col_filter_info:
        st.info("**Filtre Kuralı:** `BBZeminid` değeri '0' (sıfır) olmayan kayıtlar ayrıştırılacaktır.")
    
    with col_filter_btn:
        if st.button("🔍 Filtreyi Uygula"):
            if st.session_state['data_asama1'] is not None:
                df = st.session_state['data_asama1']
                if 'BBZeminid' in df.columns:
                    res = df[df['BBZeminid'] != '0']
                    st.session_state['data_asama2'] = res
                    log_ekle(f"Filtreleme bitti. Kalan: {len(res)}")
                else:
                    st.error("BBZeminid sütunu yok!")
            else:
                st.error("Önce 1. Aşamayı tamamlayın.")

    if st.session_state['data_asama2'] is not None:
        c1, c2 = st.columns(2)
        c1.metric("Temizlenmiş Veri", f"{len(st.session_state['data_asama2']):,}")
        c2.download_button("💾 Temiz Veriyi İndir", csv_indir_hazirla(st.session_state['data_asama2']), "2_TemizVeri.csv", "text/csv")

# ==========================================
# 3. KART: ANALİZLER (SEKMELİ YAPI)
# ==========================================
st.markdown("### 📊 3. ve 4. Aşama: Detaylı Analizler")

tab1, tab2 = st.tabs(["📑 KiKm Raporu (Aşama 3)", "🚫 Mimari Proje Kontrolü (Aşama 4)"])

# SEKME 1: KİKM
with tab1:
    st.write("Benzersiz parsel listesini oluşturur (Tekilleştirme).")
    if st.button("Oluştur: KiKm Listesi"):
        if st.session_state['data_asama2'] is not None:
            df = st.session_state['data_asama2']
            target = ["AtZeminid", "IlAd", "IlceAd", "MahalleAd", "AdaNo", "ParselNo", "MimariProjeDurumu", "MimariProjeSayisi"]
            cols = [c for c in df.columns if c in target]
            res = df[cols].drop_duplicates()
            st.session_state['data_asama3'] = res
            log_ekle(f"KiKm Raporu: {len(res)} satır.")
        else:
            st.warning("Veri kaynağı (Aşama 2) eksik.")
            
    if st.session_state['data_asama3'] is not None:
        st.success(f"Sonuç: {len(st.session_state['data_asama3'])} benzersiz kayıt.")
        st.dataframe(st.session_state['data_asama3'].head(3), use_container_width=True)
        st.download_button("💾 KiKm Raporunu İndir", csv_indir_hazirla(st.session_state['data_asama3']), "3_KiKmRaporu.csv", "text/csv")

# SEKME 2: MİMARİ YOK
with tab2:
    st.write("Mimari projesi 'Yok' olan kayıtları filtreler.")
    if st.button("Analiz Et: Projesi Olmayanlar"):
        if st.session_state['data_asama2'] is not None:
            df = st.session_state['data_asama2']
            if 'MimariProjeDurumu' in df.columns:
                res = df[df['MimariProjeDurumu'] == 'Yok']
                st.session_state['data_asama4'] = res
                log_ekle(f"Mimari Yok Analizi: {len(res)} satır.")
            else:
                st.error("MimariProjeDurumu sütunu bulunamadı.")
        else:
            st.warning("Veri kaynağı (Aşama 2) eksik.")
            
    if st.session_state['data_asama4'] is not None:
        st.error(f"Dikkat: {len(st.session_state['data_asama4'])} adet kayıtta proje yok!")
        st.dataframe(st.session_state['data_asama4'].head(3), use_container_width=True)
        st.download_button("💾 Listeyi İndir", csv_indir_hazirla(st.session_state['data_asama4']), "4_MimariYok.csv", "text/csv")

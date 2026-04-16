import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import time
import requests

# ================= CONFIG & PAGE SETUP =================
st.set_page_config(page_title="Kuyumhane Fiyat Stüdyosu", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS FOR REACT APP STYLING ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Arka Plan ve Ana Metin */
.stApp {
    background-color: #FAF5EE;
    color: #2A1F12;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #FEFAF5;
    border-right: 1.5px solid #EDE7DC;
}

/* KURUMSAL LOGO */
.kuyumhane-logo {
    font-size: 26px; 
    color: #B0946A; 
    font-weight: 800; 
    letter-spacing: 5px; 
    text-transform: uppercase;
    margin-bottom: 5px;
    font-family: 'Playfair Display', serif;
}

/* Başlıklar */
h1, h2, h3, h4 {
    font-family: 'Playfair Display', serif !important;
    color: #1E1208 !important;
}

/* Sekmeler (Tabs) */
.stTabs [data-baseweb="tab-list"] {
    gap: 20px;
    border-bottom: 2px solid #EDE7DC;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    color: #9A8F82;
    padding-bottom: 12px;
    font-size: 16px;
}
.stTabs [aria-selected="true"] {
    color: #2A1F12 !important;
    border-bottom-color: #B7860B !important;
}

/* Butonlar */
.stButton > button {
    background-color: #F0EBE2;
    color: #5A4A38;
    border: 1.5px solid #D8CEBD;
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    background-color: #3D2B1A;
    color: #FFF8EE;
    border-color: #3D2B1A;
}

/* YENİ ÜRÜN FORMU TASARIM DÜZELTMESİ */
[data-testid="stForm"] {
    background-color: #FEFAF5 !important;
    border: 1.5px solid #EDE7DC !important;
    border-radius: 20px !important;
    padding: 30px !important;
    box-shadow: 0 8px 24px rgba(90,60,20,0.04) !important;
}

/* Input Alanları */
.stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
    background-color: #FFFFFF !important;
    border: 1px solid #E0D8CE !important;
    border-radius: 10px;
    color: #2A1F12;
    font-family: 'Inter', sans-serif;
    padding: 10px 15px;
}

/* Uploader Kutusu */
[data-testid="stFileUploadDropzone"] {
    background-color: #FFFFFF !important;
    border: 2px dashed #D8CEBD !important;
    border-radius: 12px !important;
    padding: 20px !important;
}

/* Arama ve Filtre Kutusu Arkası */
.search-filter-container {
    background-color: #FEFAF5;
    padding: 15px;
    border-radius: 16px;
    border: 1.5px solid #EDE7DC;
    margin-bottom: 20px;
}

/* Veri Çerçevesi (Dataframe) Gizleme */
.stDataFrame { display: none; }
</style>
""", unsafe_allow_html=True)


# ================= GOOGLE SHEETS =================
@st.cache_resource
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gsheets"],
        scopes=scope
    )
    return gspread.authorize(creds)

client = get_gspread_client()
sheet = client.open("Etsy Price Sync").get_worksheet(0)

# ================= HELPERS =================
def safe_float(value):
    try:
        if isinstance(value, str):
            value = value.replace(",", ".")
            value = value.replace("₺", "").replace("$", "").replace("%", "").strip()
        return float(value)
    except:
        return 0.0

def image_to_base64(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        img = Image.open(uploaded_file).convert("RGB")
        # Google Sheets'in 50.000 karakterlik hücre sınırını aşmamak için optimize ediyoruz
        img.thumbnail((250, 250)) 
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=65)
        b64_str = base64.b64encode(buf.getvalue()).decode()
        
        # Eğer hala sınırın üzerindeyse (nadiren olur), biraz daha küçült
        if len(b64_str) > 49000:
            img.thumbnail((150, 150))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=50)
            b64_str = base64.b64encode(buf.getvalue()).decode()
            
        return b64_str
    except Exception as e:
        return ""

# ================= AUTO FETCH CURRENCY =================
@st.cache_data(ttl=3600)
def fetch_live_rates():
    rates = {"USDTRY": 32.5}
    try:
        r_usd = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        rates["USDTRY"] = r_usd["rates"]["TRY"]
    except:
        pass
    return rates

live_rates = fetch_live_rates()

# ================= DATA LOAD =================
try:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df = df[df["Ürün"].astype(str).str.strip() != ""]
except Exception as e:
    st.error("Google Sheets bağlantısında bir sorun oluştu. Lütfen sayfayı yenileyin.")
    df = pd.DataFrame()

# ================= SIDEBAR (FİYAT STÜDYOSU AYARLARI) =================
with st.sidebar:
    st.markdown("<div class='kuyumhane-logo'>✦ KUYUMHANE</div>", unsafe_allow_html=True)
    st.markdown("<h1 style='margin-top:0px; margin-bottom: 20px; font-size: 22px;'>Fiyat Ayarları</h1>", unsafe_allow_html=True)

    dolar_kuru = st.number_input(
        "USD/TRY Kuru (Otomatik/Manuel)",
        value=float(live_rates["USDTRY"]),
        step=0.1
    )

    st.markdown("### Gümüş Değerleri")
    gumus_gram_tl = st.number_input("Has Gümüş TL/gr", value=35.0, step=1.0) 
    iscilik_gumus_usd = st.number_input("Gümüş İşçilik $/gr", value=1.5, step=0.1)

    st.markdown("### Altın Değerleri")
    altin_has_gram_usd = st.number_input("Has Altın $/gr", value=75.0, step=1.0) 
    iscilik_altin = st.number_input("Altın İşçilik $/gr", value=10.0, step=1.0)

    st.markdown("---")
    st.markdown("### Sabit Giderler & Kesintiler")
    kargo_tl = st.number_input("Kargo (Her Ürün İçin TL)", value=650.0, step=50.0)
    indirim_yuzde = st.number_input("Müşteri İndirimi %", value=25.0, step=5.0)
    
    st.markdown("### Etsy Türkiye Gerçek Kesintileri")
    etsy_transaction = 6.5
    etsy_payments = 6.5
    etsy_regulatory = 1.5
    st.caption(f"Toplam Yüzdelik Kesinti: %{etsy_transaction + etsy_payments + etsy_regulatory} + 3 TL + 0.20$")

    offsite_ads = st.checkbox("Offsite Ads Risk Payı Ekle (%15)", value=False)

    st.markdown("---")
    st.markdown("### Kâr Simülasyonu")
    kar_multiplier = st.slider("Kâr Çarpanı", 1.0, 3.0, 1.0, 0.1)
    toplu_kar = st.number_input("Toplu Kâr Artışı TL", value=0.0, step=100.0)


# ================= ETSY PROFIT LOGIC =================
def etsy_net_profit(alici_oder_tl, maliyet_tl):
    usd = alici_oder_tl / dolar_kuru
    
    transaction_fee = usd * 0.065
    payments_fee = (usd * 0.065) + (3.0 / dolar_kuru) 
    regulatory_fee = usd * 0.015 
    listing_fee = 0.20
    offsite_fee = (usd * 0.15) if offsite_ads else 0.0

    total_fee_usd = transaction_fee + payments_fee + regulatory_fee + listing_fee + offsite_fee
    total_fee_tl = total_fee_usd * dolar_kuru
    
    net_kar_tl = alici_oder_tl - total_fee_tl - maliyet_tl
    return net_kar_tl, total_fee_tl

def calculate_price(row):
    gr = safe_float(row.get("Gr", 0))
    hedef_kar = safe_float(row.get("Hedef Kar", 0))
    kar = (hedef_kar * kar_multiplier) + toplu_kar

    kaplama = safe_float(row.get("KaplamaTL", 0))
    lazer = safe_float(row.get("LazerTL", 0))
    mine = safe_float(row.get("MineTL", 0))
    ekstra = safe_float(row.get("EkstraTL", 0))
    
    maden = row.get("Maden", "Gümüş")
    if maden == "Altın":
        maliyet_tl = (gr * altin_has_gram_usd * dolar_kuru) + (gr * iscilik_altin * dolar_kuru)
    else:
        maliyet_tl = (gr * gumus_gram_tl) + (gr * iscilik_gumus_usd * dolar_kuru)

    maliyet_tl += (kaplama + lazer + mine + ekstra + kargo_tl)
    
    komisyon_yuzdesi = (14.5 + (15 if offsite_ads else 0)) / 100
    indirim_orani = indirim_yuzde / 100
    sabit_kesintiler_tl = 3.0 + (0.20 * dolar_kuru)
    
    try:
        fiyat_etiket = (maliyet_tl + kar + sabit_kesintiler_tl) / ((1 - indirim_orani) * (1 - komisyon_yuzdesi))
    except ZeroDivisionError:
        fiyat_etiket = 0

    alici_oder = fiyat_etiket * (1 - indirim_orani)
    usd = fiyat_etiket / dolar_kuru
    net_kar, toplam_kesinti = etsy_net_profit(alici_oder, maliyet_tl)

    return fiyat_etiket, alici_oder, usd, maliyet_tl, net_kar


# ================= EDIT MODAL =================
@st.dialog("✏️ Ürünü Düzenle")
def edit_product(row, row_idx):
    st.markdown("<style> .stDialog { background-color: #FEFAF5; border-radius: 24px; } </style>", unsafe_allow_html=True)
    with st.form("edit_form"):
        st.markdown(f"### {row.get('Ürün', '')}")
        ad = st.text_input("Ürün Adı", value=row.get("Ürün", ""))
        
        c1, c2 = st.columns(2)
        with c1:
            maden = st.selectbox("Maden", ["Gümüş", "Altın"], index=0 if row.get("Maden", "Gümüş") == "Gümüş" else 1)
            gram = st.number_input("Ağırlık (Gram)", value=float(safe_float(row.get("Gr", 0))), step=0.1)
            kar = st.number_input("Hedef Net Kâr (₺)", value=float(safe_float(row.get("Hedef Kar", 3000))))
        with c2:
            kategori = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"], index=["Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"].index(row.get("Kategori", "Yüzük") if row.get("Kategori", "Yüzük") in ["Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"] else "Diğer"))
            kaplama = st.number_input("Kaplama (₺)", value=float(safe_float(row.get("KaplamaTL", 0))))
            lazer = st.number_input("Lazer/Mine/Ekstra Toplamı (₺)", value=float(safe_float(row.get("LazerTL", 0))) + float(safe_float(row.get("MineTL", 0))) + float(safe_float(row.get("EkstraTL", 0))))

        if st.form_submit_button("💳 Değişiklikleri Kaydet", use_container_width=True):
            try:
                updated = [
                    ad, maden, gram, kar, row.get("GörselData", ""), kategori, kaplama, lazer, 0, 0
                ]
                sheet.update(f"A{row_idx}:J{row_idx}", [updated], value_input_option="USER_ENTERED")
                st.success("Başarıyla Güncellendi!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error("Güncellenirken bir hata oluştu. Google Sheets sınırı aşılmış olabilir.")

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Özet", "🖼️ Galeri", "➕ Yeni Ürün Ekle"])

# ================= TAB 1: DASHBOARD (ÖZET) =================
with tab1:
    if not df.empty:
        total_etiket = 0
        total_alici = 0
        total_net = 0

        for _, row in df.iterrows():
            fiyat_etiket, alici_oder, usd, maliyet, net = calculate_price(row)
            total_etiket += fiyat_etiket
            total_alici += alici_oder
            total_net += net

        st.markdown(f"""
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px;">
            <div style="background: linear-gradient(135deg, #FEF7E0, #FFFCF8); border: 2px solid #E8C060; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(232,192,96,0.1);">
                <div style="font-size: 13px; color: #8A6A20; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px;">Toplam Etiket</div>
                <div style="font-size: 32px; font-weight: 800; color: #7A500A; font-family: monospace;">₺{total_etiket:,.2f}</div>
            </div>
            <div style="background: #EEF4F7; border: 1.5px solid #86B0C0; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(134,176,192,0.1);">
                <div style="font-size: 13px; color: #3A6A7A; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px;">Alıcı Öder (İndirimli)</div>
                <div style="font-size: 32px; font-weight: 800; color: #2A5A6A; font-family: monospace;">₺{total_alici:,.2f}</div>
            </div>
            <div style="background: #EAFCE8; border: 1.5px solid #8AC88A; border-radius: 20px; padding: 30px; grid-column: span 2; box-shadow: 0 4px 15px rgba(138,200,138,0.1);">
                <div style="font-size: 14px; color: #3A7A3A; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px;">GERÇEK NET KÂR HEDEFİ ({len(df)} Ürün)</div>
                <div style="font-size: 42px; font-weight: 800; color: #2A5A2A; font-family: monospace;">₺{total_net:,.2f}</div>
                <div style="font-size: 14px; color: #5A8A5A; margin-top: 8px;">Kargo, işçilik ve tüm Türkiye Etsy kesintileri (%14.5 + 3₺ + 0.20$) düşüldükten sonra net cebinize giren.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Kayıtlı ürün bulunmamaktadır.")

# ================= TAB 2: PRODUCTS (GALERİ) =================
with tab2:
    st.markdown("<div class='search-filter-container'>", unsafe_allow_html=True)
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search = st.text_input("🔍 Ürün Ara", placeholder="Örn: 14K Yüzük", label_visibility="collapsed")
    with col_filter:
        kategori_filtre_galeri = st.selectbox("Kategori", ["Tümü", "Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"], label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    if not df.empty:
        if search:
            f_df = df[df["Ürün"].str.contains(search, case=False)]
        else:
            f_df = df

        if kategori_filtre_galeri != "Tümü":
            f_df = f_df[f_df["Kategori"] == kategori_filtre_galeri]

        cols = st.columns(4)
        for idx, row in f_df.reset_index().iterrows():
            row_idx = int(row["index"]) + 2
            fiyat_etiket, alici_oder, usd, maliyet, net = calculate_price(row)
            
            maden_renk = "#4A7A8A" if row.get('Maden') != 'Altın' else "#B7860B"
            maden_bg = "#EEF4F7" if row.get('Maden') != 'Altın' else "#FEF7E6"
            maden_label = str(row.get('Maden', 'Gümüş')).upper()

            with cols[idx % 4]:
                st.markdown(f"""<div style="background:#FFFCF8; border:1.5px solid #EDE7DC; border-radius:18px; overflow:hidden; box-shadow:0 4px 12px rgba(90,60,20,0.05); margin-bottom: 15px;"><div style="width:100%; padding-bottom:75%; position:relative; background:{maden_bg};"><img src="data:image/jpeg;base64,{row.get('GörselData', '')}" onerror="this.style.display='none'" style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover;" /><div style="position:absolute; top:10px; left:10px;"><span style="font-size:10px; font-weight:700; letter-spacing:1.5px; color:{maden_renk}; background:rgba(255,255,255,0.9); padding:5px 10px; border-radius:20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">{maden_label}</span></div></div><div style="padding:15px;"><div style="font-size:16px; font-weight:800; color:#2A1F12; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-family: 'Playfair Display', serif;">{row.get('Ürün', 'İsimsiz')}</div><div style="font-size:13px; color:#9A8F82; margin-bottom:12px; font-weight: 500;">{row.get('Kategori', 'Diğer')} · {row.get('Gr', '0')}g</div><div style="font-size:22px; font-weight:800; color:#A0721A; font-family:monospace; line-height: 1;">₺{fiyat_etiket:,.2f}</div><div style="font-size:13px; color:#B0A090; margin-top: 4px; font-weight: 600;">Alıcı Öder: ₺{alici_oder:,.2f}</div><div style="background: rgba(42, 90, 42, 0.08); border-radius: 8px; padding: 6px 10px; margin-top: 12px; border: 1px solid rgba(42, 90, 42, 0.15);"><div style="font-size:13px; color:#2A5A2A; font-weight:700; text-align: center;">Net Kâr: ₺{net:,.0f}</div></div></div></div>""", unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 1])
                if c1.button("✏️ Düzenle", key=f"edit_{idx}", use_container_width=True):
                    edit_product(row, row_idx)
                if c2.button("🗑️ Sil", key=f"del_{idx}", use_container_width=True):
                    sheet.delete_rows(row_idx)
                    st.rerun()

# ================= TAB 3: NEW PRODUCT (YENİ ÜRÜN) =================
with tab3:
    st.markdown("<h2 style='margin-bottom: 25px; color: #1E1208; font-size: 28px;'>✨ Yeni Ürün Oluştur</h2>", unsafe_allow_html=True)
    
    with st.form("new_product", clear_on_submit=True):
        st.markdown("<h4 style='color: #8A7A6A; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px;'>Temel Bilgiler</h4>", unsafe_allow_html=True)
        ad = st.text_input("Ürün Adı", placeholder="Örn: 14K Altın Harf Kolye")
        
        c1, c2 = st.columns(2)
        with c1:
            maden = st.selectbox("Maden", ["Gümüş", "Altın"])
            gram = st.number_input("Ağırlık (Gram)", step=0.1, min_value=0.0)
        with c2:
            kategori = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"])
            kar = st.number_input("Hedef Net Kâr (₺)", value=3000, step=100)

        st.markdown("<hr style='border: 1px solid #EDE7DC; margin: 25px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #8A7A6A; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px;'>Ekstra Giderler (Opsiyonel)</h4>", unsafe_allow_html=True)
        
        c3, c4, c5, c6 = st.columns(4)
        with c3:
            mine = st.number_input("Mine (₺)", value=0, step=50)
        with c4:
            kaplama = st.number_input("Kaplama (₺)", value=0, step=50)
        with c5:
            lazer = st.number_input("Lazer (₺)", value=0, step=50)
        with c6:
            ekstra = st.number_input("Ekstra Gider (₺)", value=0, step=50)

        st.markdown("<hr style='border: 1px solid #EDE7DC; margin: 25px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #8A7A6A; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px;'>Ürün Görseli</h4>", unsafe_allow_html=True)
        img = st.file_uploader("Sürükle bırak veya bilgisayarından seç", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        if st.form_submit_button("💳 Sisteme Kaydet", use_container_width=True):
            if ad and gram > 0:
                img64 = image_to_base64(img)
                try:
                    sheet.append_row(
                        [ad, maden, gram, kar, img64, kategori, kaplama, lazer, mine, ekstra],
                        value_input_option="USER_ENTERED"
                    )
                    st.success(f"🎉 Harika! {ad} başarıyla vitrine eklendi.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error("Görsel boyutu Google Sheets sınırını aşıyor. Lütfen daha düşük çözünürlüklü bir fotoğraf seçin veya kodu kontrol edin.")
            else:
                st.error("Lütfen Ürün Adı ve Gramajını eksiksiz girin.")

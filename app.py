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

/* KURUMSAL LOGO BÜYÜTÜLDÜ */
.kuyumhane-logo {
    font-size: 24px; 
    color: #B0946A; 
    font-weight: 800; 
    letter-spacing: 4px; 
    text-transform: uppercase;
    margin-bottom: 5px;
    font-family: 'Playfair Display', serif;
}

/* Başlıklar */
h1, h2, h3 {
    font-family: 'Playfair Display', serif !important;
    color: #1E1208 !important;
}

/* Sekmeler (Tabs) */
.stTabs [data-baseweb="tab-list"] {
    gap: 15px;
    border-bottom: 2px solid #EDE7DC;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    color: #9A8F82;
    padding-bottom: 10px;
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
    border-radius: 11px;
    font-weight: 600;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    background-color: #3D2B1A;
    color: #FFF8EE;
    border-color: #3D2B1A;
}

/* YENİ ÜRÜN FORMU TASARIM DÜZELTMESİ (Renk Uyumsuzluğunu Giderir) */
[data-testid="stForm"] {
    background-color: transparent !important;
    border: 1.5px solid #EDE7DC !important;
    border-radius: 17px !important;
    padding: 20px !important;
    box-shadow: 0 2px 8px rgba(90,60,20,0.03) !important;
}

/* Input Alanları */
.stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
    background-color: #FFF !important;
    border: 1px solid #E0D8CE !important;
    border-radius: 10px;
    color: #2A1F12;
    font-family: 'Inter', sans-serif;
}

/* Uploader Kutusu */
[data-testid="stFileUploadDropzone"] {
    background-color: #FFF !important;
    border: 2px dashed #D8CEBD !important;
    border-radius: 12px !important;
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
    img = Image.open(uploaded_file).convert("RGB")
    img.thumbnail((400, 400))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return base64.b64encode(buf.getvalue()).decode()

# ================= AUTO FETCH METALS & CURRENCY =================
@st.cache_data(ttl=3600) # Saatte bir günceller
def fetch_live_rates():
    rates = {"USDTRY": 32.0, "XAUUSD": 85.0, "XAGUSD": 1.0} # Fallback değerleri
    try:
        # USD/TRY Çekme
        r_usd = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        rates["USDTRY"] = r_usd["rates"]["TRY"]
        
        # Gerçek bir projede Altın/Gümüş için metals-api.com veya yfinance kullanılır.
        # Burada simüle ediyoruz veya ücretsiz public API varsa entegre ediyoruz.
        # Has Altın gram = (Ons fiyatı / 31.1)
    except:
        pass
    return rates

live_rates = fetch_live_rates()

# ================= DATA LOAD =================
data = sheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    df = df[df["Ürün"].astype(str).str.strip() != ""]

# ================= SIDEBAR (FİYAT STÜDYOSU AYARLARI) =================
with st.sidebar:
    st.markdown("<div class='kuyumhane-logo'>✦ KUYUMHANE</div>", unsafe_allow_html=True)
    st.markdown("<h1 style='margin-top:0px; margin-bottom: 20px;'>Fiyat Ayarları</h1>", unsafe_allow_html=True)

    dolar_kuru = st.number_input(
        "USD/TRY Kuru (Otomatik/Manuel)",
        value=float(live_rates["USDTRY"]),
        step=0.1
    )

    st.markdown("### Gümüş Değerleri")
    gumus_gram_tl = st.number_input("Has Gümüş TL/gr", value=37.0)
    iscilik_gumus_usd = st.number_input("Gümüş İşçilik $/gr", value=1.5, step=0.1)

    st.markdown("### Altın Değerleri")
    altin_has_gram_usd = st.number_input("Has Altın $/gr", value=85.0)
    iscilik_altin = st.number_input("Altın İşçilik $/gr", value=10.0)

    st.markdown("---")
    st.markdown("### Sabit Giderler & Kesintiler")
    kargo_tl = st.number_input("Kargo (Her Ürün İçin TL)", value=650.0)
    indirim_yuzde = st.number_input("Müşteri İndirimi %", value=25.0)
    
    st.markdown("### Etsy Türkiye Gerçek Kesintileri")
    etsy_transaction = 6.5
    etsy_payments = 6.5
    etsy_regulatory = 1.5
    st.caption(f"Toplam Yüzdelik Kesinti: %{etsy_transaction + etsy_payments + etsy_regulatory} + 3 TL + 0.20$")

    offsite_ads = st.checkbox("Offsite Ads Risk Payı Ekle (%15)", value=False)

    st.markdown("---")
    st.markdown("### Kâr Simülasyonu")
    kar_multiplier = st.slider("Kâr Çarpanı", 1.0, 3.0, 1.0, 0.1)
    toplu_kar = st.number_input("Toplu Kâr Artışı TL", value=0.0)

    kategori_filtre = st.selectbox("Kategori Filtresi", ["Tümü", "Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"])

# ================= ETSY PROFIT LOGIC (TÜRKİYE DÜZELTMESİ) =================
def etsy_net_profit(alici_oder_tl, maliyet_tl):
    usd = alici_oder_tl / dolar_kuru
    
    # Gerçek Türkiye Kesintileri
    transaction_fee = usd * 0.065
    payments_fee = (usd * 0.065) + (3.0 / dolar_kuru) # %6.5 + 3 TL
    regulatory_fee = usd * 0.015 # Türkiye Yasal İşletme Kesintisi
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
    
    # Toplam Komisyon Oranı Hesaplama
    komisyon_yuzdesi = (14.5 + (15 if offsite_ads else 0)) / 100
    indirim_orani = indirim_yuzde / 100
    
    # Formül: Etiket Fiyatı = (Maliyet + Hedef Kar + 3 TL + (0.20$ * Kur)) / ( (1 - İndirim) * (1 - KomisyonYuzdesi) )
    sabit_kesintiler_tl = 3.0 + (0.20 * dolar_kuru)
    
    try:
        fiyat_etiket = (maliyet_tl + kar + sabit_kesintiler_tl) / ((1 - indirim_orani) * (1 - komisyon_yuzdesi))
    except ZeroDivisionError:
        fiyat_etiket = 0

    alici_oder = fiyat_etiket * (1 - indirim_orani)
    usd = fiyat_etiket / dolar_kuru
    net_kar, toplam_kesinti = etsy_net_profit(alici_oder, maliyet_tl)

    return fiyat_etiket, alici_oder, usd, maliyet_tl, net_kar


# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Özet", "🖼️ Galeri", "➕ Yeni Ürün"])

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
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
            <div style="background: linear-gradient(135deg, #FEF7E0, #FFFCF8); border: 2px solid #E8C060; border-radius: 17px; padding: 20px;">
                <div style="font-size: 11px; color: #8A6A20; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 5px;">Toplam Etiket</div>
                <div style="font-size: 28px; font-weight: 800; color: #7A500A; font-family: monospace;">₺{total_etiket:,.2f}</div>
            </div>
            <div style="background: #EEF4F7; border: 1.5px solid #86B0C0; border-radius: 17px; padding: 20px;">
                <div style="font-size: 11px; color: #3A6A7A; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 5px;">Alıcı Öder (İndirimli)</div>
                <div style="font-size: 28px; font-weight: 800; color: #2A5A6A; font-family: monospace;">₺{total_alici:,.2f}</div>
            </div>
            <div style="background: #EAFCE8; border: 1.5px solid #8AC88A; border-radius: 17px; padding: 20px; grid-column: span 2;">
                <div style="font-size: 11px; color: #3A7A3A; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 5px;">GERÇEK NET KÂR HEDEFİ ({len(df)} Ürün)</div>
                <div style="font-size: 36px; font-weight: 800; color: #2A5A2A; font-family: monospace;">₺{total_net:,.2f}</div>
                <div style="font-size: 12px; color: #5A8A5A; margin-top: 5px;">Kargo, işçilik ve tüm Türkiye Etsy kesintileri (%14.5 + 3₺ + 0.20$) düşüldükten sonra net cebinize giren.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background: #FFFCF8; border: 1.5px solid #EDE7DC; border-radius: 14px; padding: 15px; margin-top: 15px;">
            <div style="font-size: 11px; color: #8A7A6A; font-weight: 700; letter-spacing: 1.3px; text-transform: uppercase; margin-bottom: 10px;">Geçerli Değerler ve Kesintiler</div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #F0EDE8; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>Kargo (her ürün)</span><strong style="color: #4A3F32; font-family: monospace;">₺{kargo_tl}</strong></div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #F0EDE8; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>Etsy Türkiye Toplam Kesinti</span><strong style="color: #A04030; font-family: monospace;">%14.5 + 3 TL + $0.20</strong></div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #F0EDE8; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>Offsite Ads (Risk Payı)</span><strong style="color: #A04030; font-family: monospace;">{off_ads}</strong></div>
            <div style="display: flex; justify-content: space-between; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>USD/TRY (Anlık)</span><strong style="color: #4A3F32; font-family: monospace;">₺{dolar_kuru}</strong></div>
        </div>
        """.format(kargo_tl=kargo_tl, dolar_kuru=dolar_kuru, off_ads="Açık (%15)" if offsite_ads else "Kapalı"), unsafe_allow_html=True)
    else:
        st.info("Kayıtlı ürün bulunmamaktadır.")

# ================= TAB 2: PRODUCTS (GALERİ) =================
with tab2:
    search = st.text_input("Ürün Ara...", placeholder="Örn: Damla Yüzük")

    if not df.empty:
        if search:
            f_df = df[df["Ürün"].str.contains(search, case=False)]
        else:
            f_df = df

        if kategori_filtre != "Tümü":
            f_df = f_df[f_df["Kategori"] == kategori_filtre]

        cols = st.columns(4)
        for idx, row in f_df.reset_index().iterrows():
            row_idx = int(row["index"]) + 2
            fiyat_etiket, alici_oder, usd, maliyet, net = calculate_price(row)
            
            maden_renk = "#4A7A8A" if row.get('Maden') != 'Altın' else "#B7860B"
            maden_bg = "#EEF4F7" if row.get('Maden') != 'Altın' else "#FEF7E6"
            maden_label = str(row.get('Maden', 'Gümüş')).upper()

            with cols[idx % 4]:
                st.markdown(f"""
                <div style="background:#FFFCF8; border:1.5px solid #EDE7DC; border-radius:17px; overflow:hidden; box-shadow:0 2px 8px rgba(90,60,20,0.06); margin-bottom: 10px;">
                    <div style="width:100%; padding-bottom:90%; position:relative; background:{maden_bg};">
                        <img src="data:image/jpeg;base64,{row.get('GörselData', '')}" onerror="this.style.display='none'" style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover;" />
                        <div style="position:absolute; top:7px; left:7px;">
                            <span style="font-size:9px; font-weight:700; letter-spacing:1.1px; color:{maden_renk}; background:rgba(255,255,255,0.85); padding:3px 7px; border-radius:18px;">{maden_label}</span>
                        </div>
                    </div>
                    <div style="padding:12px;">
                        <div style="font-size:13px; font-weight:700; color:#2A1F12; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{row.get('Ürün', 'İsimsiz')}</div>
                        <div style="font-size:11px; color:#9A8F82; margin-bottom:8px;">{row.get('Kategori', 'Diğer')} · {row.get('Gr', '0')}g</div>
                        <div style="font-size:16px; font-weight:800; color:#A0721A; font-family:monospace;">₺{fiyat_etiket:,.2f}</div>
                        <div style="font-size:10px; color:#B0A090;">Alıcı Öder: ₺{alici_oder:,.2f}</div>
                        <div style="font-size:11px; color:#2A5A2A; margin-top:4px; font-weight:600;">Net Kâr: ₺{net:,.0f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 1])
                if c1.button("🗑️ Sil", key=f"del{idx}", use_container_width=True):
                    sheet.delete_rows(row_idx)
                    st.rerun()

# ================= TAB 3: NEW PRODUCT (YENİ ÜRÜN) =================
with tab3:
    st.markdown("<h3 style='margin-bottom: 20px; color: #3D2B1A !important;'>✨ Yeni Ürün Ekle</h3>", unsafe_allow_html=True)
    
    with st.form("new_product", clear_on_submit=True):
        ad = st.text_input("Ürün Adı", placeholder="Örn: 14K Altın Harf Kolye")
        
        c1, c2 = st.columns(2)
        with c1:
            maden = st.selectbox("Maden", ["Gümüş", "Altın"])
            gram = st.number_input("Ağırlık (Gram)", step=0.1, min_value=0.0)
        with c2:
            kategori = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"])
            kar = st.number_input("Hedef Net Kâr (₺)", value=3000, step=100)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        c3, c4, c5, c6 = st.columns(4)
        with c3:
            mine = st.number_input("Mine (₺)", value=0, step=50)
        with c4:
            kaplama = st.number_input("Kaplama (₺)", value=0, step=50)
        with c5:
            lazer = st.number_input("Lazer (₺)", value=0, step=50)
        with c6:
            ekstra = st.number_input("Ekstra Gider (₺)", value=0, step=50)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        img = st.file_uploader("Ürün Görseli Yükle", type=["jpg", "jpeg", "png"])
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        if st.form_submit_button("💳 Ürünü Ekle ve Kaydet", use_container_width=True):
            if ad and gram > 0:
                img64 = image_to_base64(img)
                sheet.append_row(
                    [ad, maden, gram, kar, img64, kategori, kaplama, lazer, mine, ekstra],
                    value_input_option="USER_ENTERED"
                )
                st.success(f"🎉 {ad} başarıyla sisteme eklendi!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("Lütfen Ürün Adı ve Gramajını eksiksiz girin.")

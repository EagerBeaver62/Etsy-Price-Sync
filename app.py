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

/* Input Alanları */
.stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
    background-color: #FEFAF5;
    border: 1.5px solid #E0D8CE;
    border-radius: 10px;
    color: #2A1F12;
    font-family: 'Inter', sans-serif;
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
            value = value.replace("₺", "").replace("$", "").strip()
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

# ================= AUTO USD TRY =================
@st.cache_data(ttl=3600)
def get_usd_try():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        data = r.json()
        return data["rates"]["TRY"]
    except:
        return None

usd_try = get_usd_try()

# ================= DATA LOAD =================
data = sheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    df = df[df["Ürün"].astype(str).str.strip() != ""]

# ================= SIDEBAR (FİYAT STÜDYOSU AYARLARI) =================
with st.sidebar:
    st.markdown("<div style='font-size:10px; color:#B0946A; font-weight:700; letter-spacing:3px; text-transform:uppercase;'>✦ KUYUMHANE</div>", unsafe_allow_html=True)
    st.markdown("<h1 style='margin-top:0px; margin-bottom: 20px;'>Fiyat Ayarları</h1>", unsafe_allow_html=True)

    dolar_kuru = st.number_input(
        "USD/TRY Kuru (Manuel override)",
        value=float(usd_try) if usd_try else 32.0,
        step=0.1
    )

    st.markdown("### Gümüş Değerleri")
    gumus_gram_tl = st.number_input("Has Gümüş TL/gr", value=37.0)
    iscilik_gumus_usd = st.number_input("Gümüş İşçilik $/gr", value=1.5, step=0.1)

    st.markdown("### Altın Değerleri")
    altin_has_gram_usd = st.number_input("Has Altın $/gr", value=85.0)
    iscilik_altin = st.number_input("Altın İşçilik $/gr", value=10.0)

    st.markdown("---")
    st.markdown("### Sabit Giderler")
    kargo_tl = st.number_input("Kargo (Her Ürün İçin TL)", value=650.0)
    indirim_yuzde = st.number_input("Etsy İndirimi %", value=25.0)

    st.markdown("---")
    st.markdown("### Kâr Simülasyonu")
    kar_multiplier = st.slider("Kâr Çarpanı", 1.0, 3.0, 1.0, 0.1)
    toplu_kar = st.number_input("Toplu Kâr Artışı TL", value=0.0)

    kategori_filtre = st.selectbox("Kategori Filtresi", ["Tümü", "Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"])

# ================= ETSY PROFIT LOGIC =================
def etsy_net_profit(price_tl, cost_tl):
    usd = price_tl / dolar_kuru
    etsy_fee = usd * 0.065
    payment_fee = usd * 0.03 + 0.25
    listing_fee = 0.20
    total_fee = (etsy_fee + payment_fee + listing_fee) * dolar_kuru
    return price_tl - total_fee - cost_tl

def calculate_price(row):
    gr = safe_float(row.get("Gr", 0))
    hedef_kar = safe_float(row.get("Hedef Kar", 0))
    kar = (hedef_kar * kar_multiplier) + toplu_kar

    kaplama = safe_float(row.get("KaplamaTL", 0))
    lazer = safe_float(row.get("LazerTL", 0))
    mine = safe_float(row.get("MineTL", 0))
    ekstra = safe_float(row.get("EkstraTL", 0))
    
    # Kategoriye/Madene göre maliyet hesaplama (Streamlit altyapısı baz alındı)
    maden = row.get("Maden", "Gümüş")
    if maden == "Altın":
        maliyet = (gr * altin_has_gram_usd * dolar_kuru) + (gr * iscilik_altin * dolar_kuru)
    else:
        maliyet = (gr * gumus_gram_tl) + (gr * iscilik_gumus_usd * dolar_kuru)

    maliyet += (kaplama + lazer + mine + ekstra + kargo_tl)
    komisyon = 0.17 + (indirim_yuzde / 100)
    
    fiyat_etiket = (maliyet + kar) / (1 - komisyon)
    alici_oder = fiyat_etiket * (1 - (indirim_yuzde / 100)) # İndirimli son fiyat
    usd = fiyat_etiket / dolar_kuru
    net = etsy_net_profit(alici_oder, maliyet) # Etsy komisyonları alıcının ödediği tutar üzerinden kesilir

    return fiyat_etiket, alici_oder, usd, maliyet, net


# ================= EDIT MODAL =================
@st.dialog("Ürünü Düzenle")
def edit_product(row, row_idx):
    st.markdown("<style> .stDialog { background-color: #FEFAF5; border-radius: 24px; } </style>", unsafe_allow_html=True)
    with st.form("edit_form"):
        ad = st.text_input("Ürün Adı", value=row.get("Ürün", ""))
        maden = st.selectbox("Maden", ["Gümüş", "Altın"], index=0 if row.get("Maden", "Gümüş") == "Gümüş" else 1)
        kategori = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"], index=["Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"].index(row.get("Kategori", "Yüzük")))
        
        c1, c2 = st.columns(2)
        with c1:
            gram = st.number_input("Ağırlık (Gram)", value=float(safe_float(row.get("Gr", 0))), step=0.1)
            kar = st.number_input("Hedef Net Kâr (₺)", value=float(safe_float(row.get("Hedef Kar", 3000))))
            mine = st.number_input("Mine (₺)", value=float(safe_float(row.get("MineTL", 0))))
        with c2:
            kaplama = st.number_input("Kaplama (₺)", value=float(safe_float(row.get("KaplamaTL", 0))))
            lazer = st.number_input("Lazer (₺)", value=float(safe_float(row.get("LazerTL", 0))))
            ekstra = st.number_input("Ekstra Gider (₺)", value=float(safe_float(row.get("EkstraTL", 0))))

        if st.form_submit_button("Güncelle", use_container_width=True):
            updated = [
                ad, maden, gram, kar, row.get("GörselData", ""), kategori, kaplama, lazer, mine, ekstra
            ]
            sheet.update(f"A{row_idx}:J{row_idx}", [updated], value_input_option="USER_ENTERED")
            st.success("Başarıyla Güncellendi!")
            time.sleep(0.5)
            st.rerun()

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
                <div style="font-size: 11px; color: #3A6A7A; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 5px;">Alıcı Öder</div>
                <div style="font-size: 28px; font-weight: 800; color: #2A5A6A; font-family: monospace;">₺{total_alici:,.2f}</div>
            </div>
            <div style="background: #EAFCE8; border: 1.5px solid #8AC88A; border-radius: 17px; padding: 20px; grid-column: span 2;">
                <div style="font-size: 11px; color: #3A7A3A; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 5px;">NET KÂR HEDEFİ ({len(df)} Ürün)</div>
                <div style="font-size: 36px; font-weight: 800; color: #2A5A2A; font-family: monospace;">₺{total_net:,.2f}</div>
                <div style="font-size: 12px; color: #5A8A5A; margin-top: 5px;">kargo, komisyon ve işçilik düşüldükten sonra</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background: #FFFCF8; border: 1.5px solid #EDE7DC; border-radius: 14px; padding: 15px; margin-top: 15px;">
            <div style="font-size: 11px; color: #8A7A6A; font-weight: 700; letter-spacing: 1.3px; text-transform: uppercase; margin-bottom: 10px;">Sabit Değerler</div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #F0EDE8; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>Kargo (her ürün)</span><strong style="color: #4A3F32; font-family: monospace;">₺{kargo_tl}</strong></div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #F0EDE8; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>İşçilik</span><strong style="color: #4A3F32; font-family: monospace;">${iscilik_gumus_usd} / ürün</strong></div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #F0EDE8; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>Etsy İndirimi</span><strong style="color: #4A3F32; font-family: monospace;">%{indirim_yuzde}</strong></div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #F0EDE8; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>Etsy Komisyonu</span><strong style="color: #4A3F32; font-family: monospace;">%6.5</strong></div>
            <div style="display: flex; justify-content: space-between; padding: 8px 0; font-size: 13px; color: #7A7060;"><span>USD/TRY</span><strong style="color: #4A3F32; font-family: monospace;">₺{dolar_kuru}</strong></div>
        </div>
        """.format(kargo_tl=kargo_tl, iscilik_gumus_usd=iscilik_gumus_usd, indirim_yuzde=indirim_yuzde, dolar_kuru=dolar_kuru), unsafe_allow_html=True)
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
                        <div style="font-size:10px; color:#B0A090;">alıcı: ₺{alici_oder:,.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 1])
                if c1.button("✏️ Düzenle", key=f"edit{idx}", use_container_width=True):
                    edit_product(row, row_idx)
                if c2.button("🗑️ Sil", key=f"del{idx}", use_container_width=True):
                    sheet.delete_rows(row_idx)
                    st.rerun()

# ================= TAB 3: NEW PRODUCT (YENİ ÜRÜN) =================
with tab3:
    st.markdown("<h3 style='margin-bottom: 20px;'>✨ Yeni Ürün Ekle</h3>", unsafe_allow_html=True)
    with st.form("new_product"):
        ad = st.text_input("Ürün Adı")
        c1, c2 = st.columns(2)
        with c1:
            maden = st.selectbox("Maden", ["Gümüş", "Altın"])
            gram = st.number_input("Ağırlık (Gram)", step=0.1)
        with c2:
            kategori = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe", "Broş", "Diğer"])
            kar = st.number_input("Hedef Net Kâr (₺)", value=3000)

        c3, c4, c5, c6 = st.columns(4)
        with c3:
            mine = st.number_input("Mine (₺)", value=0)
        with c4:
            kaplama = st.number_input("Kaplama (₺)", value=0)
        with c5:
            lazer = st.number_input("Lazer (₺)", value=0)
        with c6:
            ekstra = st.number_input("Ekstra Gider (₺)", value=0)

        img = st.file_uploader("Ürün Görseli Yükle", type=["jpg", "jpeg", "png"])

        if st.form_submit_button("💳 Ürünü Ekle", use_container_width=True):
            if ad and gram > 0:
                img64 = image_to_base64(img)
                sheet.append_row(
                    [ad, maden, gram, kar, img64, kategori, kaplama, lazer, mine, ekstra],
                    value_input_option="USER_ENTERED"
                )
                st.success(f"{ad} başarıyla eklendi!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Lütfen Ürün Adı ve Gramajı eksiksiz girin.")

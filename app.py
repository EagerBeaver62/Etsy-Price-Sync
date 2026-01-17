import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Etsy Profesyonel Dashboard", layout="wide", page_icon="💎")

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_gsheet_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

# --- GÖRSEL İŞLEME (GÜÇLENDİRİLMİŞ SIKIŞTIRMA) ---
def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.thumbnail((100, 100)) # Daha da küçültüldü
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=30, optimize=True) # Maksimum sıkıştırma
            return base64.b64encode(buffered.getvalue()).decode()
        except: return ""
    return ""

@st.cache_data(ttl=3600)
def piyasa_verileri():
    try:
        dolar = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return dolar, altin, gumus
    except: return 35.0, 2650.0, 31.0

# --- VERİLERİ ÇEK ---
dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()
sheet = get_gsheet_client()

if sheet:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
else:
    df = pd.DataFrame()

# --- TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    .product-card {
        background-color: white; padding: 15px; border-radius: 12px;
        border: 1px solid #eee; text-align: center; margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .delete-btn button { background-color: #ff4b4b !important; color: white !important; font-size: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Ayarlar")
    kur = st.number_input("💵 Dolar Kuru", value=float(dolar_kuru))
    gr_iscilik = st.number_input("🛠️ İşçilik ($/gr)", value=1.5)
    kargo = st.number_input("🚚 Kargo (TL)", value=450.0)
    indirim = st.number_input("🏷️ İndirim (%)", value=10.0)
    komisyon = 0.17
    
    st.divider()
    view_mode = st.radio("Görünüm Seçimi", ["🎨 Kart Görünümü", "📋 Liste Görünümü"])

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Fiyat Paneli")
tab1, tab2 = st.tabs(["📊 Ürün Yönetimi", "➕ Yeni Ürün"])

with tab2:
    with st.form("ekle_form", clear_on_submit=True):
        u_ad = st.text_input("Ürün Adı")
        u_maden = st.selectbox("Maden", ["Gümüş", "Altın"])
        u_gr = st.number_input("Gram", value=5.0)
        u_kar = st.number_input("Hedef Kar (TL)", value=2000.0)
        u_img = st.file_uploader("Ürün Görseli")
        if st.form_submit_button("Kaydet ve Gönder"):
            if u_ad and sheet:
                img_b64 = image_to_base64(u_img)
                sheet.append_row([u_ad, u_maden, u_gr, u_kar, img_b64])
                st.success("Ürün eklendi!")
                st.rerun()

with tab1:
    if not df.empty:
        if view_mode == "🎨 Kart Görünümü":
            cols = st.columns(4)
            for idx, row in df.iterrows():
                ons = ons_altin if row['Maden'] == "Altın" else ons_gumus
                maliyet = ((ons/31.1035) * float(row['Gr']) * kur) + (float(row['Gr']) * gr_iscilik * kur) + kargo
                fiyat = (maliyet + float(row['Hedef Kar'])) / (1 - (komisyon + indirim/100))
                
                img_src = f"data:image/jpeg;base64,{row['GörselData']}" if row['GörselData'] else ""
                
                with cols[idx % 4]:
                    st.markdown(f"""
                    <div class="product-card">
                        <img src="{img_src}" style="width:100%; height:120px; object-fit:contain;">
                        <p style="font-weight:bold; margin-top:5px;">{row['Ürün']}</p>
                        <h3 style="color:#861211;">{round(fiyat, 2)} ₺</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"🗑️ Sil: {row['Ürün']}", key=f"del_{idx}"):
                        sheet.delete_rows(idx + 2) # Başlık satırı + 0-index dengesi
                        st.rerun()
        
        else: # Liste Görünümü
            st.subheader("Ürün Fiyat Listesi")
            df_display = df.copy()
            # Fiyatları hesaplayıp tabloya ekleyelim
            prices = []
            for _, r in df.iterrows():
                ons = ons_altin if r['Maden'] == "Altın" else ons_gumus
                m = ((ons/31.1035) * float(r['Gr']) * kur) + (float(r['Gr']) * gr_iscilik * kur) + kargo
                f = (m + float(r['Hedef Kar'])) / (1 - (komisyon + indirim/100))
                prices.append(f"{round(f, 2)} ₺")
            
            df_display['Hesaplanan Fiyat'] = prices
            st.table(df_display[['Ürün', 'Maden', 'Gr', 'Hesaplanan Fiyat']])

    else:
        st.info("Henüz ürün bulunmuyor.")

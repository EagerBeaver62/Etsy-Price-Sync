import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import time

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="CRIPP Jewelry Panel", layout="wide")

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_info(st.secrets["gsheets"], scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error("Google Sheets bağlantı hatası! Lütfen Secrets kısmını kontrol edin.")
        st.stop()

client = get_gspread_client()
sheet = client.open("Etsy Price Sync").get_worksheet(0)

# --- YARDIMCI FONKSİYONLAR ---
def safe_float(value, default=0.0):
    """Virgül ve nokta ayrımını akıllıca çözer"""
    try:
        if value is None or value == "": return default
        val_str = str(value).strip().replace(",", ".")
        return float(val_str)
    except:
        return default

def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file).convert("RGB")
            img.thumbnail((400, 400)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=75, optimize=True)
            return base64.b64encode(buffered.getvalue()).decode()
        except: return ""
    return ""

# --- DÜZENLEME MODALI ---
@st.dialog("Ürün Bilgilerini Düzenle")
def edit_product_modal(row_data, row_idx):
    with st.form(f"modal_form_{row_idx}"):
        new_ad = st.text_input("Ürün Adı", value=row_data['Ürün'])
        c1, c2 = st.columns(2)
        with c1:
            # ÖNEMLİ: text_input yapıldı, + ve - butonları artık olmayacak.
            new_gr_text = st.text_input("Gram (Örn: 5,7)", value=str(row_data.get('Gr')).replace(".", ","))
            new_kar = st.number_input("Hedef Kar (TL)", value=safe_float(row_data.get('Hedef Kar')))
        with c2:
            new_kap = st.number_input("Kaplama (TL)", value=safe_float(row_data.get('KaplamaTL')))
            new_laz = st.number_input("Lazer (TL)", value=safe_float(row_data.get('LazerTL')))
            new_min = st.number_input("Mine (TL)", value=safe_float(row_data.get('MineTL')))
        
        if st.form_submit_button("✅ Kaydet"):
            fixed_gr = safe_float(new_gr_text)
            updated_row = [new_ad, row_data['Maden'], fixed_gr, new_kar, row_data['GörselData'], "Yüzük", new_kap, new_laz, new_min]
            sheet.update(f"A{row_idx}:I{row_idx}", [updated_row])
            st.success("Güncellendi!")
            time.sleep(0.5)
            st.rerun()

# --- VERİ ÇEKME VE EKRAN ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

with st.sidebar:
    st.title("💎 Fiyat Ayarları")
    dolar = st.number_input("💵 Dolar Kuru", value=44.07)
    gumus_has = st.number_input("Gümüş Has (TL)", value=125.60)
    kargo = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim = st.number_input("🏷️ İndirim (%)", value=15.0)

st.title("Etsy Akıllı Fiyat Paneli")
t1, t2 = st.tabs(["📊 Liste", "➕ Ekle"])

with t1:
    if not df.empty:
        cols = st.columns(4)
        for idx, row in df.iterrows():
            row_idx = idx + 2
            gr = safe_float(row.get('Gr'))
            kar = safe_float(row.get('Hedef Kar'))
            
            # Hesaplama
            komisyon = 0.17 + (indirim / 100)
            maliyet = (gr * gumus_has) + (gr * 1.5 * dolar) + safe_float(row.get('KaplamaTL')) + kargo
            fiyat = (maliyet + kar) / (1 - komisyon)

            with cols[idx % 4]:
                st.image(f"data:image/jpeg;base64,{row['GörselData']}", use_container_width=True)
                st.markdown(f"**{row['Ürün']}**")
                st.success(f"{fiyat:,.0f} ₺")
                st.caption(f"⚖️ {gr} gr")
                if st.button("✏️ Düzenle", key=f"ed_{idx}"):
                    edit_product_modal(row, row_idx)

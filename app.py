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
    except: return None

# --- GÖRSEL İŞLEME ---
def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            if img.mode != "RGB": img = img.convert("RGB")
            img.thumbnail((120, 120)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=50, optimize=True)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except: return ""
    return ""

@st.cache_data(ttl=3600)
def piyasa_verileri():
    try:
        dolar = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return dolar, altin, gumus
    except: return 43.27, 2650.0, 31.0

dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()
sheet = get_gsheet_client()

if sheet:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
else:
    df = pd.DataFrame()

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Ayarlar")
    kur = st.number_input("💵 Dolar Kuru", value=float(dolar_kuru), format="%.2f")
    gr_iscilik = st.number_input("🛠️ İşçilik ($/gr)", value=1.5, format="%.2f")
    kargo = st.number_input("🚚 Kargo (TL)", value=450.0)
    indirim = st.number_input("🏷️ İndirim (%)", value=10.0)
    komisyon = 0.17
    view_mode = st.radio("Görünüm Seçimi", ["🎨 Kart Görünümü", "📋 Liste Görünümü"])

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Fiyat Paneli")
tab1, tab2 = st.tabs(["📊 Ürün Yönetimi", "➕ Yeni Ürün"])

with tab2:
    with st.form("ekle_form", clear_on_submit=True):
        u_ad = st.text_input("Ürün Adı")
        u_maden = st.selectbox("Maden", ["Gümüş", "Altın"])
        u_gr = st.text_input("Gram (Örn: 3.5)", value="0.0")
        u_kar = st.number_input("Hedef Kar (TL)", value=2000.0)
        u_img = st.file_uploader("Ürün Görseli", type=["jpg", "jpeg", "png"])
        if st.form_submit_button("Excel'e Kaydet"):
            if u_ad and sheet:
                safe_gr = u_gr.replace(',', '.')
                img_data = image_to_base64(u_img)
                sheet.append_row([u_ad, u_maden, safe_gr, u_kar, img_data])
                st.success("Ürün Excel'e kaydedildi!")
                st.rerun()

with tab1:
    if not df.empty:
        # --- ARAMA KUTUSU ---
        search_term = st.text_input("🔍 Ürün Adı ile Ara...", "").lower()
        
        # Filtreleme işlemi
        filtered_df = df[df['Ürün'].astype(str).str.lower().str.contains(search_term)]
        
        if not filtered_df.empty:
            if view_mode == "🎨 Kart Görünümü":
                cols = st.columns(4)
                for idx, row in filtered_df.reset_index().iterrows():
                    m_ad = row.get('Ürün', 'İsimsiz Ürün')
                    m_tur = row.get('Maden', 'Gümüş')
                    try: m_gram = float(str(row.get('Gr', 0)).replace(',', '.'))
                    except: m_gram = 0.0
                    try: m_hedef = float(str(row.get('Hedef Kar', 0)).replace(',', '.'))
                    except: m_hedef = 0.0
                    m_img = row.get('GörselData', '')
                    
                    ons = ons_altin if m_tur == "Altın" else ons_gumus
                    maliyet = ((ons/31.1035) * m_gram * kur) + (m_gram * gr_iscilik * kur) + kargo
                    fiyat = (maliyet + m_hedef) / (1 - (komisyon + indirim/100))
                    
                    with cols[idx % 4]:
                        st.markdown(f"""
                        <div style="background-color:white; padding:15px; border-radius:15px; border:1px solid #eee; text-align:center; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            <img src="data:image/jpeg;base64,{m_img}" style="width:100%; height:130px; object-fit:contain; border-radius:10px; background-color:#f8f9fa;" onerror="this.src='https://via.placeholder.com/150?text=Gorsel+Yok';">
                            <p style="font-weight:bold; margin-top:10px; color:#333; height:40px; overflow:hidden;">{m_ad}</p>
                            <h3 style="color:#861211; margin:0;">{round(fiyat, 2)} ₺</h3>
                            <p style="color:#666; font-size:12px;">{m_gram} gr / $ {round(fiyat/kur, 2)}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"🗑️ Sil", key=f"del_{row['index']}"):
                            sheet.delete_rows(int(row['index']) + 2)
                            st.rerun()
            else:
                st.dataframe(filtered_df, use_container_width=True)
        else:
            st.warning("Aradığınız kriterlere uygun ürün bulunamadı.")
    else:
        st.info("Henüz ürün bulunmuyor.")

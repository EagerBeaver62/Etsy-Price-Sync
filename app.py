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
    except:
        return None

# --- GÖRSEL İŞLEME ---
def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            if img.mode != "RGB": img = img.convert("RGB")
            img.thumbnail((100, 100)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=40, optimize=True)
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
    except: return 43.0, 2650.0, 31.0

dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()
sheet = get_gsheet_client()

if sheet:
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
    except: df = pd.DataFrame()
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
        if st.form_submit_button("Kaydet ve Gönder"):
            if u_ad and sheet:
                safe_gr = u_gr.replace(',', '.')
                img_b64 = image_to_base64(u_img)
                sheet.append_row([u_ad, u_maden, safe_gr, u_kar, img_b64])
                st.success("Ürün başarıyla eklendi!")
                st.rerun()

with tab1:
    if not df.empty:
        if view_mode == "🎨 Kart Görünümü":
            cols = st.columns(4)
            for idx, row in df.iterrows():
                m_ad = str(row.get('Ürün', '-'))
                m_tur = str(row.get('Maden', 'Gümüş'))
                
                # Gramaj ve Kar Hesaplama
                try: m_gram = float(str(row.get('Gr', 0)).replace(',', '.'))
                except: m_gram = 0.0
                try: m_hedef = float(str(row.get('Hedef Kar', 0)).replace(',', '.'))
                except: m_hedef = 0.0
                
                # Görsel Çekme (Düzeltilen Kısım)
                m_img = str(row.get('GörselData', ''))
                
                ons = ons_altin if m_tur == "Altın" else ons_gumus
                maliyet = ((ons/31.1035) * m_gram * kur) + (m_gram * gr_iscilik * kur) + kargo
                fiyat = (maliyet + m_hedef) / (1 - (komisyon + indirim/100))
                
                # Görsel HTML yapısı (Garantiye almak için base64 kontrolü)
                img_html = ""
                if m_img and len(m_img) > 100:
                    img_html = f'<img src="data:image/jpeg;base64,{m_img}" style="width:100%; height:120px; object-fit:contain; border-radius:5px;">'
                else:
                    img_html = '<div style="width:100%; height:120px; background:#f0f0f0; display:flex; align-items:center; justify-content:center; border-radius:5px; color:#ccc;">Görsel Yok</div>'

                with cols[idx % 4]:
                    st.markdown(f"""
                    <div style="background-color:white; padding:15px; border-radius:12px; border:1px solid #eee; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                        {img_html}
                        <p style="font-weight:bold; margin-top:10px; font-size:14px; height:40px; overflow:hidden;">{m_ad}</p>
                        <h3 style="color:#861211; margin:0;">{round(fiyat, 2)} ₺</h3>
                        <p style="color:gray; font-size:12px; margin-bottom:10px;">{m_gram} gr</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("🗑️ Sil", key=f"del_{idx}"):
                        sheet.delete_rows(idx + 2)
                        st.rerun()
        else:
            st.dataframe(df[['Ürün', 'Maden', 'Gr', 'Hedef Kar']], use_container_width=True)
    else:
        st.info("Henüz ürün bulunmuyor.")

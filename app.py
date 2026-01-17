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
        return None

# --- GÖRSEL İŞLEME (EKSTRA SIKIŞTIRILMIŞ) ---
def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            # Standart renk formatına zorla
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Boyutu minimuma indir (Hücrede yer kaplamaması için)
            img.thumbnail((80, 80)) 
            
            buffered = BytesIO()
            # Kaliteyi %20'ye düşürerek veriyi çok hafifletiyoruz
            img.save(buffered, format="JPEG", quality=20, optimize=True)
            
            return base64.b64encode(buffered.getvalue()).decode()
        except:
            return ""
    return ""

@st.cache_data(ttl=3600)
def piyasa_verileri():
    try:
        dolar = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return dolar, altin, gumus
    except: return 35.0, 2650.0, 31.0

# --- VERİLERİ HAZIRLA ---
dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()
sheet = get_gsheet_client()

if sheet:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
else:
    df = pd.DataFrame()

# --- SIDEBAR (AYARLAR) ---
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
                # Google Sheets'e yeni satırı ekle
                sheet.append_row([u_ad, u_maden, u_gr, u_kar, img_b64])
                st.success("Ürün eklendi!")
                st.rerun()

with tab1:
    if not df.empty:
        if view_mode == "🎨 Kart Görünümü":
            cols = st.columns(4)
            for idx, row in df.iterrows():
                m_ad = row.get('Ürün', '-')
                m_tur = row.get('Maden', 'Gümüş')
                m_gram = float(row.get('Gr', 0))
                m_hedef = float(row.get('Hedef Kar', 0))
                m_img = row.get('GörselData', '')

                ons = ons_altin if m_tur == "Altın" else ons_gumus
                maliyet = ((ons/31.1035) * m_gram * kur) + (m_gram * gr_iscilik * kur) + kargo
                fiyat = (maliyet + m_hedef) / (1 - (komisyon + indirim/100))
                
                img_src = f"data:image/jpeg;base64,{m_img}" if m_img else ""
                
                with cols[idx % 4]:
                    st.markdown(f"""
                    <div style="background-color:white; padding:15px; border-radius:12px; border:1px solid #ddd; text-align:center; margin-bottom:10px;">
                        <img src="{img_src}" style="width:100%; height:120px; object-fit:contain; background-color:#f9f9f9;">
                        <p style="font-weight:bold; margin-top:5px; height:20px; overflow:hidden;">{m_ad}</p>
                        <h3 style="color:#861211;">{round(fiyat, 2)} ₺</h3>
                        <p style="color:gray; font-size:14px;">$ {round(fiyat/kur, 2)}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"🗑️ Sil", key=f"del_{idx}"):
                        sheet.delete_rows(idx + 2)
                        st.rerun()
        
        else: # LİSTE GÖRÜNÜMÜ
            st.subheader("Ürün Fiyat Listesi")
            df_list = df.copy()
            final_prices = []
            for _, r in df.iterrows():
                m_tur = r.get('Maden', 'Gümüş')
                m_gram = float(r.get('Gr', 0))
                m_hedef = float(r.get('Hedef Kar', 0))
                ons = ons_altin if m_tur == "Altın" else ons_gumus
                m = ((ons/31.1035) * m_gram * kur) + (m_gram * gr_iscilik * kur) + kargo
                f = (m + m_hedef) / (1 - (komisyon + indirim/100))
                final_prices.append(f"{round(f, 2)} ₺")
            
            df_list['Hesaplanan Fiyat'] = final_prices
            st.dataframe(df_list[['Ürün', 'Maden', 'Gr', 'Hesaplanan Fiyat']], use_container_width=True)

    else:
        st.info("Henüz ürün bulunmuyor.")

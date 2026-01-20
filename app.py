import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import datetime

# --- KÜTÜPHANE KONTROLLERİ ---
try:
    import yfinance as yf
except ImportError:
    st.error("Lütfen requirements.txt dosyasına 'yfinance' ekleyin.")
    st.stop()

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry", layout="wide", page_icon="💎")

# --- YARDIMCI FONKSİYONLAR ---
def safe_float(value):
    try:
        if value is None or str(value).strip() == "": return 0.0
        return float(str(value).replace(',', '.').replace('₺', '').replace('$', '').strip())
    except: return 0.0

def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            if img.mode != "RGB": img = img.convert("RGB")
            img.thumbnail((150, 150)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=60)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except: return ""
    return ""

# --- CANLI PİYASA VERİSİ (SADECE RAKAM) ---
@st.cache_data(ttl=60)
def get_market_data():
    try:
        d = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        a = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        g = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return float(d), float(a), float(g), datetime.datetime.now().strftime("%H:%M")
    except:
        return 43.27, 2650.0, 31.0, "Yenileniyor..."

dolar, altin_ons, gumus_ons, saat = get_market_data()

# --- GOOGLE SHEETS ---
def get_sheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1 
        return pd.DataFrame(sh.get_all_records()), sh
    except: return pd.DataFrame(), None

df, sheet = get_sheet()

# --- SIDEBAR (Grafiksiz Sade Panel) ---
with st.sidebar:
    st.title("💎 CRIPP Jewelry")
    st.caption(f"Son Güncelleme: {saat}")
    
    st.divider()
    st.metric("💵 Dolar/TL", f"{dolar:.2f} ₺")
    st.metric("🥇 Altın Ons", f"${altin_ons:.0f}")
    st.metric("🥈 Gümüş Ons", f"${gumus_ons:.2f}")

    st.divider()
    has_altin = (altin_ons / 31.1035) * dolar
    has_gumus = (gumus_ons / 31.1035) * dolar
    st.success(f"**Has Altın:** {has_altin:.2f} ₺")
    st.info(f"**Has Gümüş:** {has_gumus:.2f} ₺")
    
    st.divider()
    iscilik = st.number_input("İşçilik ($/gr)", value=1.50)
    kargo = st.number_input("Kargo (TL)", value=650.0)
    indirim = st.number_input("Etsy İndirim (%)", value=15.0)
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN ---
st.header("💎 Etsy Akıllı Fiyat Paneli")
t1, t2 = st.tabs(["📊 Ürünler", "➕ Yeni Ekle"])

with t1:
    if not df.empty:
        all_kats = ["Hepsi"] + sorted(list(df['Kategori'].unique()))
        secilen_kat = st.pills("Kategoriler", all_kats, default="Hepsi")
        arama = st.text_input("🔍 Ürün Ara...", "")
        
        mask = df['Ürün'].astype(str).str.lower().str.contains(arama.lower())
        if secilen_kat != "Hepsi": mask = mask & (df['Kategori'] == secilen_kat)
        f_df = df[mask]
        
        if view_mode == "🎨 Kartlar":
            cols = st.columns(4)
            for idx, row in f_df.reset_index().iterrows():
                row_idx = int(row.get('index')) + 2
                
                # Değişkenler
                m_gr = safe_float(row.get('Gr', 0))
                m_kar = safe_float(row.get('Hedef Kar', 0))
                m_kap = safe_float(row.get('KaplamaTL', 0))
                m_laz = safe_float(row.get('LazerTL', 0))
                m_maden = row.get('Maden', 'Gümüş')
                
                # Fiyat Hesaplama
                ons = altin_ons if m_maden == "Altın" else gumus_ons
                maliyet = ((ons/31.1035)*m_gr*dolar) + (m_gr*iscilik*dolar) + m_kap + m_laz + kargo
                fiyat = (maliyet + m_kar) / (1 - (0.17 + indirim/100))
                
                with cols[idx % 4]:
                    img = row.get('GörselData', '')
                    st.markdown(f"""
                    <div style="background:white; padding:10px; border-radius:12px; border:1px solid #eee; text-align:center;">
                        <img src="data:image/jpeg;base64,{img}" style="height:120px; object-fit:contain;">
                        <p style="font-weight:bold; margin:5px 0; font-size:13px; height:35px; overflow:hidden;">{row.get('Ürün')}</p>
                        <h3 style="color:#d63031; margin:0;">{fiyat:,.0f} ₺</h3>
                        <p style="font-size:10px; color:gray;">{m_gr}g | Kap: {m_kap}₺ | Laz: {m_laz}₺</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    b1, b2 = st.columns(2)
                    if b1.button("✏️", key=f"edit_{idx}"):
                        st.session_state[f"form_{idx}"] = not st.session_state.get(f"form_{idx}", False)
                    if b2.button("🗑️", key=f"del_{idx}"):
                        sheet.delete_rows(row_idx)
                        st.rerun()
                    
                    if st.session_state.get(f"form_{idx}"):
                        with st.form(f"f_{idx}"):
                            n_name = st.text_input("Ad", value=row.get('Ürün'))
                            n_gr = st.text_input("Gram", value=str(m_gr))
                            n_kap = st.number_input("Kaplama (TL)", value=float(m_kap))
                            n_laz = st.number_input("Lazer (TL)", value=float(m_laz))
                            n_kar = st.number_input("Hedef Kar", value=float(m_kar))
                            if st.form_submit_button("Güncelle"):
                                # Sütun sıralamasına göre update (1: Ad, 3: Gr, 4: Kar, 7: Kaplama, 8: Lazer)
                                sheet.update_cell(row_idx, 1, n_name)
                                sheet.update_cell(row_idx, 3, n_gr.replace(',','.'))
                                sheet.update_cell(row_idx, 4, n_kar)
                                sheet.update_cell(row_idx, 7, n_kap)
                                sheet.update_cell(row_idx, 8, n_laz)
                                st.session_state[f"form_{idx}"] = False
                                st.rerun()
        else:
            st.dataframe(f_df, use_container_width=True)

with t2:
    with st.form("yeni_urun"):
        c1, c2 = st.columns(2)
        with c1:
            u_ad = st.text_input("Ürün Adı")
            u_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Küpe", "Bileklik"])
            u_maden = st.selectbox("Maden", ["Gümüş", "Altın"])
            u_gr = st.text_input("Gram", value="0.0")
        with c2:
            u_kap = st.number_input("Kaplama Maliyeti (TL)", value=0.0)
            u_laz = st.number_input("Lazer Maliyeti (TL)", value=0.0)
            u_kar = st.number_input("Hedef Kar (TL)", value=2500.0)
            u_img = st.file_uploader("Görsel", type=['jpg','png'])
        
        if st.form_submit_button("Kaydet"):
            img_str = image_to_base64(u_img)
            # Sıralama: Ürün, Maden, Gr, Kar, Görsel, Kategori, Kaplama, Lazer, Zincir
            sheet.append_row([u_ad, u_maden, u_gr.replace(',','.'), u_kar, img_str, u_kat, u_kap, u_laz, 0])
            st.success("Başarıyla eklendi!")
            st.rerun()

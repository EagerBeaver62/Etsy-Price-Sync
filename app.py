import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import datetime
try:
    import plotly.graph_objects as go
except ImportError:
    st.error("Lütfen GitHub'daki 'requirements.txt' dosyanıza 'plotly' ekleyin.")

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry", layout="wide", page_icon="💎")

# --- GÜVENLİ SAYI DÖNÜŞTÜRÜCÜ ---
def safe_float(value):
    try:
        if value is None or value == "": return 0.0
        return float(str(value).replace(',', '.').strip())
    except: return 0.0

# --- PİYASA VERİLERİ (SOL PANEL İÇİN) ---
@st.cache_data(ttl=300)
def get_sidebar_chart(ticker, color):
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if df.empty: return None
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color=color, width=2)))
        fig.update_layout(
            height=120, margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    except: return None

@st.cache_data(ttl=60)
def piyasa_canli():
    try:
        d_val = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        a_val = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        g_val = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return float(d_val), float(a_val), float(g_val), datetime.datetime.now().strftime("%H:%M:%S")
    except: return 43.27, 2650.0, 31.0, "Yükleniyor..."

dolar_kuru, ons_altin, ons_gumus, son_guncelleme = piyasa_canli()

# --- GOOGLE SHEETS ---
def get_gsheet_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1
    except: return None

sheet = get_gsheet_client()

# --- SIDEBAR (GRAFİKLER BURAYA TAŞINDI) ---
with st.sidebar:
    st.title("💎 CRIPP Jewelry")
    st.success(f"🕒 {son_guncelleme}")
    
    st.divider()
    # Dolar
    st.metric("💵 Dolar/TL", f"{dolar_kuru:.2f} ₺")
    st.plotly_chart(get_sidebar_chart("USDTRY=X", "#27ae60"), use_container_width=True, config={'displayModeBar': False})
    
    # Altın
    st.metric("🥇 Altın Ons", f"${ons_altin:.0f}")
    st.plotly_chart(get_sidebar_chart("GC=F", "#f1c40f"), use_container_width=True, config={'displayModeBar': False})
    
    st.divider()
    gr_altin_tl = (ons_altin / 31.1035) * dolar_kuru
    st.info(f"⚖️ **Has Altın:** {gr_altin_tl:.2f} ₺")
    
    st.divider()
    gr_iscilik = st.number_input("🛠️ İşçilik ($/gr)", value=1.50)
    kargo = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim = st.number_input("🏷️ İndirim (%)", value=15.0)
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN (TABLAR GERİ GELDİ) ---
st.title("💎 Etsy Akıllı Fiyat Paneli")

tab1, tab2 = st.tabs(["📊 Ürün Yönetimi", "➕ Yeni Ürün Ekle"])

if sheet:
    try:
        df = pd.DataFrame(sheet.get_all_records())
    except: df = pd.DataFrame()

    with tab1:
        if not df.empty:
            # Kategori Filtresi (Pills)
            mevcut_kats = ["Hepsi"] + sorted(list(df['Kategori'].unique()))
            sel_kat = st.pills("Kategoriler", mevcut_kats, default="Hepsi")
            
            search = st.text_input("🔍 İsimle ara...", "").lower()
            mask = df['Ürün'].astype(str).str.lower().str.contains(search)
            if sel_kat != "Hepsi": mask = mask & (df['Kategori'] == sel_kat)
            
            f_df = df[mask]
            
            if view_mode == "🎨 Kartlar":
                cols = st.columns(4)
                for idx, row in f_df.reset_index().iterrows():
                    m_gram = safe_float(row.get('Gr', 0))
                    m_hedef = safe_float(row.get('Hedef Kar', 0))
                    ons = ons_altin if row.get('Maden') == "Altın" else ons_gumus
                    
                    maliyet = ((ons/31.1035) * m_gram * dolar_kuru) + (m_gram * gr_iscilik * dolar_kuru) + \
                              safe_float(row.get('KaplamaTL',0)) + safe_float(row.get('LazerTL',0)) + kargo
                    fiyat = (maliyet + m_hedef) / (1 - (0.17 + indirim/100))

                    with cols[idx % 4]:
                        st.markdown(f"""
                        <div style="background-color:white; padding:10px; border-radius:15px; border:1px solid #eee; text-align:center;">
                            <img src="data:image/jpeg;base64,{row.get('GörselData','')}" style="width:100%; height:130px; object-fit:contain;">
                            <p style="font-weight:bold; font-size:14px; margin:5px 0;">{row.get('Ürün','Adsız')}</p>
                            <h2 style="color:#d63031; margin:0;">{round(fiyat, 2)} ₺</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        st.divider()
            else: st.dataframe(f_df, use_container_width=True)

    with tab2:
        st.write("Buradan yeni ürün ekleyebilirsiniz (Form kodlarınızı buraya ekleyin).")

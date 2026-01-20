import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import datetime

# Plotly yüklü değilse bile uygulamanın çökmemesi için koruma
try:
    import plotly.graph_objects as go
except ImportError:
    go = None

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry", layout="wide", page_icon="💎")

# --- GÜVENLİ VERİ DÖNÜŞTÜRÜCÜ ---
def safe_float(value):
    try:
        if value is None or value == "": return 0.0
        return float(str(value).replace(',', '.').strip())
    except: return 0.0

# --- KÜÇÜK SIDEBAR GRAFİĞİ ---
def draw_mini_chart(ticker, color):
    if go is None: return None
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if df.empty: return None
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color=color, width=1.5)))
        fig.update_layout(
            height=60, margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        return fig
    except: return None

# --- CANLI PİYASA VERİSİ ---
@st.cache_data(ttl=60)
def get_live_market():
    try:
        d = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        a = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        g = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return float(d), float(a), float(g), datetime.datetime.now().strftime("%H:%M:%S")
    except:
        return 43.26, 2650.0, 31.0, "Yenileniyor..."

dolar_kuru, ons_altin, ons_gumus, son_saat = get_live_market()

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_sheet_data():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1
        return pd.DataFrame(sheet.get_all_records()), sheet
    except:
        return pd.DataFrame(), None

df, sheet_client = get_sheet_data()

# --- SIDEBAR (SOL PANEL) ---
with st.sidebar:
    st.title("💎 CRIPP Jewelry")
    st.caption(f"Son Güncelleme: {son_saat}")
    
    st.divider()
    # Dolar ve Küçük Grafik
    st.metric("💵 Dolar/TL", f"{dolar_kuru:.2f} ₺")
    chart_dolar = draw_mini_chart("USDTRY=X", "#2ecc71")
    if chart_dolar: st.plotly_chart(chart_dolar, use_container_width=True, config={'displayModeBar': False})
    
    # Altın ve Küçük Grafik
    st.metric("🥇 Altın Ons", f"${ons_altin:.0f}")
    chart_altin = draw_mini_chart("GC=F", "#f1c40f")
    if chart_altin: st.plotly_chart(chart_altin, use_container_width=True, config={'displayModeBar': False})
    
    st.divider()
    gr_altin_tl = (ons_altin / 31.1035) * dolar_kuru
    st.info(f"⚖️ **Has Altın:** {gr_altin_tl:.2f} ₺")
    
    st.divider()
    gr_iscilik = st.number_input("🛠️ İşçilik ($/gr)", value=1.50)
    kargo = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim = st.number_input("🏷️ İndirim (%)", value=15.0)
    view_mode = st.radio("Görünüm Seçimi", ["🎨 Kartlar", "📋 Liste"])

# --- ANA PANEL ---
st.header("💎 Etsy Akıllı Fiyat & Stok Paneli")

tab1, tab2 = st.tabs(["📊 Ürün Yönetimi", "➕ Yeni Ürün Ekle"])

with tab1:
    if not df.empty:
        # Kategori Filtreleri (Modern Stil)
        mevcut_kats = ["Hepsi"] + sorted(list(df['Kategori'].unique()))
        sel_kat = st.pills("Kategoriler", mevcut_kats, default="Hepsi")
        
        search = st.text_input("🔍 İsimle ara...", "").lower()
        
        mask = df['Ürün'].astype(str).str.lower().str.contains(search)
        if sel_kat != "Hepsi":
            mask = mask & (df['Kategori'] == sel_kat)
        
        filtered_df = df[mask]
        
        if view_mode == "🎨 Kartlar":
            cols = st.columns(4)
            for idx, row in filtered_df.reset_index().iterrows():
                # Hesaplama
                m_gram = safe_float(row.get('Gr', 0))
                m_hedef = safe_float(row.get('Hedef Kar', 0))
                ons = ons_altin if row.get('Maden') == "Altın" else ons_gumus
                
                maliyet = ((ons/31.1035) * m_gram * dolar_kuru) + (m_gram * gr_iscilik * dolar_kuru) + \
                          safe_float(row.get('KaplamaTL', 0)) + safe_float(row.get('LazerTL', 0)) + kargo
                fiyat = (maliyet + m_hedef) / (1 - (0.17 + indirim/100))
                
                with cols[idx % 4]:
                    st.markdown(f"""
                    <div style="background-color:white; padding:15px; border-radius:15px; border:1px solid #eee; text-align:center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                        <img src="data:image/jpeg;base64,{row.get('GörselData','')}" style="width:100%; height:150px; object-fit:contain; border-radius:10px;">
                        <p style="font-weight:bold; margin-top:10px; min-height:40px;">{row.get('Ürün','Adsız')}</p>
                        <h2 style="color:#d63031; margin:0;">{round(fiyat, 2)} ₺</h2>
                        <p style="font-size:11px; color:gray;">Gr: {m_gram} | Kar: {m_hedef}₺</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.write("") # Boşluk
        else:
            st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("Veri bulunamadı.")

with tab2:
    st.info("Yeni ürün ekleme formu burada yer alacak.")

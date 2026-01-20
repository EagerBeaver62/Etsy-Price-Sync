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
    st.error("Lütfen GitHub'daki 'requirements.txt' dosyanıza 'plotly' ekleyip kaydedin.")

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry Dashboard", layout="wide", page_icon="💎")

# --- GÜVENLİ SAYI DÖNÜŞTÜRÜCÜ ---
def safe_float(value):
    try:
        if value is None or value == "": return 0.0
        return float(str(value).replace(',', '.').strip())
    except: return 0.0

# --- PİYASA VERİLERİ ---
@st.cache_data(ttl=300)
def get_clean_data(ticker):
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        return data[['Close']]
    except: return pd.DataFrame()

def draw_simple_line_chart(df, title, color):
    if df.empty: return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Close'], 
        mode='lines', 
        line=dict(color=color, width=3),
        hovertemplate='%{y:.2f}' # Sadece değer görünür
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor='rgba(0,0,0,0)', # Arka plan temiz
        xaxis=dict(showgrid=False, title="Tarih"),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Fiyat")
    )
    return fig

@st.cache_data(ttl=60)
def piyasa_canli():
    try:
        d_val = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        a_val = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        g_val = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return float(d_val), float(a_val), float(g_val), datetime.datetime.now().strftime("%H:%M:%S")
    except: return 43.27, 2650.0, 31.0, "Yükleniyor..."

dolar_kuru, ons_altin, ons_gumus, son_guncelleme = piyasa_canli()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 CRIPP Jewelry")
    st.divider()
    st.success(f"🕒 **Son Kontrol:** {son_guncelleme}")
    
    st.markdown("### 📈 Anlık Kurlar")
    st.metric("💵 Dolar/TL", f"{dolar_kuru:.2f} ₺")
    st.metric("🥇 Altın Ons", f"${ons_altin:.0f}")
    st.metric("🥈 Gümüş Ons", f"${ons_gumus:.2f}")
    
    st.divider()
    gr_altin_tl = (ons_altin / 31.1035) * dolar_kuru
    gr_gumus_tl = (ons_gumus / 31.1035) * dolar_kuru
    st.info(f"**Has Altın:** {gr_altin_tl:.2f} ₺\n\n**Has Gümüş:** {gr_gumus_tl:.2f} ₺")
    
    st.divider()
    gr_iscilik = st.number_input("🛠️ İşçilik ($/gr)", value=1.50)
    kargo = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim = st.number_input("🏷️ İndirim (%)", value=15.0)
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN ---
st.title("💎 Fiyat Takip ve Yönetim")

# Sadeleştirilmiş Grafik Alanı
st.markdown("### 📊 30 Günlük Değişim Trendi")
g_col1, g_col2, g_col3 = st.columns(3)

with g_col1:
    f1 = draw_simple_line_chart(get_clean_data("USDTRY=X"), "Dolar/TL", "#27ae60")
    if f1: st.plotly_chart(f1, use_container_width=True)

with g_col2:
    f2 = draw_simple_line_chart(get_clean_data("GC=F"), "Altın Ons ($)", "#f1c40f")
    if f2: st.plotly_chart(f2, use_container_width=True)

with g_col3:
    f3 = draw_simple_line_chart(get_clean_data("SI=F"), "Gümüş Ons ($)", "#7f8c8d")
    if f3: st.plotly_chart(f3, use_container_width=True)

st.divider()

# Ürün Yönetimi ve Tab yapısı burada devam eder...
# (Daha önce çalışan ürün listeleme kodlarını bu satırın altına ekleyebilirsin)

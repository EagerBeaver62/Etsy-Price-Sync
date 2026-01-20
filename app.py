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
    st.error("Lütfen requirements.txt dosyanıza 'plotly' ekleyin.")

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry Dashboard", layout="wide", page_icon="💎")

# --- GÜVENLİ SAYI DÖNÜŞTÜRÜCÜ ---
def safe_float(value):
    try:
        if value is None or value == "": return 0.0
        return float(str(value).replace(',', '.').strip())
    except: return 0.0

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
            img.thumbnail((150, 150)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=60)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except: return ""
    return ""

# --- PİYASA VERİLERİ VE GRAFİKLER ---
@st.cache_data(ttl=300)
def get_historical_data(ticker):
    try: return yf.download(ticker, period="1mo", interval="1d", progress=False)
    except: return pd.DataFrame()

def draw_chart(df, title, color):
    if df.empty: return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', line=dict(color=color)))
    fig.update_layout(title=title, height=200, margin=dict(l=0,r=0,t=30,b=0))
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
sheet = get_gsheet_client()

# --- SIDEBAR ---
with st.sidebar:
    try: st.image("Adsız tasarım (22).png", use_container_width=True)
    except: st.title("💎 CRIPP Jewelry")
    
    st.divider()
    st.markdown(f"**🕒 Son Kontrol:** `{son_guncelleme}`")
    st.markdown("### 📈 Canlı Piyasalar")
    c1, c2 = st.columns(2)
    c1.metric("💵 USD/TRY", f"{dolar_kuru:.2f} ₺")
    c2.metric("🥈 Gümüş Ons", f"${ons_gumus:.2f}")
    st.metric("🥇 Altın Ons", f"${ons_altin:.0f}")
    
    st.divider()
    gr_altin_tl = (ons_altin / 31.1035) * dolar_kuru
    gr_gumus_tl = (ons_gumus / 31.1035) * dolar_kuru
    st.info(f"⚖️ **Has Gümüş:** {gr_gumus_tl:.2f} ₺\n\n⚖️ **Has Altın:** {gr_altin_tl:.2f} ₺")
    
    st.divider()
    gr_iscilik = st.number_input("🛠️ İşçilik ($/gr)", value=1.50)
    kargo = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim = st.number_input("🏷️ Etsy İndirim (%)", value=15.0)
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Fiyat & Stok Paneli")

with st.expander("📊 1 Aylık Piyasa Değişim Grafikleri", expanded=False):
    g1, g2, g3 = st.columns(3)
    with g1: 
        fig = draw_chart(get_historical_data("USDTRY=X"), "Dolar/TL", "#2ecc71")
        if fig: st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = draw_chart(get_historical_data("GC=F"), "Altın Ons ($)", "#f1c40f")
        if fig: st.plotly_chart(fig, use_container_width=True)
    with g3:
        fig = draw_chart(get_historical_data("SI=F"), "Gümüş Ons ($)", "#95a5a6")
        if fig: st.plotly_chart(fig, use_container_width=True)

tab1, tab2 = st.tabs(["📊 Ürün Yönetimi", "➕ Yeni Ürün Ekle"])

if sheet:
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
    except: df = pd.DataFrame()

    with tab1:
        if not df.empty:
            # Kategori Filtresi
            mevcut_kats = ["Hepsi"] + sorted(list(df['Kategori'].unique()))
            if 'sel_kat' not in st.session_state: st.session_state.sel_kat = "Hepsi"
            
            k_cols = st.columns(len(mevcut_kats))
            for i, kat in enumerate(mevcut_kats):
                if k_cols[i].button(kat, key=f"k_{kat}", use_container_width=True, type="primary" if st.session_state.sel_kat == kat else "secondary"):
                    st.session_state.sel_kat = kat
                    st.rerun()

            search = st.text_input("🔍 Ara...", "").lower()
            mask = df['Ürün'].astype(str).str.lower().str.contains(search)
            if st.session_state.sel_kat != "Hepsi": mask = mask & (df['Kategori'] == st.session_state.sel_kat)
            
            f_df = df[mask]

            if view_mode == "🎨 Kartlar":
                cols = st.columns(4)
                for idx, row in f_df.reset_index().iterrows():
                    actual_idx = int(row['index']) + 2
                    m_gram = safe_float(row.get('Gr', 0))
                    m_hedef = safe_float(row.get('Hedef Kar', 0))
                    m_maden = row.get('Maden', 'Gümüş')
                    
                    ons = ons_altin if m_maden == "Altın" else ons_gumus
                    maliyet = ((ons/31.1035) * m_gram * dolar_kuru) + (m_gram * gr_iscilik * dolar_kuru) + \
                              safe_float(row.get('KaplamaTL',0)) + safe_float(row.get('LazerTL',0)) + \
                              safe_float(row.get('ZincirTL',0)) + kargo
                    fiyat = (maliyet + m_hedef) / (1 - (0.17 + indirim/100))

                    with cols[idx % 4]:
                        st.markdown(f"""
                        <div style="background-color:white; padding:12px; border-radius:15px; border:1px solid #eee; text-align:center; margin-bottom:10px;">
                            <img src="data:image/jpeg;base64,{row.get('GörselData','')}" style="width:100%; height:140px; object-fit:contain; border-radius:8px;">
                            <p style="font-weight:bold; margin-top:8px; font-size:14px; height:40px; overflow:hidden;">{row.get('Ürün','Adsız')}</p>
                            <h2 style="color:#d63031; margin:0;">{round(fiyat, 2)} ₺</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        b1, b2 = st.columns(2)
                        if b1.button("✏️", key=f"e_{actual_idx}"): st.session_state[f"edit_{actual_idx}"] = True
                        if b2.button("🗑️", key=f"d_{actual_idx}"):
                            sheet.delete_rows(actual_idx)
                            st.rerun()

                        if st.session_state.get(f"edit_{actual_idx}", False):
                            with st.form(key=f"f_{actual_idx}"):
                                e_name = st.text_input("İsim", value=row.get('Ürün',''))
                                e_gr = st.text_input("Gr", value=str(m_gram))
                                e_kar = st.number_input("Kar", value=m_hedef)
                                if st.form_submit_button("Güncelle"):
                                    sheet.update_cell(actual_idx, 1, e_name)
                                    sheet.update_cell(actual_idx, 3, e_gr.replace(',','.'))
                                    sheet.update_cell(actual_idx, 4, e_kar)
                                    st.session_state[f"edit_{actual_idx}"] = False
                                    st.rerun()
            else: st.dataframe(f_df, use_container_width=True)

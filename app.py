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

# Plotly kontrolü (Grafikler için şart)
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

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

# --- GRAFİK ÇİZME FONKSİYONU ---
def create_sparkline(ticker, color):
    if not PLOTLY_AVAILABLE: return None
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if data.empty: return None
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data.index, 
            y=data['Close'], 
            mode='lines', 
            line=dict(color=color, width=2),
            fill='tozeroy' # Altını hafif doldurur, daha şık durur
        ))
        fig.update_layout(
            height=50, 
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False, fixedrange=True),
            yaxis=dict(visible=False, fixedrange=True),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            hovermode=False 
        )
        return fig
    except: return None

# --- VERİ ÇEKME ---
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
        # BURAYA KENDİ SHEET ID'NİZİ YAZIN
        sh = client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1 
        return pd.DataFrame(sh.get_all_records()), sh
    except: return pd.DataFrame(), None

df, sheet = get_sheet()

# --- SIDEBAR (Grafikli Sol Panel) ---
with st.sidebar:
    st.image("Adsız tasarım (22).png") if 'Adsız tasarım (22).png' in [f.name for f in  st.runtime.get_instance()._session_state._new_session_state] else st.title("💎 CRIPP")
    st.caption(f"Son Güncelleme: {saat}")
    
    if not PLOTLY_AVAILABLE:
        st.error("Grafik için requirements.txt'ye 'plotly' ekle!")

    st.divider()
    
    # DOLAR
    c1, c2 = st.columns([1,2])
    c1.metric("USD", f"{dolar:.2f}")
    fig_d = create_sparkline("USDTRY=X", "#2ecc71")
    if fig_d: st.plotly_chart(fig_d, use_container_width=True, config={'displayModeBar': False})
    
    # ALTIN
    st.metric("Altın Ons", f"${altin_ons:.0f}")
    fig_a = create_sparkline("GC=F", "#f1c40f")
    if fig_a: st.plotly_chart(fig_a, use_container_width=True, config={'displayModeBar': False})

    # GÜMÜŞ
    st.metric("Gümüş Ons", f"${gumus_ons:.2f}")
    fig_g = create_sparkline("SI=F", "#95a5a6")
    if fig_g: st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})

    st.divider()
    
    # GRAM HESAPLARI
    has_altin = (altin_ons / 31.1035) * dolar
    has_gumus = (gumus_ons / 31.1035) * dolar
    
    st.info(f"**Has Altın:** {has_altin:.2f} ₺")
    st.info(f"**Has Gümüş:** {has_gumus:.2f} ₺")
    
    st.divider()
    # MALİYET GİRDİLERİ
    iscilik = st.number_input("İşçilik ($/gr)", value=1.50)
    kargo = st.number_input("Kargo (TL)", value=650.0)
    indirim = st.number_input("Etsy İndirim (%)", value=15.0)
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Fiyat Paneli")

t1, t2 = st.tabs(["📊 Ürünler", "➕ Ekle"])

with t1:
    if not df.empty:
        # Filtreler
        all_kats = ["Hepsi"] + sorted(list(df['Kategori'].unique())) if 'Kategori' in df.columns else ["Hepsi"]
        secilen_kat = st.pills("Kategori", all_kats, default="Hepsi")
        arama = st.text_input("Ara...", "")
        
        # Filtreleme
        mask = df['Ürün'].astype(str).str.lower().str.contains(arama.lower())
        if secilen_kat != "Hepsi": mask = mask & (df['Kategori'] == secilen_kat)
        f_df = df[mask]
        
        if view_mode == "🎨 Kartlar":
            cols = st.columns(4)
            for idx, row in f_df.reset_index().iterrows():
                actual_row_num = int(row.get('index', -1)) + 2 # Sheet satır numarası
                
                # --- HESAPLAMA ---
                m_gram = safe_float(row.get('Gr', 0))
                m_kar = safe_float(row.get('Hedef Kar', 0))
                m_kap = safe_float(row.get('KaplamaTL', 0))
                m_laz = safe_float(row.get('LazerTL', 0))
                m_maden = row.get('Maden', 'Gümüş')
                
                ons_base = altin_ons if m_maden == "Altın" else gumus_ons
                maliyet = ((ons_base/31.1035)*m_gram*dolar) + (m_gram*iscilik*dolar) + m_kap + m_laz + kargo
                satis = (maliyet + m_kar) / (1 - (0.17 + indirim/100))
                
                with cols[idx % 4]:
                    # KART GÖRÜNÜMÜ
                    img_data = row.get('GörselData', '')
                    img_src = f"data:image/jpeg;base64,{img_data}" if img_data else ""
                    
                    st.markdown(f"""
                    <div style="background:white; padding:10px; border-radius:12px; border:1px solid #eee; text-align:center; box-shadow:0 2px 4px #eee;">
                        <img src="{img_src}" style="height:120px; object-fit:contain; border-radius:8px;">
                        <div style="font-weight:bold; margin:5px 0; height:40px; overflow:hidden;">{row.get('Ürün','?')}</div>
                        <div style="color:#e74c3c; font-size:1.2em; font-weight:bold;">{satis:,.0f} ₺</div>
                        <div style="font-size:0.8em; color:grey;">{m_gram}gr | Kar: {m_kar}₺</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # BUTONLAR (DÜZENLE & SİL)
                    b1, b2 = st.columns(2)
                    if b1.button("✏️", key=f"e_{idx}"):
                        st.session_state[f"edit_mode_{idx}"] = not st.session_state.get(f"edit_mode_{idx}", False)
                    
                    if b2.button("🗑️", key=f"d_{idx}"):
                        sheet.delete_rows(actual_row_num)
                        st.rerun()
                    
                    # DÜZENLEME FORMU (Açılır/Kapanır)
                    if st.session_state.get(f"edit_mode_{idx}", False):
                        with st.container(border=True):
                            new_name = st.text_input("Ad", value=row.get('Ürün'), key=f"i1_{idx}")
                            new_gr = st.text_input("Gram", value=str(m_gram), key=f"i2_{idx}")
                            new_kar = st.number_input("Hedef Kar", value=float(m_kar), key=f"i3_{idx}")
                            
                            if st.button("Kaydet", key=f"s_{idx}", type="primary"):
                                # Hücreleri güncelle (1: Ürün, 3: Gr, 4: Kar - Sütun sırasına göre)
                                sheet.update_cell(actual_row_num, 1, new_name)
                                sheet.update_cell(actual_row_num, 3, new_gr.replace(',','.'))
                                sheet.update_cell(actual_row_num, 4, new_kar)
                                st.session_state[f"edit_mode_{idx}"] = False
                                st.rerun()

        else:
            st.dataframe(f_df, use_container_width=True)
    else:
        st.info("Veri yok.")

with t2:
    with st.form("ekle"):
        c1, c2 = st.columns(2)

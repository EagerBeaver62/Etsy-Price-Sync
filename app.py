import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import datetime

# --- KÜTÜPHANE KONTROLÜ (HATA VERMEMESİ İÇİN) ---
try:
    import yfinance as yf
except ImportError:
    st.error("Lütfen 'requirements.txt' dosyasına 'yfinance' ekleyin.")
    st.stop()

try:
    import plotly.graph_objects as go
    PLOTLY_VAR = True
except ImportError:
    PLOTLY_VAR = False # Plotly yoksa grafik çizme, ama uygulamayı da kapatma.

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry", layout="wide", page_icon="💎")

# --- GÜVENLİ SAYI DÖNÜŞTÜRÜCÜ (SİSTEMİN ÇÖKMESİNİ ENGELLER) ---
def safe_float(value):
    try:
        if value is None or str(value).strip() == "": return 0.0
        # Virgülleri noktaya çevir ve boşlukları temizle
        clean_val = str(value).replace(',', '.').replace('₺', '').replace('$', '').strip()
        return float(clean_val)
    except:
        return 0.0

# --- GRAFİK ÇİZME (HATA KORUMALI) ---
def draw_mini_chart(ticker, color):
    if not PLOTLY_VAR: return None # Kütüphane yoksa hiç deneme
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if df.empty: return None
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color=color, width=2)))
        fig.update_layout(
            height=50, margin=dict(l=0, r=0, t=0, b=0),
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
        # Veri çekilemezse varsayılan değerler dönsün, sistem durmasın
        return 43.26, 2650.0, 31.0, "Bağlantı Bekleniyor..."

dolar_kuru, ons_altin, ons_gumus, son_saat = get_live_market()

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_sheet_data():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Lütfen buradaki dosya ID'nizin veya isminizin doğru olduğundan emin olun
        sheet = client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1
        return pd.DataFrame(sheet.get_all_records()), sheet
    except Exception as e:
        return pd.DataFrame(), None

df, sheet_client = get_sheet_data()

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

# --- SIDEBAR (SOL PANEL) ---
with st.sidebar:
    st.title("💎 CRIPP Jewelry")
    st.caption(f"⏱️ {son_saat}")
    
    if not PLOTLY_VAR:
        st.warning("Grafikler için 'requirements.txt' dosyasına 'plotly' ekleyin.")

    st.divider()
    
    # 1. DOLAR
    st.metric("💵 Dolar/TL", f"{dolar_kuru:.2f} ₺")
    chart_dolar = draw_mini_chart("USDTRY=X", "#2ecc71")
    if chart_dolar: st.plotly_chart(chart_dolar, use_container_width=True, config={'displayModeBar': False})
    
    # 2. ALTIN
    st.metric("🥇 Altın Ons", f"${ons_altin:.0f}")
    chart_altin = draw_mini_chart("GC=F", "#f1c40f")
    if chart_altin: st.plotly_chart(chart_altin, use_container_width=True, config={'displayModeBar': False})

    # 3. GÜMÜŞ (Bu kısım "Gümüş Yok" dediğiniz yerdi, şimdi burada)
    st.metric("🥈 Gümüş Ons", f"${ons_gumus:.2f}")
    chart_gumus = draw_mini_chart("SI=F", "#95a5a6")
    if chart_gumus: st.plotly_chart(chart_gumus, use_container_width=True, config={'displayModeBar': False})
    
    st.divider()
    # Gram Hesapları
    gr_altin_tl = (ons_altin / 31.1035) * dolar_kuru
    gr_gumus_tl = (ons_gumus / 31.1035) * dolar_kuru
    
    st.info(f"""
    ⚖️ **Gram Fiyatları**
    
    **Altın:** {gr_altin_tl:.2f} ₺
    **Gümüş:** {gr_gumus_tl:.2f} ₺
    """)
    
    st.divider()
    # Ayarlar
    gr_iscilik = st.number_input("🛠️ İşçilik ($/gr)", value=1.50)
    kargo = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim = st.number_input("🏷️ İndirim (%)", value=15.0)
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA PANEL ---
st.header("💎 Etsy Akıllı Fiyat & Stok Paneli")

tab1, tab2 = st.tabs(["📊 Ürün Yönetimi", "➕ Yeni Ürün Ekle"])

# --- TAB 1: LİSTELEME ---
with tab1:
    if not df.empty:
        # Filtreler
        mevcut_kats = ["Hepsi"] + sorted(list(df['Kategori'].unique())) if 'Kategori' in df.columns else ["Hepsi"]
        
        # st.pills bazı versiyonlarda hata verebilir, güvenli olan selectbox kullanalım şimdilik
        try:
            sel_kat = st.pills("Kategoriler", mevcut_kats, default="Hepsi")
        except:
            sel_kat = st.selectbox("Kategori Seç", mevcut_kats)
            
        search = st.text_input("🔍 İsimle ara...", "").lower()
        
        # Filtreleme Mantığı
        mask = df['Ürün'].astype(str).str.lower().str.contains(search)
        if sel_kat != "Hepsi":
            mask = mask & (df['Kategori'] == sel_kat)
        
        filtered_df = df[mask]
        
        # GÖRÜNÜM: KARTLAR
        if view_mode == "🎨 Kartlar":
            cols = st.columns(4)
            for idx, row in filtered_df.reset_index().iterrows():
                # --- HESAPLAMA (GÜVENLİ) ---
                # safe_float ile veriyi koruyoruz
                m_gram = safe_float(row.get('Gr', 0))
                m_hedef = safe_float(row.get('Hedef Kar', 0))
                
                # Ek Maliyetler (Varsa çek, yoksa 0)
                m_kap = safe_float(row.get('KaplamaTL', 0))
                m_laz = safe_float(row.get('LazerTL', 0))
                m_zin = safe_float(row.get('ZincirTL', 0)) # Eğer zincir sütunu eklediyseniz
                
                # Maden Kuru Seçimi
                maden_tur = row.get('Maden', 'Gümüş')
                ons_fiyat = ons_altin if maden_tur == "Altın" else ons_gumus
                
                # Formül: (Maden + İşçilik + Ekler + Kargo)
                maden_tl = (ons_fiyat / 31.1035) * m_gram * dolar_kuru
                iscilik_tl = m_gram * gr_iscilik * dolar_kuru
                ek_maliyetler = m_kap + m_laz + m_zin + kargo
                
                toplam_maliyet = maden_tl + iscilik_tl + ek_maliyetler
                
                # Satış Fiyatı
                komisyon_orani = 0.17 + (indirim / 100)
                satis_fiyati = (toplam_maliyet + m_hedef) / (1 - komisyon_orani)
                
                # Kart Tasarımı
                with cols[idx % 4]:
                    img_src = row.get('GörselData', '')
                    img_html = f'<img src="data:image/jpeg;base64,{img_src}" style="width:100%; height:150px; object-fit:contain; border-radius:10px;">' if img_src else '<div style="height:150px; background:#f0f0f0; border-radius:10px; display:flex; align-items:center; justify-content:center;">Resim Yok</div>'
                    
                    st.markdown(f"""
                    <div style="background-color:white; padding:15px; border-radius:15px; border:1px solid #eee; text-align:center; margin-bottom:20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                        {img_html}
                        <p style="font-weight:bold; margin-top:10px; font-size:14px; height:40px; overflow:hidden;">{row.get('Ürün', 'İsimsiz')}</p>
                        <h3 style="color:#d63031; margin:5px 0;">{satis_fiyati:,.2f} ₺</h3>
                        <div style="font-size:11px; color:gray; display:flex; justify-content:space-between;">
                            <span>{m_gram} Gr</span>
                            <span>Kâr: {m_hedef}₺</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Düzenle / Sil Butonları (İsteğe bağlı aktif edilebilir)
                    b1, b2 = st.columns(2)
                    if b2.button("🗑️ Sil", key=f"del_{row['index']}"):
                        sheet_client.delete_rows(int(row['index']) + 2)
                        st.rerun()

        # GÖRÜNÜM: LİSTE
        else:
            st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("Tablo boş veya yüklenemedi. 'Yeni Ürün Ekle' sekmesinden ürün ekleyin.")

# --- TAB 2: EKLEME ---
with tab2:
    with st.form("yeni_urun"):
        c1, c2 = st.columns(2)
        with c1:
            n_ad = st.text_input("Ürün Adı")
            n_kat = st.selectbox("Kategori", ["Kolye", "Yüzük", "Küpe", "Bileklik", "Diğer"])
            n_maden = st.selectbox("Maden", ["Gümüş", "Altın"])
            n_gr = st.text_input("Gramaj", value="0.0")
        with c2:
            n_kap = st.number_input("Kaplama (TL)", value=0.0)
            n_laz = st.number_input("Lazer (TL)", value=0.0)
            n_zin = st.number_input("Zincir (TL)", value=0.0)
            n_kar = st.number_input("Hedef Kar (TL)", value=2500.0)
            n_img = st.file_uploader("Görsel", type=["jpg","png"])
        
        if st.form_submit_button("Kaydet"):
            if sheet_client:
                img_str = image_to_base64(n_img)
                # Google Sheets'e güvenli kayıt
                sheet_client.append_row([
                    n_ad, n_maden, n_gr.replace(',','.'), n_kar, img_str, n_kat, n_kap, n_laz, n_zin
                ])
                st.success("Ürün eklendi!")
                st.rerun()

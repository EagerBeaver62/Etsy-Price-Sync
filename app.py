import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import datetime
import requests
import json
import time

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

# --- HAREM ALTIN VERİ ÇEKME ---
@st.cache_data(ttl=60)
def get_harem_data():
    url = "https://www.haremaltin.com/dashboard/ajax/pol"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.haremaltin.com/"
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            data_dict = data.get('data', {})
            
            gumus_usd_raw = data_dict.get('GUMUSUSD', {}).get('satis', 0)
            altin_tl_raw = data_dict.get('ALTIN', {}).get('satis', 0)
            dolar_tl_raw = data_dict.get('USDTRY', {}).get('satis', 0)
            ons_raw = data_dict.get('ALTINONS', {}).get('satis', 0)

            return {
                'gumus_usd': safe_float(gumus_usd_raw),
                'altin_tl': safe_float(altin_tl_raw),
                'dolar_tl': safe_float(dolar_tl_raw),
                'altin_ons': safe_float(ons_raw),
                'status': 'success',
                'time': datetime.datetime.now().strftime("%H:%M")
            }
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    
    return {'status': 'error', 'msg': 'Veri alınamadı'}

market_data = get_harem_data()

# Yedek Veri
if market_data['status'] == 'error':
    try:
        d = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        a = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        market_data = {
            'gumus_usd': 0.0,
            'altin_tl': (a/31.1035)*d,
            'dolar_tl': d,
            'altin_ons': a,
            'status': 'backup',
            'time': datetime.datetime.now().strftime("%H:%M")
        }
    except:
        market_data = {'gumus_usd':0, 'altin_tl':0, 'dolar_tl':0, 'altin_ons':0, 'status':'fail', 'time':'--:--'}

dolar_kuru = market_data['dolar_tl']
altin_ons = market_data['altin_ons']
saat = market_data['time']

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

# --- SIDEBAR (SOL PANEL) ---
with st.sidebar:
    st.title("💎 CRIPP Jewelry")
    st.caption(f"Veri: {market_data['status'].upper()} | {saat}")
    st.divider()
    
    st.metric("💵 Dolar/TL", f"{dolar_kuru:.2f} ₺")
    
    # --- 1. GÜMÜŞ AYARLARI ---
    st.subheader("🥈 Gümüş Ayarları")
    raw_gumus = market_data['gumus_usd']
    if raw_gumus > 500: auto_gumus_gram_usd = raw_gumus / 1000
    else: auto_gumus_gram_usd = raw_gumus

    mode_gumus = st.radio("Gümüş Kaynağı", ["Otomatik", "Manuel"], horizontal=True, key="gumus_radio")
    
    if mode_gumus == "Otomatik" and market_data['status'] == 'success':
        gumus_baz_usd = auto_gumus_gram_usd
        st.info(f"Harem Gümüş: ${gumus_baz_usd:.3f}")
    else:
        varsayilan_g = 3.15 if auto_gumus_gram_usd == 0 else auto_gumus_gram_usd
        gumus_baz_usd = st.number_input("Manuel Gümüş ($/Gr)", value=float(varsayilan_g), step=0.01, format="%.3f")
    
    st.divider()

    # --- 2. ALTIN AYARLARI (YENİ) ---
    st.subheader("🥇 Altın Ayarları")
    has_altin_usd_gr = altin_ons / 31.1035
    
    mode_altin = st.radio("Altın Kaynağı", ["Otomatik", "Manuel"], horizontal=True, key="altin_radio")

    if mode_altin == "Otomatik" and market_data['status'] == 'success':
        altin_baz_usd = has_altin_usd_gr
        st.info(f"Harem Has Altın: ${altin_baz_usd:.2f}")
    else:
        varsayilan_a = 2650.0 / 34.0 if has_altin_usd_gr == 0 else has_altin_usd_gr
        altin_baz_usd = st.number_input("Manuel Has Altın ($/Gr)", value=float(varsayilan_a), step=1.0, format="%.2f", help="Buraya 24 Ayar (Has) Dolar fiyatını girin.")

    st.divider()
    
    # MALİYETLER
    st.write("🔧 **İşçilik & Giderler**")
    iscilik_gumus = st.number_input("Gümüş İşçilik ($/gr)", value=1.50, step=0.10)
    iscilik_altin = st.number_input("Altın İşçilik ($/gr)", value=10.00, step=0.50)
    
    kargo_tl = st.number_input("Kargo (TL)", value=650.0)
    indirim_yuzde = st.number_input("Etsy İndirim (%)", value=15.0)
    
    st.divider()
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN ---
st.header("💎 Etsy Akıllı Fiyat Paneli")

t1, t2 = st.tabs(["📊 Ürün Listesi", "➕ Yeni Ürün Ekle"])

# --- TAB 1: ÜRÜN LİSTELEME ---
with t1:
    if not df.empty:
        all_kats = ["Hepsi"] + sorted(list(df['Kategori'].unique()))
        try:
            secilen_kat = st.pills("Kategoriler", all_kats, default="Hepsi")
        except:
            secilen_kat = st.selectbox("Kategori", all_kats)

        arama = st.text_input("🔍 Ürün Ara...", "")
        
        mask = df['Ürün'].astype(str).str.lower().str.contains(arama.lower())
        if secilen_kat != "Hepsi": mask = mask & (df['Kategori'] == secilen_kat)
        f_df = df[mask]
        
        if view_mode == "🎨 Kartlar":
            cols = st.columns(4)
            for idx, row in f_df.reset_index().iterrows():
                row_idx = int(row.get('index')) + 2
                
                # VERİLER
                m_gr = safe_float(row.get('Gr', 0))
                m_kar = safe_float(row.get('Hedef Kar', 0))
                m_kap = safe_float(row.get('KaplamaTL', 0))
                m_laz = safe_float(row.get('LazerTL', 0))
                m_maden = str(row.get('Maden', 'Gümüş'))
                
                # --- FİYAT HESAPLAMA MOTORU ---
                komisyon = 0.17 + (indirim_yuzde / 100)
                
                # 1. GÜMÜŞ FİYATI HESAPLA (Varsayılan olarak her zaman hesapla)
                cost_gumus_usd = (m_gr * gumus_baz_usd) + (m_gr * iscilik_gumus)
                cost_gumus_tl = (cost_gumus_usd * dolar_kuru) + m_kap + m_laz + kargo_tl
                fiyat_gumus = (cost_gumus_tl + m_kar) / (1 - komisyon)
                
                # 2. ALTIN (14K) FİYATI HESAPLA (Karşılaştırma için)
                # ÖNEMLİ: Gümüş kalıbı altına dökülürse yaklaşık 1.35 kat ağır gelir.
                # 14 Ayar Milyem: 0.585
                altin_yogunluk_farki = 1.35 
                tahmini_altin_gr = m_gr * altin_yogunluk_farki
                
                cost_altin_usd = (tahmini_altin_gr * altin_baz_usd * 0.585) + (tahmini_altin_gr * iscilik_altin)
                cost_altin_tl = (cost_altin_usd * dolar_kuru) + m_laz + kargo_tl # Altında kaplama olmaz genelde
                
                # Altında kar marjı genelde daha yüksek istenir ama şimdilik aynı karı ekleyelim
                # veya karı oranlayabiliriz. Şimdilik sabit kar + %10 risk payı koyalım
                fiyat_altin = (cost_altin_tl + (m_kar * 1.5)) / (1 - komisyon)

                # KART GÖSTERİMİ
                with cols[idx % 4]:
                    img = row.get('GörselData', '')
                    
                    st.markdown(f"""
                    <div style="background:white; padding:15px; border-radius:12px; border:1px solid #eee; text-align:center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                        <img src="data:image/jpeg;base64,{img}" style="height:120px; object-fit:contain; margin-bottom:10px;">
                        <p style="font-weight:bold; margin:0 0 10px 0; font-size:14px; height:40px; overflow:hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">{row.get('Ürün')}</p>
                        
                        <div style="display:flex; justify-content:space-between; align-items:center; background:#f8f9fa; padding:8px; border-radius:8px;">
                            <div style="text-align:left; width:48%; border-right:1px solid #ddd;">
                                <div style="font-size:10px; color:#7f8c8d;">🥈 925 Gümüş</div>
                                <div style="color:#2c3e50; font-weight:bold; font-size:15px;">{fiyat_gumus:,.0f} ₺</div>
                            </div>
                            <div style="text-align:right; width:48%;">
                                <div style="font-size:10px; color:#f39c12;">🟡 14K Altın</div>
                                <div style="color:#d35400; font-weight:bold; font-size:15px;">{fiyat_altin:,.0f} ₺</div>
                            </div>
                        </div>

                        <div style="font-size:10px; color:gray; margin-top:8px;">
                            ⚖️ Ag: {m_gr}gr | Au: ~{tahmini_altin_gr:.1f}gr
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c_edit, c_del = st.columns(2)
                    if c_edit.button("✏️", key=f"e_{idx}"):
                        st.session_state[f"form_{idx}"] = not st.session_state.get(f"form_{idx}", False)
                    if c_del.button("🗑️", key=f"d_{idx}"):
                        sheet.delete_rows(row_idx)
                        st.cache_data.clear()
                        st.rerun()
                    
                    if st.session_state.get(f"form_{idx}"):
                        with st.form(f"edit_form_{idx}"):
                            n_name = st.text_input("Ad", value=row.get('Ürün'))
                            n_gr = st.text_input("Gümüş Gram", value=str(m_gr))
                            n_kar = st.number_input("Hedef Kar", value=float(m_kar))
                            
                            if st.form_submit_button("💾 Kaydet"):
                                sheet.update_cell(row_idx, 1, n_name)
                                sheet.update_cell(row_idx, 3, n_gr.replace(',','.'))
                                sheet.update_cell(row_idx, 4, n_kar)
                                st.session_state[f"form_{idx}"] = False
                                st.cache_data.clear()
                                st.rerun()
        else:
            st.dataframe(f_df, use_container_width=True)

# --- TAB 2: YENİ ÜRÜN EKLEME ---
with t2:
    st.subheader("Yeni Ürün Ekle")
    
    with st.form("yeni_urun_formu", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            u_ad = st.text_input("Ürün Adı", placeholder="Örn: Baget Taşlı Yüzük")
            u_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Küpe", "Bileklik", "Diğer"])
            u_gr = st.text_input("Gümüş Ağırlığı (Gr)", value="0.0")
            
        with c2:
            u_kap = st.number_input("Kaplama (TL)", value=0.0)
            u_laz = st.number_input("Lazer (TL)", value=0.0)
            u_kar = st.number_input("Hedef Kar (TL)", value=3000.0)
            u_img = st.file_uploader("Görsel Yükle", type=['jpg','png'])
        
        submitted = st.form_submit_button("Listeye Ekle")
        
        if submitted:
            if not u_ad:
                st.error("Lütfen ürün adı giriniz.")
            else:
                with st.spinner("Ekleniyor..."):
                    img_str = image_to_base64(u_img)
                    
                    # --- GÜVENLİ EKLEME ---
                    mevcut_urunler = sheet.col_values(1)
                    son_satir_index = len(mevcut_urunler) + 1
                    
                    yeni_veri = [
                        u_ad, 
                        "Gümüş", # Varsayılan maden
                        u_gr.replace(',','.'), 
                        u_kar, 
                        img_str, 
                        u_kat, 
                        u_kap, 
                        u_laz, 
                        0
                    ]
                    
                    aralik = f"A{son_satir_index}:I{son_satir_index}"
                    sheet.update(range_name=aralik, values=[yeni_veri])
                    
                    st.success(f"✅ '{u_ad}' eklendi!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()

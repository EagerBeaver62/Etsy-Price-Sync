import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import time
import requests

st.set_page_config(page_title="CRIPP Jewelry Panel", layout="wide")

# ================= GOOGLE SHEETS =================
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gsheets"],
        scopes=scope
    )
    return gspread.authorize(creds)

client = get_gspread_client()
sheet = client.open("Etsy Price Sync").get_worksheet(0)

# ================= HELPER =================
def safe_float(value):
    try:
        return float(str(value).replace(",", "."))
    except:
        return 0

def image_to_base64(uploaded_file):
    if uploaded_file is None:
        return ""
    img = Image.open(uploaded_file).convert("RGB")
    img.thumbnail((400, 400))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return base64.b64encode(buf.getvalue()).decode()

# ================= METAL API =================
def get_metal_price():
    try:
        r = requests.get("https://api.metals.live/v1/spot/gold")
        gold_price = r.json()[0]["price"]
        return gold_price
    except:
        return None

# ================= DATA =================
data = sheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    df = df[df["Ürün"].astype(str).str.strip() != ""]

# ================= SIDEBAR =================
with st.sidebar:

    st.title("💎 Fiyat Ayarları")

    dolar_kuru = st.number_input("Dolar Kuru", value=44.07)

    st.subheader("Gümüş")

    gumus_gram_tl = st.number_input(
        "Has Gümüş TL",
        value=125.60
    )

    iscilik_gumus_usd = st.number_input(
        "İşçilik $/gr",
        value=1.50
    )

    st.subheader("14K Altın")

    altin_has_gram_usd = st.number_input(
        "Has Altın $",
        value=85.0
    )

    iscilik_altin = st.number_input(
        "Altın İşçilik $/gr",
        value=10.0
    )

    st.markdown("---")

    kargo_tl = st.number_input("Kargo", value=650.0)

    indirim_yuzde = st.number_input("Etsy indirim %", value=15.0)

    st.markdown("---")

    st.subheader("Kar Simülasyonu")

    kar_multiplier = st.slider(
        "Kar çarpanı",
        1.0,
        3.0,
        1.0,
        0.1
    )

    st.markdown("---")

    st.subheader("Toplu Güncelleme")

    toplu_artis = st.number_input(
        "Kar Artışı TL",
        value=0
    )

    kategori_sec = st.selectbox(
        "Kategori",
        ["Hepsi","Yüzük","Kolye","Bileklik","Küpe"]
    )

# ================= ETSY KAR =================
def calculate_profit(sale_price_tl, cost_tl):

    usd_price = sale_price_tl / dolar_kuru

    etsy_fee = usd_price * 0.065
    payment_fee = usd_price * 0.03 + 0.25
    listing_fee = 0.20

    total_fee_usd = etsy_fee + payment_fee + listing_fee

    total_fee_tl = total_fee_usd * dolar_kuru

    net_profit = sale_price_tl - total_fee_tl - cost_tl

    return net_profit

# ================= PANEL =================
st.title("Etsy Akıllı Fiyat Paneli")

tab1, tab2 = st.tabs(["Ürün Listesi", "Yeni Ürün"])

# ================= LIST =================
with tab1:

    search = st.text_input("Ürün Ara")

    if not df.empty:

        if search:
            f_df = df[df["Ürün"].str.contains(search, case=False)]
        else:
            f_df = df

        cols = st.columns(4)

        for idx, row in f_df.reset_index().iterrows():

            row_idx = int(row["index"]) + 2

            gr = safe_float(row.get("Gr"))

            kar = safe_float(row.get("Hedef Kar")) * kar_multiplier

            kaplama = safe_float(row.get("KaplamaTL"))

            lazer = safe_float(row.get("LazerTL"))

            mine = safe_float(row.get("MineTL"))

            if kategori_sec != "Hepsi":
                if row["Kategori"] != kategori_sec:
                    continue

            kar += toplu_artis

            komisyon = 0.17 + (indirim_yuzde / 100)

            g_maliyet = (
                (gr * gumus_gram_tl)
                + (gr * iscilik_gumus_usd * dolar_kuru)
                + kaplama
                + lazer
                + mine
                + kargo_tl
            )

            fiyat_gumus = (g_maliyet + kar) / (1 - komisyon)

            usd_price = fiyat_gumus / dolar_kuru

            net_profit = calculate_profit(
                fiyat_gumus,
                g_maliyet
            )

            with cols[idx % 4]:

                st.image(
                    f"data:image/jpeg;base64,{row['GörselData']}"
                )

                st.write(row["Ürün"])

                st.success(f"Gümüş: {round(fiyat_gumus)} ₺")

                st.info(f"${round(usd_price,2)}")

                if net_profit < 0:
                    st.error(f"Zarar: {round(net_profit)} ₺")
                else:
                    st.caption(f"Net Kar: {round(net_profit)} ₺")

                st.caption(f"{gr} gr")

                c1, c2 = st.columns(2)

                if c1.button("Sil", key=f"del{idx}"):

                    sheet.delete_rows(row_idx)

                    st.rerun()

# ================= NEW =================
with tab2:

    with st.form("new_product"):

        ad = st.text_input("Ürün Adı")

        gram = st.number_input(
            "Gram",
            step=0.1
        )

        kar = st.number_input(
            "Kar",
            value=3000
        )

        img = st.file_uploader(
            "Foto",
            type=["jpg","jpeg","png"]
        )

        if st.form_submit_button("Kaydet"):

            img64 = image_to_base64(img)

            sheet.append_row(
                [
                    ad,
                    "Gümüş",
                    gram,
                    kar,
                    img64,
                    "Yüzük",
                    0,
                    0,
                    0
                ],
                value_input_option="USER_ENTERED"
            )

            st.success("Ürün eklendi")

            time.sleep(1)

            st.rerun()

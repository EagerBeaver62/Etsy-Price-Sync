import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import time

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
        "Kar Çarpanı",
        1.0,
        3.0,
        1.0,
        0.1
    )

    st.subheader("Toplu Kar Artışı")

    toplu_kar = st.number_input(
        "TL",
        value=0
    )

    kategori_filtre = st.selectbox(
        "Kategori",
        ["Hepsi","Yüzük","Kolye","Bileklik","Küpe"]
    )


# ================= ETSY KAR =================

def etsy_net_profit(price_tl, cost_tl):

    usd = price_tl / dolar_kuru

    etsy_fee = usd * 0.065
    payment_fee = usd * 0.03 + 0.25
    listing_fee = 0.20

    total_fee = (etsy_fee + payment_fee + listing_fee) * dolar_kuru

    return price_tl - total_fee - cost_tl


# ================= EDIT MODAL =================

@st.dialog("Ürün Düzenle")

def edit_product(row, row_idx):

    with st.form("edit_form"):

        ad = st.text_input("Ürün Adı", value=row["Ürün"])

        c1, c2 = st.columns(2)

        with c1:

            gram = st.number_input(
                "Gram",
                value=float(safe_float(row["Gr"])),
                step=0.1
            )

            kar = st.number_input(
                "Hedef Kar",
                value=float(safe_float(row["Hedef Kar"]))
            )

            mine = st.number_input(
                "Mine TL",
                value=float(safe_float(row.get("MineTL")))
            )

        with c2:

            kaplama = st.number_input(
                "Kaplama TL",
                value=float(safe_float(row.get("KaplamaTL")))
            )

            lazer = st.number_input(
                "Lazer TL",
                value=float(safe_float(row.get("LazerTL")))
            )

            ekstra = st.number_input(
                "Ekstra Gider",
                value=float(safe_float(row.get("EkstraTL")))
            )

        if st.form_submit_button("Kaydet"):

            updated = [
                ad,
                "Gümüş",
                gram,
                kar,
                row["GörselData"],
                row["Kategori"],
                kaplama,
                lazer,
                mine,
                ekstra
            ]

            sheet.update(
                f"A{row_idx}:J{row_idx}",
                [updated],
                value_input_option="USER_ENTERED"
            )

            st.success("Güncellendi")

            time.sleep(0.5)

            st.rerun()


# ================= PANEL =================

st.title("💎 CRIPP Etsy Fiyat Paneli")

tab1, tab2 = st.tabs(["📦 Ürünler", "➕ Yeni Ürün"])


# ================= ÜRÜNLER =================

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

            if kategori_filtre != "Hepsi":

                if row["Kategori"] != kategori_filtre:
                    continue

            gr = safe_float(row["Gr"])

            kar = safe_float(row["Hedef Kar"]) * kar_multiplier + toplu_kar

            kaplama = safe_float(row.get("KaplamaTL"))

            lazer = safe_float(row.get("LazerTL"))

            mine = safe_float(row.get("MineTL"))

            ekstra = safe_float(row.get("EkstraTL"))

            komisyon = 0.17 + (indirim_yuzde / 100)

            maliyet = (
                (gr * gumus_gram_tl)
                + (gr * iscilik_gumus_usd * dolar_kuru)
                + kaplama
                + lazer
                + mine
                + ekstra
                + kargo_tl
            )

            fiyat = (maliyet + kar) / (1 - komisyon)

            usd = fiyat / dolar_kuru

            net = etsy_net_profit(fiyat, maliyet)

            with cols[idx % 4]:

                st.markdown(f"""
                <div style="
                border:1px solid #eee;
                border-radius:14px;
                padding:15px;
                background:white;
                box-shadow:0 4px 12px rgba(0,0,0,0.06);
                text-align:center;
                ">

                <img src="data:image/jpeg;base64,{row['GörselData']}"
                style="width:100%;height:200px;object-fit:contain;border-radius:10px">

                <h4 style="margin-top:10px">{row['Ürün']}</h4>

                <div style="
                background:#f1f8f6;
                padding:8px;
                border-radius:8px;
                margin-bottom:5px;
                color:#2ecc71;
                font-weight:bold">
                {round(fiyat)} ₺
                </div>

                <div style="
                background:#fef6e4;
                padding:6px;
                border-radius:8px;
                font-weight:bold">
                ${round(usd,2)}
                </div>

                <div style="font-size:12px;color:gray;margin-top:5px">
                ⚖ {gr} gr
                </div>

                </div>
                """, unsafe_allow_html=True)

                if net < 0:

                    st.error(f"Zarar: {round(net)} ₺")

                else:

                    st.caption(f"Net Kar: {round(net)} ₺")

                c1, c2 = st.columns(2)

                if c1.button("✏️ Düzenle", key=f"edit{idx}"):

                    edit_product(row, row_idx)

                if c2.button("🗑️ Sil", key=f"del{idx}"):

                    sheet.delete_rows(row_idx)

                    st.rerun()


# ================= YENİ ÜRÜN =================

with tab2:

    with st.form("new_product"):

        ad = st.text_input("Ürün Adı")

        kategori = st.selectbox(
            "Kategori",
            ["Yüzük","Kolye","Bileklik","Küpe"]
        )

        gram = st.number_input(
            "Gram",
            step=0.1
        )

        kar = st.number_input(
            "Hedef Kar",
            value=3000
        )

        mine = st.number_input("Mine TL", value=0)

        kaplama = st.number_input("Kaplama TL", value=0)

        lazer = st.number_input("Lazer TL", value=0)

        ekstra = st.number_input("Ekstra Gider", value=0)

        img = st.file_uploader(
            "Görsel",
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
                    kategori,
                    kaplama,
                    lazer,
                    mine,
                    ekstra
                ],
                value_input_option="USER_ENTERED"
            )

            st.success("Ürün eklendi")

            time.sleep(1)

            st.rerun()

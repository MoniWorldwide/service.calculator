import sys
# --- FIX FOR PYTHON 3.13+ (imghdr er fjernet fra Python) ---
try:
    import imghdr
except ImportError:
    from unittest.mock import MagicMock
    mock_imghdr = MagicMock()
    # Vi giver mock-objektet de funktioner, som modulerne forventer
    mock_imghdr.what.return_value = None
    sys.modules["imghdr"] = mock_imghdr

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_drawable_canvas import st_canvas

# --- KONFIGURATION AF SIDEN ---
st.set_page_config(page_title="Deutz-Fahr Serviceaftale", layout="wide")

# --- STYRING AF MAPPER OG LOGO ---
DATA_MAPPE = "service_ark"
FAST_DIVERSE_GEBYR = 500.0 

def find_logo():
    mulige_stier = ["logo.png", os.path.join(DATA_MAPPE, "logo.png")]
    for sti in mulige_stier:
        if os.path.exists(sti):
            return sti
    return None

# --- TOP SEKTION ---
col1, col2 = st.columns([1, 3])
logo_sti = find_logo()

with col1:
    if logo_sti:
        st.image(logo_sti, width=200)
    else:
        st.markdown("<h1 style='color: #d32f2f; margin: 0;'>DEUTZ-FAHR</h1>", unsafe_allow_html=True)

with col2:
    st.markdown("<h1 style='margin-bottom: 0; color: #367c2b;'>Serviceberegner & Digital Aftale</h1>", unsafe_allow_html=True)

st.divider()

# Find filer og indlæs data
if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' ikke fundet.")
else:
    filer = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller = sorted([f.replace('.csv', '') for f in filer])

    if modeller:
        st.sidebar.header("1. Maskine & Priser")
        model_valg = st.sidebar.selectbox("Vælg Traktormodel", modeller)
        timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750)
        ordretype = st.sidebar.radio("Pristype", ["Brutto", "Haste", "Uge", "Måned"])
        avance = st.sidebar.slider("Avance på reservedele (%)", 0, 50, 0)

        st.sidebar.divider()
        st.sidebar.header("2. Kundeinformation")
        forhandler = st.sidebar.text_input("Forhandler", "Indtast forhandler")
        kunde = st.sidebar.text_input("Kundenavn")
        kunde_adr = st.sidebar.text_input("Adresse / By")
        stelnummer = st.sidebar.text_input("Stelnummer")

        # Indlæs den specifikke CSV
        valgt_fil = os.path.join(DATA_MAPPE, f"{model_valg}.csv")
        try:
            df_raw = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
            h_idx = 0
            for i, row in df_raw.iterrows():
                if row.astype(str).str.contains('timer', case=False).any():
                    h_idx = i
                    break
            df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=h_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            besk_kol = df.columns[0]
            pris_kol = df.columns[7]
            int_kols = [c for c in df.columns if "timer" in c.lower()]

            def rens(val):
                if pd.isna(val): return 0.0
                s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
                return float(s.replace(',', '.').strip()) if s else 0.0

            if int_kols:
                st.sidebar.divider()
                valgt_int = st.sidebar.selectbox("Aftale stop-punkt", int_kols)
                valgt_t = int("".join(filter(str.isdigit, valgt_int)))
                
                # Beregning af historik (alt før stop-punktet)
                hist_int = [c for c in int_kols if int("".join(filter(str.isdigit, c))) < valgt_t]
                
                v_idx = df[df[besk_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                v_s = v_idx[0] if len(v_idx) > 0 else 9999
                
                t_res, t_vd, t_arb = 0.0, 0.0, 0.0
                for i in hist_int:
                    m = df[i].astype(str).replace(['nan', 'None', ''], None).notna()
                    res_df = df[(df.index < v_s) & m]
                    t_res += (res_df[ordretype].apply(rens) * res_df['Antal'].apply(rens) * (1 + avance/100)).sum()
                    
                    vd_df = df[(df.index > v_s) & m]
                    vd_df = vd_df[~vd_df[besk_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                    t_vd += (vd_df[pris_kol].apply(rens) * vd_df['Antal'].apply(rens)).sum()
                    t_vd += FAST_DIVERSE_GEBYR # Din faste instruks
                    
                    m_arb = df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)
                    t_std = rens(df[m_arb][i].values[0]) if m_arb.any() else 0.0
                    t_arb += (t_std * timepris)

                total = t_res + t_vd + t_arb
                cph = total / valgt_t if valgt_t > 0 else 0

                tab1, tab2 = st.tabs(["📊 Økonomi", "✍️ Serviceaftale"])

                with tab1:
                    st.metric("Serviceomkostning pr. time", f"{cph:,.2f} DKK/t")
                    st.write(f"Akkumuleret total for 0-{valgt_t} timer: **{total:,.2f} DKK**")

                with tab2:
                    st.markdown(f"""
                    <div style="padding: 20px; border: 1px solid #ccc; background-color: white; color: black;">
                        <h2 style="text-align: center; color: #367c2b;">SERVICEAFTALE</h2>
                        <p><b>Model:</b> Deutz-Fahr {model_valg} | <b>Stelnummer:</b> {stelnummer}</p>
                        <p><b>Kunde:</b> {kunde}</p>
                        <p><b>Pris pr. driftstime: {cph:,.2f} DKK (Ekskl. moms)</b></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        st.caption("Forhandler")
                        st_canvas(stroke_width=2, stroke_color="black", background_color="#eee", height=100, width=250, key="c1")
                    with col_s2:
                        st.caption("Kunde")
                        st_canvas(stroke_width=2, stroke_color="blue", background_color="#eee", height=100, width=250, key="c2")
                    
                    if st.button("Udfør"):
                        st.success("Aftale bekræftet!")

        except Exception as e:
            st.error(f"Fejl: {e}")

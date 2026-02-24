import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_drawable_canvas import st_canvas  # Ny import til underskrift

# Konfiguration
st.set_page_config(page_title="Deutz-Fahr Serviceaftale", layout="wide")

# --- KONSTANTER ---
DATA_MAPPE = "service_ark"
FAST_DIVERSE_GEBYR = 500.0 

# --- LOGO OG TITEL ---
col1, col2 = st.columns([1, 3])
with col1:
    logo_path = os.path.join(DATA_MAPPE, "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        st.markdown("<h1 style='color: #d32f2f; margin: 0;'>DEUTZ-FAHR</h1>", unsafe_allow_html=True)

with col2:
    st.markdown("<h1 style='margin-bottom: 0; color: #367c2b;'>Serviceberegner & Digital Aftale</h1>", unsafe_allow_html=True)

st.divider()

# Find filer
if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' ikke fundet.")
    modeller_raw = []
else:
    filer_i_mappe = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller_raw = sorted([f.replace('.csv', '') for f in filer_i_mappe])

if modeller_raw:
    # --- SIDEBAR KONFIGURATION ---
    st.sidebar.header("1. Maskine & Priser")
    model_visning = {f"Deutz-Fahr {m}": m for m in modeller_raw}
    valgt_visningsnavn = st.sidebar.selectbox("Vælg Traktormodel", list(model_visning.keys()))
    model_valg = model_visning[valgt_visningsnavn]
    
    timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750)
    ordretype = st.sidebar.radio("Pristype", ["Brutto", "Haste", "Uge", "Måned"])
    avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

    st.sidebar.divider()
    st.sidebar.header("2. Kunde & Forhandler")
    forhandler_navn = st.sidebar.text_input("Forhandler", "Indtast forhandler")
    kunde_navn = st.sidebar.text_input("Kundenavn")
    kunde_adr = st.sidebar.text_input("Adresse / By")
    stelnummer = st.sidebar.text_input("Stelnummer")

    # --- DATABEHANDLING ---
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
        
        beskrivelse_kol = df.columns[0]
        pris_kol_h = df.columns[7]
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]

        def rens(val):
            if pd.isna(val): return 0.0
            s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
            return float(s.replace(',', '.').strip()) if s else 0.0

        if interval_kolonner:
            st.sidebar.divider()
            valgt_interval = st.sidebar.selectbox("Aftale stop-punkt", interval_kolonner)
            valgt_t = int("".join(filter(str.isdigit, valgt_interval)))
            
            hist_int = [c for c in interval_kolonner if int("".join(filter(str.isdigit, c))) < valgt_t]
            
            # Beregn totaler
            v_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            v_s = v_idx[0] if len(v_idx) > 0 else 9999
            
            tot_res, tot_vd, tot_arb = 0.0, 0.0, 0.0
            for i in hist_int:
                mask = df[i].astype(str).replace(['nan', 'None', ''], None).notna()
                res_p = df[(df.index < v_s) & mask]
                tot_res += (res_p[ordretype].apply(rens) * res_p['Antal'].apply(rens) * (1 + avance/100)).sum()
                
                vd_p = df[(df.index > v_s) & mask]
                vd_p = vd_p[~vd_p[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                tot_vd += (vd_p[pris_kol_h].apply(rens) * vd_p['Antal'].apply(rens)).sum()
                tot_vd += FAST_DIVERSE_GEBYR # Din faste kost (500 DKK)
                
                mask_arb = df[beskrivelse_kol].astype(str).str.contains('Arbejd', case=False, na=False)
                t_std = rens(df[mask_arb][i].values[0]) if mask_arb.any() else 0.0
                tot_arb += (t_std * timepris)

            tot_alt = tot_res + tot_vd + tot_arb
            cph = tot_alt / valgt_t if valgt_t > 0 else 0

            # --- TABS ---
            t1, t2 = st.tabs(["📊 Beregner", "✍️ Underskriv Aftale"])

            with t1:
                st.metric("Reel pris pr. driftstime", f"{cph:,.2f} DKK/t")
                st.write(f"Baseret på historik frem til {valgt_t} timer.")

            with t2:
                # Kontrakt layout
                st.markdown(f"""
                <div style="padding: 30px; border: 1px solid #eee; background-color: white; color: black;">
                    <h2 style="color: #367c2b; text-align: center;">SERVICEAFTALE</h2>
                    <p><strong>Model:</strong> Deutz-Fahr {model_valg} | <strong>Stelnummer:</strong> {stelnummer}</p>
                    <p><strong>Kunde:</strong> {kunde_navn}, {kunde_adr}</p>
                    <hr>
                    <p>Denne aftale dækker alle foreskrevne services frem til <b>{valgt_t} timer</b>.<br>
                    Den aftalte timepris for service er <b>{cph:,.2f} DKK pr. driftstime</b> (ekskl. moms).</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("---")
                
                # Underskriftsfelter
                c_sign1, c_sign2 = st.columns(2)
                
                with c_sign1:
                    st.write(f"**{forhandler_navn} (Forhandler)**")
                    st_canvas(
                        fill_color="rgba(255, 255, 255, 0)",
                        stroke_width=2,
                        stroke_color="black",
                        background_color="#f0f2f6",
                        height=150,
                        width=300,
                        drawing_mode="freedraw",
                        key="canvas_forhandler",
                    )
                
                with c_sign2:
                    st.write(f"**{kunde_navn} (Kunde)**")
                    st_canvas(
                        fill_color="rgba(255, 255, 255, 0)",
                        stroke_width=2,
                        stroke_color="blue", # Blå farve til kunden for kontrast
                        background_color="#f0f2f6",
                        height=150,
                        width=300,
                        drawing_mode="freedraw",
                        key="canvas_kunde",
                    )
                
                st.markdown("---")
                if st.button("✅ Bekræft og lås aftale"):
                    st.success("Aftalen er klar til print (Ctrl+P) eller arkivering som PDF.")

    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")

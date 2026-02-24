import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURATION AF SIDEN ---
st.set_page_config(page_title="Deutz-Fahr Serviceaftale", layout="wide")

# --- STYRING AF MAPPER OG LOGO ---
DATA_MAPPE = "service_ark"
FAST_DIVERSE_GEBYR = 500.0  # Din faste instruks

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
    st.markdown("<h1 style='margin-bottom: 0; color: #367c2b;'>Serviceberegner & Aftale</h1>", unsafe_allow_html=True)

st.divider()

# Find filer
if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' ikke fundet. Tjek din GitHub.")
else:
    filer = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller = sorted([f.replace('.csv', '') for f in filer])

    if modeller:
        # --- SIDEBAR ---
        st.sidebar.header("1. Maskine & Priser")
        model_valg = st.sidebar.selectbox("Vælg Traktormodel", modeller)
        timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750)
        ordretype = st.sidebar.radio("Pristype", ["Brutto", "Haste", "Uge", "Måned"])
        avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

        st.sidebar.divider()
        st.sidebar.header("2. Kundeinformation")
        forhandler = st.sidebar.text_input("Forhandler", "Indtast forhandler")
        kunde = st.sidebar.text_input("Kundenavn")
        kunde_adr = st.sidebar.text_input("Adresse / By")
        stelnummer = st.sidebar.text_input("Stelnummer")

        # Indlæs CSV
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
                
                # Beregning (kun før stop-punktet)
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
                    t_vd += FAST_DIVERSE_GEBYR # Din faste kost
                    
                    m_arb = df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)
                    t_std = rens(df[m_arb][i].values[0]) if m_arb.any() else 0.0
                    t_arb += (t_std * timepris)

                total = t_res + t_vd + t_arb
                cph = total / valgt_t if valgt_t > 0 else 0

                # --- VISNING ---
                tab1, tab2 = st.tabs(["📊 Økonomisk Overblik", "📜 Serviceaftale"])

                with tab1:
                    st.subheader(f"Beregning for 0 - {valgt_t} timer")
                    st.metric("Servicepris pr. driftstime", f"{cph:,.2f} DKK/t")
                    st.info(f"Baseret på {len(hist_int)} services inkl. {FAST_DIVERSE_GEBYR} DKK i diverse pr. gang.")

                with tab2:
                    st.markdown(f"""
                    <div style="padding: 30px; border: 2px solid #367c2b; background-color: white; color: black; font-family: sans-serif;">
                        <h2 style="text-align: center; color: #367c2b;">SERVICEAFTALE</h2>
                        <hr>
                        <p><b>Dato:</b> {datetime.now().strftime('%d-%m-%Y')}</p>
                        <p><b>Model:</b> Deutz-Fahr {model_valg} | <b>Stelnummer:</b> {stelnummer}</p>
                        <p><b>Kunde:</b> {kunde} | <b>Adresse:</b> {kunde_adr}</p>
                        <br>
                        <p>Denne aftale dækker alle foreskrevne services frem til <b>{valgt_t} timer</b>.</p>
                        <p style="font-size: 1.2em;"><b>Fast pris pr. driftstime: {cph:,.2f} DKK</b> (Ekskl. moms)</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("### Digital Bekræftelse")
                    c1, c2 = st.columns(2)
                    with c1:
                        forh_sign = st.text_input("Underskrift Forhandler (Navn)", value=forhandler)
                    with c2:
                        kunde_sign = st.text_input("Underskrift Kunde (Navn)")
                    
                    if st.button("Udfærdig Aftale"):
                        if not kunde_sign:
                            st.warning("Kunden skal indtaste sit navn for at bekræfte.")
                        else:
                            st.success(f"Aftale bekræftet af {kunde_sign} d. {datetime.now().strftime('%d-%m-%Y')}")
                            st.balloons()
                            st.info("Du kan nu printe siden som PDF (Ctrl+P)")

        except Exception as e:
            st.error(f"Fejl: {e}")

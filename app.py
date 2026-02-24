import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

DATA_MAPPE = "service_ark"
FAST_DIVERSE_GEBYR = 500.0  # Din faste instruks (Diverse/Miljø)

def find_logo():
    # Kigger efter logo i både hovedmappe og undermappe
    stier = ["logo.png", os.path.join(DATA_MAPPE, "logo.png")]
    for sti in stier:
        if os.path.exists(sti):
            return sti
    return None

# --- 2. HEADER ---
col_l, col_r = st.columns([1, 3])
logo_sti = find_logo()

with col_l:
    if logo_sti:
        st.image(logo_sti, width=180)
    else:
        st.markdown("<h2 style='color: #d32f2f;'>DEUTZ-FAHR</h2>", unsafe_allow_html=True)

with col_r:
    st.markdown("<h1 style='margin-bottom: 0; color: #367c2b;'>Serviceberegner & Digital Aftale</h1>", unsafe_allow_html=True)
    st.caption(f"Dato: {datetime.now().strftime('%d-%m-%Y')}")

st.divider()

# --- 3. FILHÅNDTERING ---
if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' blev ikke fundet. Husk at uploade den til GitHub.")
else:
    filer = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller = sorted([f.replace('.csv', '') for f in filer])

    if modeller:
        # SIDEBAR
        st.sidebar.header("1. Maskine & Økonomi")
        model_valg = st.sidebar.selectbox("Vælg Traktormodel", modeller)
        timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750, step=25)
        ordretype = st.sidebar.radio("Pristype (Filtre)", ["Brutto", "Haste", "Uge", "Måned"])
        avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

        st.sidebar.divider()
        st.sidebar.header("2. Kundeinformation")
        forhandler = st.sidebar.text_input("Forhandler", "Indtast forhandler")
        kunde_navn = st.sidebar.text_input("Kundenavn")
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
            pris_kol_h = df.columns[7] # Kolonne H
            int_kols = [c for c in df.columns if "timer" in c.lower()]

            def rens_tal(val):
                if pd.isna(val): return 0.0
                s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
                s = s.replace(',', '.').strip()
                try: return float(s)
                except: return 0.0

            if int_kols:
                st.sidebar.divider()
                valgt_int = st.sidebar.selectbox("Aftale stop-punkt", int_kols)
                valgt_t = int("".join(filter(str.isdigit, valgt_int)))
                
                # Beregn kun historik (services FØR stop-punktet)
                hist_int = [c for c in int_kols if int("".join(filter(str.isdigit, c))) < valgt_t]
                
                # Find start på væsker
                v_idx = df[df[besk_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                v_s = v_idx[0] if len(v_idx) > 0 else 9999
                
                t_res, t_vd, t_arb = 0.0, 0.0, 0.0
                for i in hist_int:
                    mask = df[i].astype(str).replace(['nan', 'None', ''], None).notna()
                    # Filtre/Dele
                    res_df = df[(df.index < v_s) & mask]
                    t_res += (res_df[ordretype].apply(rens_tal) * res_df['Antal'].apply(rens_tal) * (1 + avance/100)).sum()
                    # Væsker & Diverse
                    vd_df = df[(df.index > v_s) & mask]
                    vd_df = vd_df[~vd_df[besk_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                    for _, r in vd_df.iterrows():
                        t_vd += rens_tal(r[pris_kol_h]) * rens_tal(r['Antal'])
                    
                    # DIN INSTRUKS: Tilføj 500 DKK pr. service
                    t_vd += FAST_DIVERSE_GEBYR
                    
                    # Arbejdsløn
                    m_arb = df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)
                    t_std = rens_tal(df[m_arb][i].values[0]) if m_arb.any() else 0.0
                    t_arb += (t_std * timepris)

                total_omk = t_res + t_vd + t_arb
                cph = total_omk / valgt_t if valgt_t > 0 else 0

                # --- VISNING (TABS) ---
                tab1, tab2 = st.tabs(["📊 Økonomisk Overblik", "📜 Digital Serviceaftale"])

                with tab1:
                    st.subheader(f"Beregning for 0 - {valgt_t} timer")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Reservedele Total", f"{t_res:,.2f} kr.")
                    c2.metric("Væsker & Diverse", f"{t_vd:,.2f} kr.")
                    c3.metric("Arbejdsløn Total", f"{t_arb:,.2f} kr.")

                    st.markdown(f"""
                        <div style="background-color: #f1f8e9; border: 2px solid #367c2b; padding: 25px; border-radius: 15px; text-align: center; margin-top: 20px;">
                            <h3 style="margin: 0; color: #2e7d32;">AFTALT PRIS PR. DRIFTSTIME</h3>
                            <h1 style="margin: 10px 0; color: #367c2b;">{cph:,.2f} DKK / t</h1>
                            <small>(Ekskl. moms og brændstof | Inkl. {FAST_DIVERSE_GEBYR} kr. i miljøgebyr pr. service)</small>
                        </div>
                    """, unsafe_allow_html=True)

                with tab2:
                    st.markdown(f"""
                    <div style="padding: 30px; border: 1px solid #ddd; background-color: white; color: black; font-family: Arial, sans-serif;">
                        <h2 style="text-align: center; color: #367c2b;">SERVICEAFTALE</h2>
                        <hr>
                        <table style="width: 100%;">
                            <tr><td><b>Model:</b> Deutz-Fahr {model_valg}</td><td><b>Kunde:</b> {kunde_navn}</td></tr>
                            <tr><td><b>Stelnummer:</b> {stelnummer}</td><td><b>Forhandler:</b> {forhandler}</td></tr>
                        </table>
                        <br>
                        <p>Denne aftale omfatter alle planlagte services jf. fabrikantens forskrifter op til <b>{valgt_t} timer</b>.</p>
                        <p style="font-size: 1.2em; border-left: 5px solid #367c2b; padding-left: 10px;">
                            <b>Fast timepris pr. driftstime: {cph:,.2f} DKK (Ekskl. moms)</b>
                        </p>
                        <br><br><br>
                        <div style="display: flex; justify-content: space-between;">
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Forhandler</div>
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Kunde</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("---")
                    st.subheader("Digital Bekræftelse")
                    c_s1, c_s2 = st.columns(2)
                    with c_s1:
                        forh_sign = st.text_input("Underskrift Forhandler", value=forhandler)
                    with c_s2:
                        kunde_sign = st.text_input("Underskrift Kunde (Indtast navn)")
                    
                    if st.button("Udfærdig og Bekræft Aftale"):
                        if kunde_sign:
                            st.success(f"Aftale bekræftet af {kunde_sign} d. {datetime.now().strftime('%d-%m-%Y')}")
                            st.balloons()
                            st.info("Tip: Tryk 'Ctrl + P' for at gemme som PDF eller printe.")
                        else:
                            st.error("Kunden skal indtaste sit navn for at bekræfte.")

        except Exception as e:
            st.error(f"Der opstod en fejl: {e}")

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. GRUNDLÆGGENDE KONFIGURATION ---
# Vi fjerner alle "custom" imports som canvas eller altair for at undgå nedbrud
st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

DATA_MAPPE = "service_ark"
# Din instruks: Tilføj altid 500 DKK pr. interval
FAST_DIVERSE_GEBYR = 500.0 

def find_logo():
    # Robust logo-søger der tjekker begge lokationer
    stier = ["logo.png", os.path.join(DATA_MAPPE, "logo.png")]
    for sti in stier:
        if os.path.exists(sti):
            return sti
    return None

# --- 2. HEADER ---
col_logo, col_title = st.columns([1, 3])
logo_sti = find_logo()

with col_logo:
    if logo_sti:
        st.image(logo_sti, width=200)
    else:
        st.header("DEUTZ-FAHR")

with col_title:
    st.title("Serviceberegner & Kontraktstyring")
    st.write(f"Dato: {datetime.now().strftime('%d-%m-%Y')}")

st.divider()

# --- 3. FILHÅNDTERING ---
if not os.path.exists(DATA_MAPPE):
    st.error(f"FEJL: Mappen '{DATA_MAPPE}' blev ikke fundet. Opret den på GitHub og læg dine CSV-filer i den.")
else:
    filer = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller = sorted([f.replace('.csv', '') for f in filer])

    if not modeller:
        st.warning("Ingen CSV-filer fundet i mappen.")
    else:
        # SIDEBAR: INPUT
        st.sidebar.header("1. Maskindata")
        model_valg = st.sidebar.selectbox("Vælg Model", modeller)
        
        st.sidebar.header("2. Økonomi")
        timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750)
        ordretype = st.sidebar.radio("Reservedelspris", ["Brutto", "Haste", "Uge", "Måned"])
        avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

        st.sidebar.header("3. Kunde & Aftale")
        kunde = st.sidebar.text_input("Kunde")
        stelnummer = st.sidebar.text_input("Stelnummer")
        forhandler = st.sidebar.text_input("Forhandler", "Indtast forhandler")

        # --- 4. BEREGNINGSLOGIK ---
        valgt_fil = os.path.join(DATA_MAPPE, f"{model_valg}.csv")
        try:
            # Vi læser filen og finder headeren dynamisk
            df_raw = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
            h_idx = 0
            for i, row in df_raw.iterrows():
                if row.astype(str).str.contains('timer', case=False).any():
                    h_idx = i
                    break
            
            df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=h_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            besk_kol = df.columns[0]
            pris_kol = df.columns[7] # Kolonnen 'H' (pris)
            int_kols = [c for c in df.columns if "timer" in c.lower()]

            def rens(val):
                if pd.isna(val): return 0.0
                s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
                return float(s.replace(',', '.').strip()) if s else 0.0

            if int_kols:
                valgt_int = st.sidebar.selectbox("Aftale stop-punkt (Timer)", int_kols)
                valgt_t = int("".join(filter(str.isdigit, valgt_int)))
                
                # Din instruks: Kun services FØR stop-punktet
                hist_int = [c for c in int_kols if int("".join(filter(str.isdigit, c))) < valgt_t]
                
                # Find skillelinjen for væsker
                v_idx = df[df[besk_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                v_start = v_idx[0] if len(v_idx) > 0 else 9999
                
                tot_res, tot_vd, tot_arb = 0.0, 0.0, 0.0

                for i in hist_int:
                    m = df[i].astype(str).replace(['nan', 'None', ''], None).notna()
                    
                    # Reservedele (Før væsker)
                    res_df = df[(df.index < v_start) & m]
                    tot_res += (res_df[ordretype].apply(rens) * res_df['Antal'].apply(rens) * (1 + avance/100)).sum()
                    
                    # Væsker & Diverse (Efter væsker)
                    vd_df = df[(df.index > v_start) & m]
                    # Vi fjerner rækker der bare hedder "diverse" da vi selv tilføjer de 500 kr.
                    vd_df = vd_df[~vd_df[besk_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                    tot_vd += (vd_df[pris_kol].apply(rens) * vd_df['Antal'].apply(rens)).sum()
                    
                    # Din faste instruks: 500 DKK pr. service interval
                    tot_vd += FAST_DIVERSE_GEBYR
                    
                    # Arbejdsløn
                    m_arb = df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)
                    t_std = rens(df[m_arb][i].values[0]) if m_arb.any() else 0.0
                    tot_arb += (t_std * timepris)

                total_omk = tot_res + tot_vd + tot_arb
                cph = total_omk / valgt_t if valgt_t > 0 else 0

                # --- 5. VISNING ---
                t1, t2 = st.tabs(["💰 Beregning", "📜 Serviceaftale"])

                with t1:
                    st.subheader(f"Økonomi for 0 - {valgt_t} timer")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Reservedele", f"{tot_res:,.2f} kr.")
                    c2.metric("Væsker/Diverse", f"{tot_vd:,.2f} kr.")
                    c3.metric("Arbejdsløn", f"{tot_arb:,.2f} kr.")
                    
                    st.success(f"Beregnet timepris: **{cph:,.2f} DKK / time**")

                with t2:
                    st.markdown(f"""
                    <div style="padding: 30px; border: 1px solid #ccc; background-color: white; color: black; font-family: sans-serif;">
                        <h2 style="text-align: center; color: #367c2b;">SERVICEAFTALE</h2>
                        <hr>
                        <p><b>Forhandler:</b> {forhandler} <span style="float:right"><b>Dato:</b> {datetime.now().strftime('%d-%m-%Y')}</span></p>
                        <p><b>Kunde:</b> {kunde}</p>
                        <p><b>Maskine:</b> Deutz-Fahr {model_valg} | <b>Stelnummer:</b> {stelnummer}</p>
                        <br>
                        <p>Denne aftale dækker alle foreskrevne services frem til <b>{valgt_t} timer</b>.</p>
                        <div style="font-size: 1.3em; background-color: #f1f8e9; padding: 10px; border: 1px solid #367c2b; text-align: center;">
                            <b>FAST PRIS PR. DRIFTSTIME: {cph:,.2f} DKK (Ekskl. moms)</b>
                        </div>
                        <br><br>
                        <div style="display: flex; justify-content: space-between; margin-top: 50px;">
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Underskrift Forhandler</div>
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Underskrift Kunde (Digitalt: {kunde})</div>
                        </div>
                    </div>
                    """, unsafe

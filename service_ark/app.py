import streamlit as st
import pandas as pd
import os

# Konfiguration af siden
st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

# --- STYRING AF MAPPER ---
DATA_MAPPE = "service_ark"

# --- TOP SEKTION: LOGO OG TITEL ---
col1, col2 = st.columns([1, 3])
with col1:
    logo_path = os.path.join(DATA_MAPPE, "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        st.markdown("<h1 style='color: #d32f2f; margin: 0;'>DEUTZ-FAHR</h1>", unsafe_allow_html=True)

with col2:
    st.markdown("<h1 style='margin-bottom: 0; color: #367c2b;'>Serviceberegner</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-style: italic; color: gray;'>Professionelt overblik over akkumulerede serviceomkostninger</p>", unsafe_allow_html=True)

st.divider()

# Find filer
if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' blev ikke fundet.")
    modeller_raw = []
else:
    filer_i_mappe = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller_raw = sorted([f.replace('.csv', '') for f in filer_i_mappe])

if not modeller_raw:
    st.warning("Ingen CSV-filer fundet.")
else:
    # --- SIDEBAR ---
    st.sidebar.header("Indstillinger")
    model_visning = {f"Deutz-Fahr {m}": m for m in modeller_raw}
    valgt_visningsnavn = st.sidebar.selectbox("Vælg Traktormodel", list(model_visning.keys()))
    model_valg = model_visning[valgt_visningsnavn]
    
    st.sidebar.divider()
    timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750, step=25)
    ordretype = st.sidebar.radio("Pristype for filtre", ["Brutto", "Haste", "Uge", "Måned"])
    avance = st.sidebar.slider("Avance på reservedele (%)", 0, 50, 0)

    valgt_fil = os.path.join(DATA_MAPPE, f"{model_valg}.csv")

    try:
        # Indlæs data
        raw_df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
        header_row_index = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains('timer', case=False).any():
                header_row_index = i
                break
        
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        df.columns = [str(c).strip() for c in df.columns]
        beskrivelse_kol = df.columns[0]
        pris_kol_h = df.columns[7]
        
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        # Hjælpefunktion til tal-rensning
        def rens_til_tal(val):
            if pd.isna(val): return 0.0
            s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
            s = s.replace(',', '.').strip()
            try: return float(s)
            except: return 0.0

        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg serviceinterval (Beregner total omkostning op til dette timetal)", interval_kolonner)
            
            # Find alle forudgående intervaller (inklusiv det valgte)
            try:
                valgt_timer_tal = int("".join(filter(str.isdigit, valgt_interval)))
                forudgaaende_intervaller = []
                for col in interval_kolonner:
                    col_timer = int("".join(filter(str.isdigit, col)))
                    if col_timer <= valgt_timer_tal:
                        forudgaaende_intervaller.append(col)
            except:
                forudgaaende_intervaller = [valgt_interval]

            # Find sektions-indekser
            v_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            d_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
            v_start = v_idx[0] if len(v_idx) > 0 else 9999
            d_start = d_idx[0] if len(d_idx) > 0 else 9999

            # --- AKKUMULERET BEREGNING ---
            total_akkumuleret = 0.0
            total_reservedele = 0.0
            total_vaesker_diverse = 0.0
            total_arbejdslon = 0.0

            for interval in forudgaaende_intervaller:
                temp_df = df.copy()
                temp_df['markeret'] = temp_df[interval].astype(str).replace(['nan', 'None', ''], None).notna()
                
                # Reservedele for dette interval
                h_df = temp_df[(temp_df.index < v_start) & (temp_df['markeret'])].copy()
                if not h_df.empty:
                    priser = h_df[ordretype].apply(rens_til_tal)
                    antal = h_df['Antal'].apply(rens_til_tal)
                    total_reservedele += (priser * antal * (1 + avance/100)).sum()

                # Væsker & Diverse for dette interval
                vd_df = temp_df[(temp_df.index > v_start) & (temp_df['markeret'])].copy()
                vd_df = vd_df[~vd_df[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                if not vd_df.empty:
                    priser = vd_df[pris_kol_h].apply(rens_til_tal)
                    antal = vd_df['Antal'].apply(rens_til_tal)
                    total_vaesker_diverse += (priser * antal).sum()

                # Arbejdsløn for dette interval
                mask_arbejd = temp_df[beskrivelse_kol].astype(str).str.contains('Arbejd', case=False, na=False)
                if mask_arbejd.any():
                    t_timer = rens_til_tal(temp_df[mask_arbejd][interval].values[0])
                    total_arbejdslon += (t_timer * timepris)

            total_akkumuleret = total_reservedele + total_vaesker_diverse + total_arbejdslon
            pris_pr_time = total_akkumuleret / valgt_timer_tal if valgt_timer_tal > 0 else 0

            # --- VISNING ---
            st.subheader(f"Total vedligeholdelse: 0 - {valgt_timer_tal} timer")
            st.write(f"Beregningen inkluderer alle serviceintervaller op til og med {valgt_interval}: ({', '.join(forudgaaende_intervaller)})")

            # Oversigt over det VALGTE (nuværende) service (det du ser på skærmen)
            st.info(f"Nedenstående tabeller viser kun indholdet for det specifikke **{valgt_interval}** service.")
            
            # (Her følger tabel-visningen for det valgte interval som før...)
            # [Koden for dataframe visning af 'hoved', 'vaesker' og 'diverse' for kun valgt_interval]
            # ... (Forkortet her for overblik, men er med i din fulde app)
            
            # --- TOTALER (AKKUMULERET) ---
            st.divider()
            st.markdown(f"### Samlede akkumulerede omkostninger (0-{valgt_timer_tal} timer)")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Total Reservedele", f"{total_reservedele:,.2f} DKK")
            with c2: st.metric("Total Væsker/Diverse", f"{total_vaesker_diverse:,.2f} DKK")
            with c3: st.metric("Total Arbejdsløn", f"{total_arbejdslon:,.2f} DKK")
            with c4: 
                st.markdown(f"<div style='background-color: #367c2b; padding: 10px; border-radius: 5px; color: white; text-align: center;'>"
                            f"<small>AKKUMULERET TOTAL</small><br><strong><big>{total_akkumuleret:,.2f} DKK</big></strong></div>", unsafe_allow_html=True)

            # --- DRIFTSØKONOMI ---
            st.markdown("<br>", unsafe_allow_html=True)
            col_info, col_box = st.columns([2, 1])
            with col_info:
                st.markdown(f"### Reel serviceomkostning pr. driftstime")
                st.write(f"Dette tal er beregnet ved at tage samtlige serviceomkostninger fra traktoren var ny til den har kørt **{valgt_timer_tal} timer**, og dividere dem med det totale timetal.")
                st.write(f"Dette giver det mest præcise billede af maskinens faktiske vedligeholdelsesomkostning pr. time.")
            
            with col_box:
                st.markdown(f"<div style='border: 2px solid #367c2b; padding: 15px; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>"
                            f"<span style='color: #555; font-size: 0.9em; font-weight: bold;'>REEL PRIS PR. DRIFTSTIME</span><br>"
                            f"<span style='font-size: 1.6em; font-weight: bold; color: #367c2b;'>{pris_pr_time:,.2f} DKK/t</span>"
                            f"</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl: {e}")

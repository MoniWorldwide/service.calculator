import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

# Logo og Titel
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
with col2:
    st.title("Deutz-Fahr Serviceberegner")

# Find filer
nuværende_mappe = os.path.dirname(__file__)
filer_i_mappe = [f for f in os.listdir(nuværende_mappe) if f.endswith('.csv')]
modeller = [f.replace('.csv', '') for f in filer_i_mappe]

if not modeller:
    st.error("Ingen data fundet.")
else:
    model_valg = st.sidebar.selectbox("Vælg Traktormodel", sorted(modeller))
    timepris = st.sidebar.number_input("Din værkstedstimepris (DKK)", value=750)
    avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 20)

    valgt_fil = os.path.join(nuværende_mappe, f"{model_valg}.csv")

    try:
        # 1. Find den rigtige overskrifts-række
        raw_df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
        header_row_index = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains('timer', case=False).any():
                header_row_index = i
                break
        
        # 2. Indlæs med rigtig header
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        df.columns = [str(c).strip() for c in df.columns]
        beskrivelse_kol = df.columns[0] # Navnet på første kolonne (f.eks. 'Deutz-Fahr...')

        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Filtrer tomme rækker væk fra det valgte interval
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '')
            mask = df[valgt_interval].str.strip() != ""
            dele_fundet = df[mask].copy()

            if not dele_fundet.empty:
                # FUNKTION TIL AT DELE TABELLEN OP
                def vis_sektion(titel, data):
                    if not data.empty:
                        st.markdown(f"### {titel}")
                        vis_kol = [beskrivelse_kol, 'Reservedelsnr.', 'Brutto']
                        eksisterende = [k for k in vis_kol if k in data.columns]
                        st.dataframe(data[eksisterende], use_container_width=True, hide_index=True)

                # Find rækkenummer for "Væsker" og "Diverse" i den oprindelige dataframe
                # Vi bruger de rå data til at finde skillelinjerne
                vaesker_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                diverse_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index

                v_start = vaesker_idx[0] if len(vaesker_idx) > 0 else 999
                d_start = diverse_idx[0] if len(diverse_idx) > 0 else 999

                # Opdel de fundne dele baseret på deres oprindelige række-index
                hoved_dele = dele_fundet[dele_fundet.index < v_start]
                vaesker_dele = dele_fundet[(dele_fundet.index > v_start) & (dele_fundet.index < d_start)]
                diverse_dele = dele_fundet[dele_fundet.index > d_start]

                # Vis sektionerne
                vis_sektion("Filtre og Reservedele", hoved_dele)
                vis_sektion("Væsker (Olie, Kølervæske mm.)", vaesker_dele)
                vis_sektion("Diverse", diverse_dele)
                
                # Prisberegning (Total)
                if 'Brutto' in dele_fundet.columns:
                    priser = dele_fundet['Brutto'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    dele_fundet['Pris_Tal'] = pd.to_numeric(priser, errors='coerce').fillna(0)
                    total_dele = dele_fundet['Pris_Tal'].sum() * (1 + avance/100)
                    
                    st.divider()
                    st.metric("Samlet pris for alle dele (m. avance)", f"{total_dele:,.2f} DKK")
            else:
                st.info(f"Ingen dele fundet for {valgt_interval}")
        else:
            st.warning("Kunne ikke finde service-intervaller.")

    except Exception as e:
        st.error(f"Fejl: {e}")

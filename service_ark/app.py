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
        # 1. Indlæs hele filen råt først for at finde den rigtige overskrifts-række
        raw_df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
        
        # Vi leder efter den række, hvor der står "timer" i en af cellerne
        header_row_index = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains('timer', case=False).any():
                header_row_index = i
                break
        
        # 2. Indlæs nu filen igen med den rigtige række som header
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        
        # Rens kolonnenavne
        df.columns = [str(c).strip() for c in df.columns]

        # Find alle kolonner der indeholder "timer"
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Find rækker med indhold (x eller tal) i valgte kolonne
            # Vi fjerner rækker der er helt tomme eller kun indeholder 'None' / 'nan'
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '')
            mask = df[valgt_interval].str.strip() != ""
            dele_til_service = df[mask].copy()

            if not dele_til_service.empty:
                st.subheader(f"Dele til {valgt_interval} service")
                
                # Dynamisk visning af de første kolonner (Beskrivelse, Nr, Pris)
                vis_kol = [df.columns[0], 'Reservedelsnr.', 'Brutto']
                eksisterende = [k for k in vis_kol if k in dele_til_service.columns]
                st.dataframe(dele_til_service[eksisterende], use_container_width=True)
                
                # Prisberegning
                if 'Brutto' in dele_til_service.columns:
                    # Rens prisen for punktum og komma
                    priser = dele_til_service['Brutto'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    dele_til_service['Pris_Tal'] = pd.to_numeric(priser, errors='coerce').fillna(0)
                    
                    total_dele = dele_til_service['Pris_Tal'].sum() * (1 + avance/100)
                    
                    st.divider()
                    st.metric("Samlet pris for dele (m. avance)", f"{total_dele:,.2f} DKK")
            else:
                st.info(f"Ingen dele fundet for intervallet: {valgt_interval}")
        else:
            st.warning("Kunne ikke finde 'timer' i filen.")
            st.write("Første 5 rækker af filen:", raw_df.head())

    except Exception as e:
        st.error(f"Fejl ved læsning: {e}")

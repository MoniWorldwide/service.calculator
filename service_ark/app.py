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
    avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

    valgt_fil = os.path.join(nuværende_mappe, f"{model_valg}.csv")

    try:
        # Vi læser filen og springer de første rækker over for at finde overskrifterne
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', skiprows=1)
        
        # Rens data: Fjern tomme kolonner og rækker
        df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')

        # Find kolonner der indeholder "timer" (intervallerne)
        interval_kolonner = [c for c in df.columns if "timer" in str(c).lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Filtrer dele der skal bruges til det valgte interval (hvor der står 'x' eller tal)
            mask = df[valgt_interval].notna()
            dele_til_service = df[mask].copy()

            # Vis resultatet
            st.subheader(f"Nødvendige dele til {valgt_interval} service")
            
            # Formatering af priser (vi antager 'Brutto' er prisen)
            if 'Brutto' in dele_til_service.columns:
                dele_til_service['Brutto'] = pd.to_numeric(dele_til_service['Brutto'].str.replace('.', '').str.replace(',', '.'), errors='coerce')
                
                # Beregn priser
                pris_dele = dele_til_service['Brutto'].sum() * (1 + avance/100)
                
                st.dataframe(dele_til_service[['Deutz-Fahr ' + model_valg + ' Stage V', 'Reservedelsnr.', 'Brutto']], use_container_width=True)
                
                # Opsamling
                st.divider()
                st.metric("Samlet pris for reservedele (ekskl. moms)", f"{pris_dele:,.2f} DKK")
            else:
                st.dataframe(dele_til_service)
        else:
            st.warning("Kunne ikke finde service-intervaller i filen. Tjek om overskrifterne er korrekte.")

    except Exception as e:
        st.error(f"Fejl ved læsning: {e}")

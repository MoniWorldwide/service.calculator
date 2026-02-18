import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

# Overskrift og Logo
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
with col2:
    st.title("Deutz-Fahr Serviceberegner")

# Find alle CSV-filer i mappen
nuværende_mappe = os.path.dirname(__file__)
filer_i_mappe = [f for f in os.listdir(nuværende_mappe) if f.endswith('.csv')]

# Lav en pæn liste over modeller baseret på de filer der rent faktisk findes
modeller = [f.replace('.csv', '') for f in filer_i_mappe]

if ikke modeller:
    st.error("Ingen CSV-filer fundet i mappen! Sørg for at dine filer ender på .csv")
else:
    model_valg = st.selectbox("Vælg Traktormodel", sorted(modeller))
    valgt_fil = os.path.join(nuværende_mappe, f"{model_valg}.csv")

    try:
        # Vi prøver først med semikolon (standard dansk Excel CSV)
        # Vi bruger 'latin-1' encoding for at håndtere danske tegn
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1')
        
        # Hvis den kun finder 1 kolonne, er det nok fordi den bruger komma i stedet for semikolon
        if df.shape[1] <= 1:
            df = pd.read_csv(valgt_fil, sep=',', encoding='latin-1')

        st.success(f"Prisliste for {model_valg} er indlæst")
        
        # Vis tabellen
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Kunne ikke læse filen. Fejl: {e}")

# Debug info (kan fjernes senere)
with st.expander("Teknisk info (Se hvilke filer systemet ser)"):
    st.write("Mappe:", nuværende_mappe)
    st.write("Filer fundet:", filer_i_mappe)

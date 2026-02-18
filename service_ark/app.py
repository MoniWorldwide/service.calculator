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

# Lav en liste over modeller
modeller = [f.replace('.csv', '') for f in filer_i_mappe]

# HER VAR FEJLEN: 'ikke' er nu rettet til 'not'
if not modeller:
    st.error("Ingen CSV-filer fundet i mappen! Sørg for at dine filer ender på .csv")
else:
    model_valg = st.selectbox("Vælg Traktormodel", sorted(modeller))
    valgt_fil = os.path.join(nuværende_mappe, f"{model_valg}.csv")

    try:
        # Prøver at læse filen (Dansk Excel bruger ofte semikolon)
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1')
        
        if df.shape[1] <= 1:
            df = pd.read_csv(valgt_fil, sep=',', encoding='latin-1')

        st.success(f"Prisliste for {model_valg} er indlæst")
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Kunne ikke læse filen. Fejl: {e}")

# Debug info
with st.expander("Teknisk info"):
    st.write("Filer fundet:", filer_i_mappe)

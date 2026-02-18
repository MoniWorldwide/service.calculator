import streamlit as st
import pandas as pd

# Opsætning af traktormodeller og deres tilhørende CSV-filer
# Sørg for at filnavnene herunder matcher præcis det, du har uploadet til GitHub
model_filer = {
    "9340": "9340.csv",
    "8280": "8280.csv",
    "7250": "7250.csv",
    "6230": "6230.csv",
    "6210": "6210.csv",
    "6190": "6190.csv",
    "6165": "6165.csv",
    "6170.4": "6170.4.csv",
    "6150.4": "6150.4.csv",
    "6135C": "6135C.csv",
    "5125": "5125.csv",
    "5115D TTV": "5115D TTV.csv",
    "5105": "5105.csv",
    "5080 Keyline": "5080 Keyline.csv"
}

st.title("Deutz-Fahr Serviceberegner")

# Valg af model
model = st.selectbox("Vælg Traktormodel", list(model_filer.keys()))

# Indlæs data
try:
    # Vi læser CSV-filen. Vi antager den er semikolon-separeret (standard i DK Excel)
    df = pd.read_csv(model_filer[model], sep=';', skiprows=2)
    st.success(f"Data for {model} er indlæst!")
    st.write(df) # Viser dataene så du kan tjekke om de ser rigtige ud
except Exception as e:
    st.error(f"Kunne ikke finde eller læse filen {model_filer[model]}. Tjek filnavnet på GitHub.")
    st.info("Husk at filerne skal ligge i samme mappe som app.py")

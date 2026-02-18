import streamlit as st
import pandas as pd
import os

# Liste over modeller
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

model = st.selectbox("Vælg Traktormodel", list(model_filer.keys()))

# Find den mappe app.py ligger i
nuværende_mappe = os.path.dirname(__file__)
fil_sti = os.path.join(nuværende_mappe, model_filer[model])

try:
    # Vi prøver at læse filen
    df = pd.read_csv(fil_sti, sep=';', encoding='utf-8')
    st.success(f"Fundet! Her er data for {model}")
    st.dataframe(df)
except Exception as e:
    st.error(f"Fejl: Kan ikke finde filen '{model_filer[model]}'")
    st.info(f"Jeg leder i denne mappe: {nuværende_mappe}")
    
    # Vis hvilke filer der rent faktisk findes i mappen, så vi kan se fejlen
    st.write("Filer fundet i mappen:", os.listdir(nuværende_mappe))

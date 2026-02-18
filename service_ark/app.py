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
    # Sidebar menu
    model_valg = st.sidebar.selectbox("Vælg Traktormodel", sorted(modeller))
    timepris = st.sidebar.number_input("Din værkstedstimepris (DKK)", value=750)
    avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 20)

    valgt_fil = os.path.join(nuværende_mappe, f"{model_valg}.csv")

    try:
        # VI GØR NOGET NYT HER: 
        # Vi indlæser filen, men fortæller at overskrifterne ligger på række 1 (header=1)
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=1)
        
        # Rens kolonnenavne for mærkelige mellemrum
        df.columns = [str(c).strip() for c in df.columns]

        # Find alle kolonner der slutter på "timer"
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Find de rækker hvor der står noget i den valgte kolonne (f.eks. et 'x' eller et antal)
            mask = df[valgt_interval].notna() & (df[valgt_interval].astype(str).str.strip() != "")
            dele_til_service = df[mask].copy()

            if not dele_til_service.empty:
                st.subheader(f"Dele til {valgt_interval} service")
                
                # Vis tabellen med relevante kolonner
                vis_kol = [df.columns[0], 'Reservedelsnr.', 'Brutto']
                eksisterende = [k for k in vis_kol if k in dele_til_service.columns]
                st.dataframe(dele_til_service[eksisterende], use_container_width=True)
                
                # Simpel prisberegning (hvis Brutto er et tal)
                try:
                    # Rens prisen (fjerner punktum og laver komma til punktum)
                    dele_til_service['Pris_Tal'] = pd.to_numeric(
                        dele_til_service['Brutto'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), 
                        errors='coerce'
                    )
                    total_dele = dele_til_service['Pris_Tal'].sum() * (1 + avance/100)
                    st.metric("Samlet pris for dele (m. avance)", f"{total_dele:,.2f} DKK")
                except:
                    st.info("Kunne ikke beregne totalpris automatisk pga. prisformatet.")
            else:
                st.info(f"Der er ikke markeret nogen dele til {valgt_interval} i dit skema.")
        else:
            st.warning("Kunne ikke finde 'timer' i overskrifterne.")
            st.write("Jeg ser disse overskrifter:", list(df.columns))

    except Exception as e:
        st.error(f"Fejl ved læsning: {e}")

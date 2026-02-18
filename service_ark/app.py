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
    # --- SIDEBAR ---
    st.sidebar.header("Indstillinger")
    model_valg = st.sidebar.selectbox("Vælg Traktormodel", sorted(modeller))
    timepris = st.sidebar.number_input("Din værkstedstimepris (DKK)", value=750)
    ordretype = st.sidebar.radio("Vælg Ordretype (Pris for filtre)", ["Brutto", "Haste", "Uge", "Måned"])
    avance = st.sidebar.slider("Avance på RESERVEDELE (%)", 0, 50, 0)

    valgt_fil = os.path.join(nuværende_mappe, f"{model_valg}.csv")

    try:
        # 1. Find header række (hvor 'timer' optræder)
        raw_df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
        header_row_index = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains('timer', case=False).any():
                header_row_index = i
                break
        
        # 2. Indlæs data med korrekt header
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        df.columns = [str(c).strip() for c in df.columns]
        beskrivelse_kol = df.columns[0]
        
        # Kolonne H (index 7) er kilden til priser for Væsker og Diverse
        pris_kol_h = df.columns[7]
        
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Rens interval-kolonnen for at finde markerede rækker
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '').str.strip()
            
            # Find index for sektions-overskrifter
            v_start = df[df[beskrivelse_kol].astype(str).str.strip().str.lower() == 'væsker'].index.min()
            d_start = df[df[beskrivelse_kol].astype(str).str.strip().str.lower() == 'diverse'].index.min()
            
            # Håndter hvis sektioner mangler
            v_start = v_start if pd.notnull(v_start) else 9999
            d_start = d_start if pd.notnull(d_start) else 9999

            # Filtrer kun rækker der har en værdi i det valgte interval
            dele_fundet = df[df[valgt_interval] != ""].copy()

            if not dele_fundet.empty:
                def rens_til_tal(val):
                    if pd.isna(val) or str(val).strip() == "": return 0.0
                    return pd.to_numeric(str(val).replace('.', '').replace(',', '.'), errors='coerce') or 0.0

                def beregn_linje_data(row):
                    # Antal (Kolonne C)
                    antal = pd.to_numeric(str(row['Antal']).replace(',', '.'), errors='coerce') or 0.0
                    
                    if row.name < v_start:
                        # RESERVEDELE: Bruger valgt ordretype (Brutto/Haste etc) + avance
                        enhedspris = rens_til_tal(row[ordretype])
                        linje_total = antal * enhedspris * (1 + avance/100)
                    else:
                        # VÆSKER & DIVERSE: Bruger Kolonne H (ingen avance)
                        enhedspris = rens_til_tal(row[pris_kol_h])
                        linje_total = antal * enhedspris
                    
                    return pd.Series([enhedspris, linje_total])

                dele_fundet[['Enhedspris', 'Linje_Total']] = dele_fundet.apply(beregn_linje_data, axis=1)

                st.subheader(f"Serviceoversigt: {model_valg} - {valgt_interval}")

                # --- VISNING ---

                # 1. Filtre og Reservedele
                hoved = dele_fundet[dele_fundet.index < v_start]
                if not hoved.empty:
                    st.markdown("#### Filtre og Reservedele")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: hoved[beskrivelse_kol],
                        'Reservedelsnr.': hoved['Reservedelsnr.'],
                        'Enhedspris': hoved['Enhedspris'].map("{:,.2f}".format),
                        'Antal': hoved['Antal'],
                        'Total (inkl. avance)': hoved['Linje_Total'].map("{:,.2f} DKK".format)
                    }), use_container_width=True, hide_index=True)

                # 2. Væsker (Mellem 'Væsker' og 'Diverse')
                vaesker = dele_fundet[(dele_fundet.index > v_start) & (dele_fundet.index < d_start)]
                if not vaesker.empty:
                    st.markdown("#### Væsker (Olie, kølervæske osv.)")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: vaesker[beskrivelse_kol],
                        'Foreslået salgspris fra Univar': vaesker['Enhedspris'].map("{:,.2f}".format),
                        'Antal': vaesker['Antal'],
                        'Total': vaesker['Linje_Total'].map("{:,.2f} DKK".format)
                    }), use_container_width=True, hide_index=True)

                # 3. Diverse (Alt fra 'Diverse' overskriften og ned, undtagen selve overskrifts-teksten)
                diverse = dele_fundet[dele_fundet.index >= d_start]
                diverse = diverse[diverse[beskrivelse_kol].astype(str).str.strip().str.lower() != 'diverse']
                
                if not diverse.empty:
                    st.markdown("#### Diverse")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: diverse[beskrivelse_kol],
                        'Foreslået salgspris': diverse['Enhedspris'].map("{:,.2f}".format),
                        'Antal': diverse['Antal'],
                        'Total': diverse['Linje_Total'].map("{:,.2f} DKK".format)
                    }), use_container_width=True, hide_index=True)

                # SAMLET TOTAL
                st.divider()
                total_sum = dele_fundet['Linje_Total'].sum()
                st.metric("Samlet pris for dele (Ekskl. moms)", f"{total_sum:,.2f} DKK")
                st.caption(f"Prisberegning: Reservedele = {ordretype} + {avance}% avance. Væsker/Diverse = Kolonne H.")
                
            else:
                st.info(f"Ingen rækker fundet for {valgt_interval}")
        else:
            st.warning("Interval-kolonner ikke fundet.")

    except Exception as e:
        st.error(f"Fejl under indlæsning: {e}")

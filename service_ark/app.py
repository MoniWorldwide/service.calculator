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
    # --- SIDEBAR OPSÆTNING ---
    st.sidebar.header("Indstillinger")
    model_valg = st.sidebar.selectbox("Vælg Traktormodel", sorted(modeller))
    
    # Vælger til ordretype/pris
    ordretype = st.sidebar.radio(
        "Vælg Ordretype (Pris)",
        ["Brutto", "Haste", "Uge", "Måned"]
    )
    
    timepris = st.sidebar.number_input("Din værkstedstimepris (DKK)", value=750)
    avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

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
        beskrivelse_kol = df.columns[0]

        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Filtrer tomme rækker væk
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '')
            mask = df[valgt_interval].str.strip() != ""
            dele_fundet = df[mask].copy()

            if not dele_fundet.empty:
                # Funktion til at rense og beregne priser
                def rens_pris(kolonne_navn):
                    if kolonne_navn in dele_fundet.columns:
                        return pd.to_numeric(
                            dele_fundet[kolonne_navn].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), 
                            errors='coerce'
                        ).fillna(0)
                    return 0

                # Beregn den valgte pris med avance
                dele_fundet['Valgt_Pris_Tal'] = rens_pris(ordretype)
                total_dele = dele_fundet['Valgt_Pris_Tal'].sum() * (1 + avance/100)

                # FUNKTION TIL AT VISSE SEKTIONER
                def vis_sektion(titel, data):
                    if not data.empty:
                        st.markdown(f"#### {titel}")
                        # Vi viser Beskrivelse, Nr, og den valgte ordretype-pris
                        vis_kol = [beskrivelse_kol, 'Reservedelsnr.', ordretype]
                        eksisterende = [k for k in vis_kol if k in data.columns]
                        st.dataframe(data[eksisterende], use_container_width=True, hide_index=True)

                # Find rækkenummer for opdeling
                vaesker_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                diverse_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index

                v_start = vaesker_idx[0] if len(vaesker_idx) > 0 else 9999
                d_start = diverse_idx[0] if len(diverse_idx) > 0 else 9999

                # Opdel dele
                hoved_dele = dele_fundet[dele_fundet.index < v_start]
                vaesker_dele = dele_fundet[(dele_fundet.index > v_start) & (dele_fundet.index < d_start)]
                diverse_dele = dele_fundet[dele_fundet.index > d_start]

                # Vis sektionerne
                st.subheader(f"Serviceoversigt ({ordretype} priser)")
                vis_sektion("Filtre og Reservedele", hoved_dele)
                vis_sektion("Væsker", vaesker_dele)
                vis_sektion("Diverse", diverse_dele)
                
                # Samlet pris boks
                st.divider()
                st.metric(f"Samlet pris for dele ({ordretype} + {avance}% avance)", f"{total_dele:,.2f} DKK")
            else:
                st.info(f"Ingen dele fundet for {valgt_interval}")
        else:
            st.warning("Kunne ikke finde service-intervaller.")

    except Exception as e:
        st.error(f"Fejl: {e}")

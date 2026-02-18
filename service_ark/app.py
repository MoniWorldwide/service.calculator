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
        # 1. Indlæs data
        raw_df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
        header_row_index = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains('timer', case=False).any():
                header_row_index = i
                break
        
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        df.columns = [str(c).strip() for c in df.columns]
        beskrivelse_kol = df.columns[0]
        pris_kol_h = df.columns[7]
        
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            def rens_til_tal(val):
                s = str(val).replace('.', '').replace(',', '.').strip()
                try:
                    return float(s)
                except:
                    return 0.0

            # Find sektioner
            v_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            d_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
            v_start = v_idx[0] if len(v_idx) > 0 else 9999
            d_start = d_idx[0] if len(d_idx) > 0 else 9999

            # Tjek for "None"
            df['er_none'] = df[beskrivelse_kol].astype(str).str.strip().lower().isin(["none", "nan", ""])

            # --- DATA OPSAMLING ---
            # Reservedele og Væsker (skal være markeret i intervallet)
            df['markeret'] = df[valgt_interval].astype(str).replace(['nan', 'None'], '').str.strip() != ""
            
            hoved = df[(df.index < v_start) & (df['markeret']) & (~df['er_none'])].copy()
            vaesker = df[(df.index > v_start) & (df.index < d_start) & (df['markeret']) & (~df['er_none'])].copy()
            
            # Diverse (altid med hvis der er pris i H, undtagen arbejdsløn)
            diverse_all = df[df.index >= d_start].copy()
            diverse_all['pris_tjek'] = diverse_all[pris_kol_h].apply(rens_til_tal)
            
            # Find Arbejdsløn (vi leder efter 'arbejd' eller 'tid' i beskrivelsen)
            mask_arbejd = diverse_all[beskrivelse_kol].astype(str).str.contains('Arbejd|Tid', case=False, na=False)
            arbejd_row = diverse_all[mask_arbejd].copy()
            
            # Almindelig Diverse (alt det der ikke er arbejdsløn)
            diverse = diverse_all[(diverse_all['pris_tjek'] > 0) & (~diverse_all['er_none']) & (~mask_arbejd)].copy()
            diverse = diverse[~diverse[beskrivelse_kol].astype(str).str.contains('^diverse$', case=False, na=False)]

            # --- BEREGNINGER ---
            def apply_calc(data, kilde_pris, multiplier=1.0):
                if data.empty: return data
                data = data.copy()
                data['Enhed_Tal'] = data[kilde_pris].apply(rens_til_tal)
                data['Antal_Tal'] = data['Antal'].apply(rens_til_tal)
                data['Total_Tal'] = data['Antal_Tal'] * data['Enhed_Tal'] * multiplier
                return data

            hoved = apply_calc(hoved, ordretype, (1 + avance/100))
            vaesker = apply_calc(vaesker, pris_kol_h)
            diverse = apply_calc(diverse, pris_kol_h)

            # Beregn Arbejdsløn specifikt
            arbejdstimer = 0.0
            arbejd_total = 0.0
            if not arbejd_row.empty:
                # Vi henter antal timer fra selve interval-kolonnen (f.eks. 6,5 timer)
                arbejdstimer = rens_til_tal(arbejd_row[valgt_interval].values[0])
                arbejd_total = arbejdstimer * timepris

            # --- VISNING ---
            st.subheader(f"Serviceoversigt: {model_valg} - {valgt_interval}")

            if not hoved.empty:
                st.markdown("#### Filtre og Reservedele")
                st.dataframe(pd.DataFrame({
                    beskrivelse_kol: hoved[beskrivelse_kol],
                    'Reservedelsnr.': hoved['Reservedelsnr.'],
                    'Enhedspris': hoved['Enhed_Tal'].map("{:,.2f}".format),
                    'Antal': hoved['Antal'],
                    'Total (inkl. avance)': hoved['Total_Tal'].map("{:,.2f} DKK".format)
                }), use_container_width=True, hide_index=True)

            if not vaesker.empty:
                st.markdown("#### Væsker (Olie, kølervæske osv.)")
                st.dataframe(pd.DataFrame({
                    beskrivelse_kol: vaesker[beskrivelse_kol],
                    'Foreslået salgspris fra Univar': vaesker['Enhed_Tal'].map("{:,.2f}".format),
                    'Antal': vaesker['Antal'],
                    'Total': vaesker['Total_Tal'].map("{:,.2f} DKK".format)
                }), use_container_width=True, hide_index=True)

            if not diverse.empty:
                st.markdown("#### Diverse")
                st.dataframe(pd.DataFrame({
                    beskrivelse_kol: diverse[beskrivelse_kol],
                    'Foreslået salgspris': diverse['Enhed_Tal'].map("{:,.2f}".format),
                    'Antal': diverse['Antal'],
                    'Total': diverse['Total_Tal'].map("{:,.2f} DKK".format)
                }), use_container_width=True, hide_index=True)

            # --- TOTAL BEREGNING ---
            st.divider()
            dele_sum = hoved['Total_Tal'].sum() + vaesker['Total_Tal'].sum() + diverse['Total_Tal'].sum()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Dele i alt", f"{dele_sum:,.2f} DKK")
            with c2:
                st.metric("Arbejdsløn", f"{arbejd_total:,.2f} DKK", help=f"{arbejdstimer} timer á {timepris} DKK")
            with c3:
                st.metric("Samlet Total (Ekskl. moms)", f"{(dele_sum + arbejd_total):,.2f} DKK")

            st.caption(f"Arbejdsløn er beregnet som {arbejdstimer} timer (fundet i {valgt_interval}) gange din timepris på {timepris} DKK.")
            
    except Exception as e:
        st.error(f"Fejl: {e}")

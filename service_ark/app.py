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
                if pd.isna(val): return 0.0
                s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
                s = s.replace(',', '.').strip()
                try:
                    return float(s)
                except:
                    return 0.0

            # Find sektions-indekser
            v_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            d_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
            v_start = v_idx[0] if len(v_idx) > 0 else 9999
            d_start = d_idx[0] if len(d_idx) > 0 else 9999

            df['er_skjult'] = df[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "unnamed", ""])

            # --- DATA OPSAMLING ---
            df['markeret'] = df[valgt_interval].astype(str).replace(['nan', 'None'], '').str.strip() != ""
            
            # 1. SUM RESERVEDELE (Filtre osv.)
            hoved = df[(df.index < v_start) & (df['markeret']) & (~df['er_skjult'])].copy()
            
            # 2. VÆSKER
            vaesker = df[(df.index > v_start) & (df.index < d_start) & (df['markeret']) & (~df['er_skjult'])].copy()
            
            # 3. DIVERSE
            diverse_sektion = df[df.index >= d_start].copy()
            diverse = diverse_sektion[(~diverse_sektion['er_skjult'])].copy()
            diverse['pris_tjek'] = diverse[pris_kol_h].apply(rens_til_tal)
            diverse = diverse[(diverse['pris_tjek'] > 0) & (~diverse[beskrivelse_kol].astype(str).str.contains('^diverse$', case=False, na=False))].copy()

            # --- ARBEJDSTIMER (Sidebar styring) ---
            st.sidebar.divider()
            mask_arbejd = df[beskrivelse_kol].astype(str).str.contains('Arbejd', case=False, na=False)
            vejledende_timer = 0.0
            if mask_arbejd.any():
                timer_raw = df[mask_arbejd][valgt_interval].values[0]
                vejledende_timer = rens_til_tal(timer_raw)

            valgte_timer = st.sidebar.number_input(f"Arbejdstimer ({valgt_interval})", value=float(vejledende_timer), step=0.5)
            arbejd_total = valgte_timer * timepris

            # --- BEREGNINGER ---
            def apply_calc(data, kilde_kol, mult=1.0):
                if data.empty: return data
                data = data.copy()
                data['Enhed_Tal'] = data[kilde_kol].apply(rens_til_tal)
                data['Antal_Tal'] = data['Antal'].apply(rens_til_tal)
                data['Total_Tal'] = data['Antal_Tal'] * data['Enhed_Tal'] * mult
                return data

            hoved = apply_calc(hoved, ordretype, (1 + avance/100))
            vaesker = apply_calc(vaesker, pris_kol_h)
            diverse = apply_calc(diverse, pris_kol_h)

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
                    'Foreslået pris': vaesker['Enhed_Tal'].map("{:,.2f}".format),
                    'Antal': vaesker['Antal'],
                    'Total': vaesker['Total_Tal'].map("{:,.2f} DKK".format)
                }), use_container_width=True, hide_index=True)

            if not diverse.empty:
                st.markdown("#### Diverse")
                st.dataframe(pd.DataFrame({
                    beskrivelse_kol: diverse[beskrivelse_kol],
                    'Foreslået pris': diverse['Enhed_Tal'].map("{:,.2f}".format),
                    'Antal': diverse['Antal'],
                    'Total': diverse['Total_Tal'].map("{:,.2f} DKK".format)
                }), use_container_width=True, hide_index=True)

            # --- TOTALER MED SUM RESERVEDELE ---
            st.divider()
            sum_reservedele = hoved['Total_Tal'].sum() if not hoved.empty else 0
            sum_vaesker_diverse = (vaesker['Total_Tal'].sum() if not vaesker.empty else 0) + (diverse['Total_Tal'].sum() if not diverse.empty else 0)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("SUM Reservedele", f"{sum_reservedele:,.2f} DKK")
            with c2:
                st.metric("Væsker & Diverse", f"{sum_vaesker_diverse:,.2f} DKK")
            with c3:
                st.metric("Arbejdsløn", f"{arbejd_total:,.2f} DKK")
            with c4:
                total_alt = sum_reservedele + sum_vaesker_diverse + arbejd_total
                st.metric("SAMLET TOTAL", f"{total_alt:,.2f} DKK")

            st.caption(f"SUM Reservedele inkluderer {avance}% avance på {ordretype}-priser.")

    except Exception as e:
        st.error(f"Fejl: {e}")

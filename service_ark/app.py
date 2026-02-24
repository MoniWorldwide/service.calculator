import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURATION AF SIDEN ---
st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

# --- INDSTILLINGER ---
DATA_MAPPE = "service_ark"
FAST_DIVERSE_GEBYR = 500.0  # Din faste instruks

def find_logo():
    mulige_stier = ["logo.png", os.path.join(DATA_MAPPE, "logo.png")]
    for sti in mulige_stier:
        if os.path.exists(sti):
            return sti
    return None

# --- TOP SEKTION ---
col_l, col_r = st.columns([1, 3])
logo_sti = find_logo()

with col_l:
    if logo_sti:
        st.image(logo_sti, width=180)
    else:
        st.markdown("<h1 style='color: #d32f2f; margin: 0;'>DEUTZ-FAHR</h1>", unsafe_allow_html=True)

with col_r:
    st.markdown("<h1 style='margin-bottom: 0; color: #367c2b;'>Serviceberegner & Aftale</h1>", unsafe_allow_html=True)
    st.caption(f"Dato: {datetime.now().strftime('%d. %B %Y')}")

st.divider()

# --- DATABEHANDLING ---
if not os.path.exists(DATA_MAPPE):
    st.error(f"Fejl: Mappen '{DATA_MAPPE}' blev ikke fundet på serveren.")
else:
    filer = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller = sorted([f.replace('.csv', '') for f in filer])

    if modeller:
        # SIDEBAR INDSTILLINGER
        st.sidebar.header("1. Grunddata")
        model_valg = st.sidebar.selectbox("Vælg Traktormodel", modeller)
        timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750, step=25)
        ordretype = st.sidebar.radio("Pristype (Reservedele)", ["Brutto", "Haste", "Uge", "Måned"])
        avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

        st.sidebar.divider()
        st.sidebar.header("2. Kunde & Forhandler")
        forhandler = st.sidebar.text_input("Forhandler", "Indtast forhandler")
        kunde_navn = st.sidebar.text_input("Kundenavn")
        kunde_adr = st.sidebar.text_input("Adresse / By")
        stelnummer = st.sidebar.text_input("Stelnummer")

        # Indlæs den valgte model
        valgt_fil = os.path.join(DATA_MAPPE, f"{model_valg}.csv")
        try:
            df_raw = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
            h_idx = 0
            for i, row in df_raw.iterrows():
                if row.astype(str).str.contains('timer', case=False).any():
                    h_idx = i
                    break
            df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=h_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            besk_kol = df.columns[0]
            pris_kol_h = df.columns[7]
            int_kols = [c for c in df.columns if "timer" in c.lower()]

            def rens_tal(val):
                if pd.isna(val): return 0.0
                s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
                s = s.replace(',', '.').strip()
                try: return float(s)
                except: return 0.0

            if int_kols:
                st.sidebar.divider()
                st.sidebar.header("3. Aftaleperiode")
                valgt_int = st.sidebar.selectbox("Beregnes op til (Stop-punkt)", int_kols)
                valgt_t = int("".join(filter(str.isdigit, valgt_int)))
                
                # Find services før stop-punktet
                hist_int = [c for c in int_kols if int("".join(filter(str.isdigit, c))) < valgt_t]
                
                v_idx = df[df[besk_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                v_s = v_idx[0] if len(v_idx) > 0 else 9999
                
                t_res, t_vd, t_arb = 0.0, 0.0, 0.0
                for i in hist_int:
                    mask = df[i].astype(str).replace(['nan', 'None', ''], None).notna()
                    # Dele
                    res_df = df[(df.index < v_s) & mask]
                    t_res += (res_df[ordretype].apply(rens_tal) * res_df['Antal'].apply(rens_tal) * (1 + avance/100)).sum()
                    # Væsker/Diverse
                    vd_df = df[(df.index > v_s) & mask]
                    vd_df = vd_df[~vd_df[besk_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                    for _, r in vd_df.iterrows():
                        t_vd += rens_tal(r[pris_kol_h]) * rens_tal(r['Antal'])
                    t_vd += FAST_DIVERSE_GEBYR # Din faste tilføjelse pr. interval
                    # Arbejde
                    m_arb = df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)
                    t_std = rens_tal(df[m_arb][i].values[0]) if m_arb.any() else 0.0
                    t_arb += (t_std * timepris)

                total_omk = t_res + t_vd + t_arb
                pris_pr_t = total_omk / valgt_t if valgt_t > 0 else 0

                # --- VISNING ---
                tab_calc, tab_contract = st.tabs(["📊 Økonomisk Beregning", "📄 Serviceaftale"])

                with tab_calc:
                    st.subheader(f"Driftsøkonomi for Deutz-Fahr {model_valg}")
                    st.write(f"Beregningen dækker perioden fra **0 til {valgt_t} timer**.")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Reservedele Total", f"{t_res:,.2f} kr.")
                    c2.metric("Væsker & Diverse", f"{t_vd:,.2f} kr.")
                    c3.metric("Arbejdsløn", f"{t_arb:,.2f} kr.")

                    st.markdown(f"""
                        <div style="background-color: #f1f8e9; border: 2px solid #367c2b; padding: 25px; border-radius: 15px; text-align: center; margin-top: 20px;">
                            <h3 style="margin: 0; color: #2e7d32;">REEL PRIS PR. DRIFTSTIME</h3>
                            <h1 style="margin: 10px 0; color: #367c2b;">{pris_pr_t:,.2f} DKK / time</h1>
                            <small>(Ekskl. moms og brændstof)</small>
                        </div>
                    """, unsafe_allow_html=True)

                with tab_contract:
                    st.markdown(f"""
                    <div style="padding: 40px; border: 1px solid #ddd; background-color: white; color: black; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
                        <div style="text-align: right; color: #666;">Dato: {datetime.now().strftime('%d-%m-%Y')}</div>
                        <h2 style="color: #367c2b; text-align: center; margin-top: 0;">SERVICEAFTALE</h2>
                        <hr style="border: 1px solid #367c2b;">
                        <br>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="width: 50%; vertical-align: top;">
                                    <b>FORHANDLER:</b><br>{forhandler}<br><br>
                                    <b>MASKINE:</b><br>Deutz-Fahr {model_valg}<br>Stelnummer: {stelnummer}
                                </td>
                                <td style="width: 50%; vertical-align: top;">
                                    <b>KUNDE:</b><br>{kunde_navn}<br>{kunde_adr}
                                </td>
                            </tr>
                        </table>
                        <br>
                        <h4>Aftalens omfang</h4>
                        <p>Aftalen omfatter alle planlagte serviceeftersyn i henhold til fabrikantens forskrifter frem til traktoren har kørt <b>{valgt_t} timer</b>.</p>
                        <p>Prisen pr. driftstime er baseret på de akkumulerede omkostninger for alle serviceintervaller <u>før</u> stop-punktet på {valgt_t} timer.</p>
                        
                        <div style="background-color: #f9f9f9; padding: 15px; border-left: 5px solid #367c2b;">
                            <b>AFTALT TIMEPRIS: {pris_pr_t:,.2f} DKK (Ekskl. moms)</b>
                        </div>
                        <br><br>
                        <div style="display: flex; justify-content: space-between; margin-top: 50px;">
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Dato / Underskrift (Forhandler)</div>
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Dato / Underskrift (Kunde)</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("---")
                    st.subheader("Digital Godkendelse")
                    sig_forh = st.text_input("Bekræftet af (Forhandler)", value=forhandler)
                    sig_kunde = st.text_input("Bekræftet af (Kunde - indtast navn)")
                    
                    if st.button("Lås og Godkend Aftale"):
                        if sig_kunde:
                            st.success(f"Aftalen er hermed bekræftet af {sig_kunde} og {sig_forh}.")
                            st.balloons()
                            st.info("Tip: Tryk 'Ctrl + P' for at gemme aftalen som PDF eller printe den.")
                        else:
                            st.error("Kunden skal indtaste sit navn for at godkende aftalen.")

        except Exception as e:
            st.error(f"Der skete en fejl i beregningen: {e}")


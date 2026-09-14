"""
Solar PV Forecasting Dashboard (Streamlit)
============================================
Run with: streamlit run app.py

Upload a raw NREL/Himawari-format CSV (Year, Month, Day, Hour, Minute,
GHI, Temperature columns, with a 2-line metadata header) and this app
will build the timestamp, run the physics-based PV model (flat and,
if the columns are present, tilt-corrected), and forecast future
output with Prophet.
"""

import numpy as np
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet

st.set_page_config(page_title="Solar PV Forecasting", layout="centered")
st.title("Solar PV Forecasting Dashboard")

st.markdown("""
Upload a raw NREL/NLR Himawari-format CSV (with `Year`, `Month`, `Day`,
`Hour`, `Minute`, `GHI`, `Temperature` columns). This app will:
- Reconstruct the timestamp index
- Run a physics-based PV output model (flat panel)
- If `DNI`, `DHI`, and `Surface Albedo` are present, also compute a
  **tilt-corrected** estimate (tilted at your latitude)
- Forecast future output using Prophet
- Visualize actual vs. predicted output
""")

uploaded_file = st.file_uploader("Upload your NREL/Himawari CSV file", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, skiprows=2)
        df['Timestamp'] = pd.to_datetime(dict(
            year=df['Year'], month=df['Month'], day=df['Day'],
            hour=df['Hour'], minute=df['Minute']
        ))
        df = df.set_index('Timestamp')
    except (KeyError, ValueError) as e:
        st.error(
            f"Couldn't parse this file as a Himawari-format export "
            f"(missing or unexpected columns: {e}). Expected columns: "
            f"Year, Month, Day, Hour, Minute, GHI, Temperature, with a "
            f"2-line metadata header."
        )
        st.stop()

    st.subheader("Raw GHI Data")
    st.line_chart(df['GHI'])

    st.subheader("Physics-Based PV Model")
    area = st.number_input("PV Area (m²)", value=16.0, help="Total panel area (e.g. 10 panels x 1.6 m²)")
    efficiency = st.slider("Panel Efficiency (%)", min_value=1, max_value=30, value=18)
    derating = st.slider("Derating Factor", min_value=0.1, max_value=1.0, value=0.85,
                          help="Accounts for wiring, inverter, and other real-world losses")

    df['PV_output_kw'] = df['GHI'] * area * (efficiency / 100) * derating / 1000
    daily_energy = df['PV_output_kw'].resample('D').sum()

    st.line_chart(daily_energy)
    st.caption(f"Estimated total annual output (flat panel): {daily_energy.sum():,.0f} kWh")

    # ---------------------------------------------------------------
    # Tilt correction -- only if the required columns are present.
    # Uploaded files won't always have DNI/DHI/Surface Albedo (e.g. a
    # simpler dataset someone else built), so this degrades gracefully
    # instead of crashing when those columns are missing.
    # ---------------------------------------------------------------
    tilt_cols = {'DNI', 'DHI', 'Surface Albedo'}
    if tilt_cols.issubset(df.columns):
        st.subheader("Tilt-Corrected Model")
        latitude = st.number_input(
            "Site latitude (degrees)", value=22.5297,
            help="Panel tilt is set to match latitude -- the standard rule of thumb to maximize annual output"
        )
        lat_rad = np.radians(latitude)
        beta = lat_rad  # tilt angle = latitude

        doy = df.index.dayofyear.values
        decl_rad = np.radians(23.45 * np.sin(np.radians(360 * (284 + doy) / 365)))
        solar_time = df['Hour'].values + df['Minute'].values / 60
        hour_angle_rad = np.radians(15 * (solar_time - 12))

        cos_theta = (np.sin(decl_rad) * np.sin(lat_rad - beta) +
                     np.cos(decl_rad) * np.cos(hour_angle_rad) * np.cos(lat_rad - beta))
        cos_theta = np.clip(cos_theta, 0, None)

        albedo = np.nan_to_num(df['Surface Albedo'].values, nan=0.2)
        beam = df['DNI'].values * cos_theta
        diffuse = df['DHI'].values * (1 + np.cos(beta)) / 2
        reflected = df['GHI'].values * albedo * (1 - np.cos(beta)) / 2
        df['POA'] = np.clip(beam + diffuse + reflected, 0, None)

        df['PV_output_kw_tilted'] = df['POA'] * area * (efficiency / 100) * derating / 1000
        daily_tilted = df['PV_output_kw_tilted'].resample('D').sum()

        gain_pct = (daily_tilted.sum() / daily_energy.sum() - 1) * 100
        col1, col2 = st.columns(2)
        col1.metric("Flat panel (annual)", f"{daily_energy.sum():,.0f} kWh")
        col2.metric("Tilted panel (annual)", f"{daily_tilted.sum():,.0f} kWh", f"{gain_pct:+.1f}%")

        compare_df = pd.DataFrame({'Flat': daily_energy, 'Tilted': daily_tilted})
        st.line_chart(compare_df)

        monthly = df.groupby(df.index.month)[['GHI', 'POA']].mean()
        monthly['pct_change'] = (monthly['POA'] / monthly['GHI'] - 1) * 100
        st.bar_chart(monthly['pct_change'])
        st.caption("Change in irradiance from tilting, by month (%) -- typically strongly "
                   "positive in winter and slightly negative at the summer peak near the equator.")
    else:
        st.info(
            "Tilt-corrected model skipped: this file doesn't have the "
            "`DNI`, `DHI`, and `Surface Albedo` columns needed for it. "
            "The flat-panel model above still works fine."
        )

    # ---------------------------------------------------------------
    # Clear Sky Index -- only if Clearsky GHI is present
    # ---------------------------------------------------------------
    if 'Clearsky GHI' in df.columns:
        st.subheader("Clear Sky Index")
        csi = (df['GHI'] / df['Clearsky GHI'].replace(0, np.nan)).resample('D').mean()
        st.line_chart(csi)
        st.caption(f"Annual mean: {csi.mean():.2f} -- how much of the cloud-free potential "
                   f"actually reached the ground each day (1.0 = perfectly clear).")

    st.subheader("Forecast with Prophet")
    n_days = len(daily_energy)
    if n_days < 30:
        st.warning(
            f"Only {n_days} days of data uploaded — Prophet's forecast "
            f"will be unreliable with this little history. At least a "
            f"few months is recommended."
        )

    df_prophet = daily_energy.reset_index()
    df_prophet.columns = ['ds', 'y']

    with st.spinner("Fitting forecast model..."):
        m = Prophet(yearly_seasonality=(n_days >= 730))
        m.fit(df_prophet)

        forecast_days = st.slider("Days to forecast ahead", 1, 30, 14)
        future = m.make_future_dataframe(periods=forecast_days, freq='D')
        forecast = m.predict(future)

    fig, ax = plt.subplots(figsize=(10, 4))
    m.plot(forecast, ax=ax)
    ax.set_ylabel("PV Output (kWh/day)")
    st.pyplot(fig)

    st.success("Forecast complete!")
    st.download_button(
        "Download Forecast CSV",
        forecast.to_csv(index=False),
        file_name="pv_forecast.csv"
    )
else:
    st.info("Upload a CSV to get started.")

"""
Solar PV Forecasting Dashboard (Streamlit)
============================================
Run with: streamlit run app.py

Upload a raw NREL/Himawari-format CSV (Year, Month, Day, Hour, Minute,
GHI, Temperature columns, with a 2-line metadata header) and this app
will build the timestamp, run the physics-based PV model, and forecast
future output with Prophet.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet

st.set_page_config(page_title="Solar PV Forecasting", layout="centered")
st.title("Solar PV Forecasting Dashboard")

st.markdown("""
Upload a raw NREL Himawari-format CSV (with `Year`, `Month`, `Day`,
`Hour`, `Minute`, `GHI`, `Temperature` columns). This app will:
- Reconstruct the timestamp index
- Run a physics-based PV output model
- Forecast future output using Prophet
- Visualize actual vs. predicted output
""")

uploaded_file = st.file_uploader("Upload your NREL/Himawari CSV file", type=["csv"])

if uploaded_file:
    # The real NREL Himawari export has a 2-line metadata header before
    # the actual column headers -- skip it the same way the analysis
    # notebook does. If a differently-formatted file is uploaded this
    # will raise a clear error rather than silently misreading columns.
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
    st.caption(f"Estimated total annual output: {daily_energy.sum():,.0f} kWh")

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
        # Yearly seasonality needs ~2 years of history to estimate
        # reliably; disable it automatically on shorter uploads rather
        # than silently producing an unstable fit.
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

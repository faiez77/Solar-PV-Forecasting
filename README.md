# ☀️ Solar PV Forecasting Using Satellite Data & ML

This project forecasts the power output of a **photovoltaic (PV) solar system** using:
- **Real-world satellite data** from the Himawari-8 API (NREL)
- A **physics-based PV model** to simulate generation
- Time-series forecasting models like **Prophet** 
- An interactive **dashboard using Streamlit or Jupyter Widgets**

---

## 📌 Project Goals

- 🔍 Analyze solar resource data from satellite-based measurements (GHI, temperature, etc.)
- 🧠 Forecast future PV output to assist in planning and reduce **O&M costs**
- ⚙️ Build a light-weight model pipeline that combines **domain knowledge of PV** with **ML forecasting**
- 📊 Provide a visual interface for easy exploration and predictions

---

## 📁 Dataset Used

- **Source**: [NREL Himawari 2016–2020 Dataset](https://developer.nrel.gov/docs/solar/nsrdb/himawari-download/)
- **Access Method**: Via API key from [NREL Developer Portal](https://developer.nrel.gov/signup/)
- **Data Type**: 
  - GHI (Global Horizontal Irradiance)
  - Temperature
  - Pressure
  - Timestamps (10-min interval)
- **Format**: CSV files per year per location

---

## ⚙️ Features Implemented

### ✅ Physics-Based PV Output Model
- Converts **GHI → PV Output** using efficiency, temperature coefficients
- Simple but effective approximation for forecasting

### ✅ Prophet Forecasting
- Trained on calculated PV output
- Produces hourly/day-ahead predictions with confidence intervals

### ✅ (Optional) LSTM Model *(under refinement)*
- Deep learning model for time-series
- Needs further tuning (was experimental)

### ✅ Dashboard UI
- Created using:
  - `Streamlit` for browser app *(or)*
  - Jupyter Notebook Widgets for inline dashboards
- Upload your CSV → forecast → view graph of predictions

---

## 📸 Sample Screenshots

> Add 1–2 screenshots showing:
- Prophet prediction vs actual
- Streamlit or Jupyter dashboard with CSV upload

---

## 🛠 How to Run

### A. Run Notebook
1. Open `pv.ipynb` in Jupyter Notebook
2. Follow cells to download, process, forecast, and visualize

### B. Run Dashboard in Jupyter
1. Open `pv_dashboard_jupyter.ipynb`
2. Upload your Himawari CSV
3. Forecast and explore interactively

### C. (Optional) Run Streamlit App
```bash
streamlit run app.py

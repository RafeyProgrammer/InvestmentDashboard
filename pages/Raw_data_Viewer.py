import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from io import StringIO

st.set_page_config(page_title="Raw Data Explorer", layout="wide")
st.title("🧪 Raw Order History Explorer")
st.caption("This page checks your account for a matching date-range export file before requesting a new one.")

# Access keys from your sidebar
API_KEY = st.sidebar.text_input("Confirm API Key for Export", type="password")
SEC_KEY = st.sidebar.text_input("API Secret", type="password")

# 🧠 Initialize our Session Memory so it persists across screen interactions
if "df_raw_data" not in st.session_state:
    st.session_state.df_raw_data = None

# 📅 1. Date Range Input Interface
st.subheader("🗓️ Select Ledger Coverage Window")
col_d1, col_d2 = st.columns(2)
with col_d1:
    # Defaults to Jan 1st of current year
    start_date = st.date_input("Start Date", value=datetime(datetime.now().year, 1, 1))
with col_d2:
    # Defaults to today
    end_date = st.date_input("End Date", value=datetime.now())

# Format the dates into strings to match the filename structure
# e.g., "2026-01-01"
start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

if st.button("🚀 Fetch History (Smart Cache Scan)"):
    if not API_KEY:
        st.error("Please enter your API Key in the sidebar.")
    elif start_date > end_date:
        st.error("Error: Start Date cannot be after End Date.")
    else:
        export_url = "https://live.trading212.com/api/v0/history/exports"

        # ─── STEP 2: SCAN SERVER FOR AN MATCHING FILE NAME ───
        with st.spinner("Scanning Trading 212 logs for an existing file with this date range..."):
            if SEC_KEY:
                status_response = requests.get(export_url, auth=(API_KEY, SEC_KEY))
            else:
                status_response = requests.get(export_url, headers={"Authorization": API_KEY})

        existing_report = None
        if status_response.status_code == 200:
            reports_list = status_response.json()

            # Loop through history looking for matching 'from' and 'to' date values inside the attributes
            for report in reports_list:
                # We extract the metadata date limits the API explicitly tracks
                time_from = report.get("timeFrom", "")
                time_to = report.get("timeTo", "")
                status = report.get("status")

                # Check if this specific item matches our desired calendar boundaries
                if time_from.startswith(start_str) and time_to.startswith(
                        end_str) and status == "Finished" and report.get("downloadLink"):
                    existing_report = report
                    break

        # ─── STEP 3: LOAD LOCAL LINK OR REQUEST A FRESH EXPORT ───
        download_link = None

        if existing_report:
            st.success(f"🎯 Found an existing finished export matching `{start_str}` to `{end_str}`! Bypassing queue.")
            download_link = existing_report.get("downloadLink")
        else:
            st.info(f"ℹ️ No active file matches `{start_str}` to `{end_str}`. Requesting fresh server compile...")

            # Use the user's explicit selections inside the generation payload
            payload = {
                "dataIncluded": {
                    "includeDividends": True,
                    "includeInterest": True,
                    "includeOrders": True,
                    "includeTransactions": True
                },
                "timeFrom": f"{start_str}T00:00:00Z",
                "timeTo": f"{end_str}T23:59:59Z"
            }

            if SEC_KEY:
                response = requests.post(export_url, auth=(API_KEY, SEC_KEY), json=payload)
            else:
                headers = {"Authorization": API_KEY, "Content-Type": "application/json"}
                response = requests.post(export_url, headers=headers, json=payload)

            if response.status_code in [200, 201]:
                report_info = response.json()
                report_id = report_info.get("reportId")
                st.info(f"New Export Triggered successfully. ID: `{report_id}`")

                # Asynchronous checking loop
                status = "Requested"
                max_attempts = 15
                attempt = 0
                status_container = st.empty()

                while not download_link and status not in ["Finished", "Failed"] and attempt < max_attempts:
                    attempt += 1
                    time.sleep(5)
                    status_container.text(
                        f"⏳ Syncing with server... State: '{status}' (Attempt {attempt}/{max_attempts})")

                    if SEC_KEY:
                        poll_response = requests.get(export_url, auth=(API_KEY, SEC_KEY))
                    else:
                        poll_response = requests.get(export_url, headers={"Authorization": API_KEY})

                    if poll_response.status_code == 200:
                        for r in poll_response.json():
                            if r.get("reportId") == report_id:
                                status = r.get("status")
                                download_link = r.get("downloadLink")
                                break
                    else:
                        break
            else:
                st.error(f"Failed to initiate export: Error {response.status_code} - {response.text}")

        # ─── STEP 4: DOWNLOAD STREAMS DIRECTLY TO THE APPS MEMORY ───
        if download_link:
            with st.spinner("Downloading and writing CSV into dynamic data workspace..."):
                csv_response = requests.get(download_link)
                if csv_response.status_code == 200:
                    st.session_state.df_raw_data = pd.read_csv(StringIO(csv_response.text))
                    st.success("🎉 Data successfully synced and ready for evaluation!")
                else:
                    st.error("Failed to parse data out of storage link destination.")

# ─── 🏗️ THE COMBINED CLEANING WORKSPACE (LIVES OUTSIDE THE FETCH BUTTON) ───
if st.session_state.df_raw_data is not None:
    # Always keep a pristine backup copies of your source data structure
    df_raw = st.session_state.df_raw_data

    st.markdown("---")
    st.subheader("🧹 Advanced Ledger Workspace Editor")
    st.caption("Prune unwanted columns and remove transaction types simultaneously before computing math models.")

    # Define your default target behavior column for tracking rows
    TARGET_COL = 'Action'

    # 🔒 1. Open the Integrated Operations Form
    with st.form("integrated_data_editor_form"):
        col_left, col_right = st.columns(2)

        # --- LEFT SIDE: ROW REMOVAL ENGINE ---
        with col_left:
            st.markdown("#### 🪵 Row Selection Filter")
            if TARGET_COL in df_raw.columns:
                unique_row_types = df_raw[TARGET_COL].dropna().unique().tolist()

                rows_to_drop = st.multiselect(
                    "Select Row Types to completely DROP:",
                    options=unique_row_types,
                    placeholder="e.g., Interest on cash, Deposit..."
                )
            else:
                st.caption(f"ℹ️ `{TARGET_COL}` column missing. Row filtration disabled.")
                rows_to_drop = []

        # --- RIGHT SIDE: COLUMN DROP ENGINE ---
        with col_right:
            st.markdown("#### ✂️ Column View Filter")
            # Pull down a clean list of every data structural field header in the CSV file
            all_available_columns = df_raw.columns.tolist()

            columns_to_drop = st.multiselect(
                "Select Columns to completely ELIMINATE:",
                options=all_available_columns,
                placeholder="e.g., File ID, FX Fees, Exchange Rate..."
            )

        # 🔘 2. Form Submit Control Action
        submit_all_edits = st.form_submit_button("⚡ Execute Matrix Cleaning Pipeline", type="primary",
                                                 use_container_width=True)

    # ─── ⚡ 3. EXECUTING PANDAS DATA TRANSFORMATIONS ───
    # Initialize our modified container frame
    df_cleaned = df_raw.copy()

    if submit_all_edits:
        # A. Handle Row Pruning Operations
        if rows_to_drop and TARGET_COL in df_cleaned.columns:
            df_cleaned = df_cleaned[~df_cleaned[TARGET_COL].isin(rows_to_drop)]

        # B. Handle Column Drop Operations (axis=1 targets vertical attributes)
        if columns_to_drop:
            df_cleaned = df_cleaned.drop(columns=columns_to_drop, errors='ignore')

    # ─── 📊 DISPLAY DYNAMIC METRICS SUMMARY ───
    st.markdown("### 📈 Pipeline Alteration Metrics Summary")
    m_col1, m_col2, m_col3 = st.columns(3)

    with m_col1:
        st.metric("Source Structure Size", f"{df_raw.shape[0]} R x {df_raw.shape[1]} C")

    with m_col2:
        rows_dropped = len(df_raw) - len(df_cleaned)
        st.metric(
            label="Rows Removed",
            value=rows_dropped,
            delta=f"-{rows_dropped} lines" if rows_dropped > 0 else "0 changes",
            delta_color="inverse"
        )

    with m_col3:
        cols_dropped = len(df_raw.columns) - len(df_cleaned.columns)
        st.metric(
            label="Columns Erased",
            value=cols_dropped,
            delta=f"-{cols_dropped} categories" if cols_dropped > 0 else "0 changes",
            delta_color="inverse"
        )

    # Render the final presentation dataframe view grid
    st.subheader("📊 Cleaned Workspace Output Grid")
    if not df_cleaned.empty:
        st.dataframe(df_cleaned, use_container_width=True)
    else:
        st.warning("⚠️ Warning: Your active filter configuration completely emptied out the dataset matrix.")
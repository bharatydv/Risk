import streamlit as st
import pandas as pd
from datetime import timedelta

st.set_page_config(page_title="Risk Analyzer", layout="centered")

st.title("Risk Violation Analyzer")

st.markdown("Upload trade history file to check risk violations.")

uploaded_file = st.file_uploader("Upload CSV or Excel File", type=["csv", "xlsx"])

risk_percent = st.number_input("Risk %", value=2.0)
analyze_button = st.button("Analyze")

if uploaded_file and analyze_button:

    # Read file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Column detection
    ticket_col = None
    time_col = None
    profit_col = None
    balance_col = None

    for col in df.columns:
        name = col.lower()
        if "ticket" in name:
            ticket_col = col
        if "opentime" in name:
            time_col = col
        if "profit" in name and "total" not in name:
            profit_col = col
        if "balance" in name:
            balance_col = col

    # Data prep
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df[profit_col] = pd.to_numeric(df[profit_col], errors='coerce')
    df[balance_col] = pd.to_numeric(df[balance_col], errors='coerce')

    df = df.dropna(subset=[time_col, profit_col])
    df = df.sort_values(time_col).reset_index(drop=True)

    starting_balance = df[balance_col].dropna().iloc[0]
    risk_amount = starting_balance * (risk_percent / 100)

    st.write("Starting Balance:", starting_balance)
    st.write("Risk Amount:", risk_amount)

    # Rule 1
    single_trade_violation = df[df[profit_col] <= -risk_amount]

    # Rule 2
    time_window = 10
    combined_violations = []

    i = 0
    while i < len(df):
        start_time = df.loc[i, time_col]
        group = [i]

        j = i + 1
        while j < len(df):
            if (df.loc[j, time_col] - start_time) <= timedelta(minutes=time_window):
                group.append(j)
                j += 1
            else:
                break

        group_df = df.loc[group]
        losing_trades = group_df[group_df[profit_col] < 0]
        combined_loss = losing_trades[profit_col].sum()

        if combined_loss <= -risk_amount:
            combined_violations.append({
                "Start Time": group_df[time_col].iloc[0],
                "End Time": group_df[time_col].iloc[-1],
                "Combined Loss": combined_loss,
                "Trade IDs": list(losing_trades[ticket_col])
            })

        i += 1

    st.subheader("Single Trade Violations")
    if len(single_trade_violation) > 0:
        st.dataframe(single_trade_violation[[ticket_col, time_col, profit_col]])
    else:
        st.write("No Single Trade Violations")

    st.subheader("Combined Violations")
    combined_df = pd.DataFrame(combined_violations)

    if len(combined_df) > 0:
        st.dataframe(combined_df)

        csv = combined_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Report",
            data=csv,
            file_name='violations_report.csv',
            mime='text/csv'
        )
    else:
        st.write("No Combined Violations")
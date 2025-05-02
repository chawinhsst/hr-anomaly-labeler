import streamlit as st
import pandas as pd
from utils import parse_csv, parse_tcx, parse_fit
from streamlit_plotly_events import plotly_events
import plotly.graph_objs as go

st.set_page_config(page_title="Multi-Select Anomaly Marker", layout="wide")

st.title("📈 Anomaly Labeling Tool")
st.write("Upload your heart rate file (.csv, .tcx, or .fit) to label anomalies interactively.")

uploaded_file = st.file_uploader("📄 Upload your CSV, TCX, or FIT file", type=["csv", "tcx", "fit"])

if uploaded_file is not None:
    file_type = uploaded_file.name.split(".")[-1].lower()

    if file_type == "csv":
        df = parse_csv(uploaded_file)
    elif file_type == "tcx":
        df = parse_tcx(uploaded_file)
    elif file_type == "fit":
        df = parse_fit(uploaded_file)
    else:
        st.error("Unsupported file type.")
        st.stop()

    df['Time'] = pd.to_datetime(df['Time'], errors='coerce', utc=True).dt.tz_localize(None)
    df.dropna(subset=['Time', 'HeartRate'], inplace=True)
    df.sort_values("Time", inplace=True)
    df.reset_index(drop=True, inplace=True)

    for col in df.columns:
        if col != "Time":
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if "Speed" in df.columns:
        df["Speed"] *= 3.6

    if "df" not in st.session_state or len(st.session_state.df) != len(df):
        df["Label"] = 0
        st.session_state.df = df
    else:
        df["Label"] = st.session_state.df["Label"]
        st.session_state.df = df

df = st.session_state.get("df")

if df is not None:
    optional_params = [col for col in df.columns if col not in ['Time', 'HeartRate', 'Label']]
    selected_params = []

    if optional_params:
        st.sidebar.subheader("📌 Additional Parameters")
        selected_params = st.sidebar.multiselect(
            "Select additional parameters to show",
            options=optional_params
        )

    st.sidebar.subheader("🪟 Slicing Window")
    slicing_window = st.sidebar.number_input(
        "Number of points per chart", min_value=0, value=0, step=1,
        help="Set how many points you want per mini-chart. If 0, show full chart."
    )

    color_palette = [
        "#2ca02c", "#ff7f0e", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]

    def create_figure(sub_df):
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=sub_df['Time'], y=sub_df['HeartRate'],
            mode='lines+markers',
            name='HeartRate',
            marker=dict(color='blue'),
            yaxis='y1'
        ))

        anomalies = sub_df[sub_df['Label'] == 1]
        fig.add_trace(go.Scatter(
            x=anomalies['Time'], y=anomalies['HeartRate'],
            mode='markers',
            name='Anomalies',
            marker=dict(color='red', size=10, symbol='x'),
            yaxis='y1'
        ))

        for i, param in enumerate(selected_params):
            fig.add_trace(go.Scatter(
                x=sub_df['Time'], y=sub_df[param],
                mode='lines+markers',
                name=param,
                marker=dict(color=color_palette[i % len(color_palette)]),
                yaxis='y2'
            ))

        right_yaxis_title = selected_params[0] if len(selected_params) == 1 else (
            "Selected Parameters" if selected_params else "")

        fig.update_layout(
            title="Click on points to select anomalies",
            xaxis_title="Time",
            yaxis=dict(
                title="Heart Rate",
                titlefont=dict(color="blue"),
                tickfont=dict(color="blue"),
            ),
            yaxis2=dict(
                title=right_yaxis_title,
                titlefont=dict(color="green"),
                tickfont=dict(color="green"),
                overlaying="y",
                side="right"
            ),
            margin=dict(l=40, r=40, t=40, b=40),
            autosize=True,
            height=450,
            plot_bgcolor="white",
            paper_bgcolor="white"
        )
        return fig

    if slicing_window > 0:
        num_chunks = (len(df) + slicing_window - 1) // slicing_window
        st.subheader(f"🪟 Displaying {num_chunks} sliced charts:")

        for i in range(num_chunks):
            start_idx = i * slicing_window
            end_idx = min((i + 1) * slicing_window, len(df))
            sliced_df = df.iloc[start_idx:end_idx]

            st.markdown(f"### Chunk {i+1} — Points {start_idx+1} to {end_idx}")
            fig = create_figure(sliced_df)
            selected_points = plotly_events(
                fig, click_event=True, hover_event=False, select_event=True, key=f"plot_{i}"
            )

            if selected_points:
                for pt in selected_points:
                    clicked_time = pd.to_datetime(pt['x'], utc=True).tz_localize(None)
                    idx = (df['Time'] - clicked_time).abs().idxmin()
                    df.at[idx, 'Label'] = 0 if df.at[idx, 'Label'] == 1 else 1
                st.session_state.df = df
                st.rerun()

    else:
        fig = create_figure(df)
        selected_points = plotly_events(
            fig, click_event=True, hover_event=False, select_event=True
        )

        if selected_points:
            for pt in selected_points:
                clicked_time = pd.to_datetime(pt['x'], utc=True).tz_localize(None)
                idx = (df['Time'] - clicked_time).abs().idxmin()
                df.at[idx, 'Label'] = 0 if df.at[idx, 'Label'] == 1 else 1
            st.session_state.df = df
            st.rerun()

    st.subheader("🔍 Labeled Anomalies")
    labeled_anomalies = df[df['Label'] == 1].reset_index()

    if not labeled_anomalies.empty:
        st.dataframe(labeled_anomalies.drop(columns=["index"]), use_container_width=True)

        selected_to_remove = st.multiselect(
            "Select row indices to remove anomaly labels:",
            options=labeled_anomalies["index"].tolist()
        )

        if selected_to_remove and st.button("Remove Selected"):
            for idx in selected_to_remove:
                df.at[idx, "Label"] = 0
            st.session_state.df = df
            st.rerun()
    else:
        st.info("No anomalies labeled yet.")

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📅 Download Labeled CSV",
        data=csv,
        file_name='labeled_heart_rate.csv',
        mime='text/csv'
    )
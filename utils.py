# utils.py
import pandas as pd
import plotly.graph_objs as go
import xml.etree.ElementTree as ET
from fitparse import FitFile
import io

def create_figure(df, selected_params):
    color_palette = [
        "#2ca02c", "#ff7f0e", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]

    fig = go.Figure()

    # HeartRate trace
    fig.add_trace(go.Scatter(
        x=df['Time'], y=df['HeartRate'],
        mode='lines+markers',
        name='HeartRate',
        marker=dict(color='blue'),
        yaxis='y1'
    ))

    # Anomalies trace
    anomalies = df[df['Label'] == 1]
    fig.add_trace(go.Scatter(
        x=anomalies['Time'], y=anomalies['HeartRate'],
        mode='markers',
        name='Anomalies',
        marker=dict(color='red', size=10, symbol='x'),
        yaxis='y1'
    ))

    # Optional parameters
    for i, param in enumerate(selected_params):
        if param in df.columns:
            fig.add_trace(go.Scatter(
                x=df['Time'], y=df[param],
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

def parse_csv(file):
    return pd.read_csv(file)

def parse_tcx(file):
    ns = {
        'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
        'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
    }
    tree = ET.parse(file)
    root = tree.getroot()
    data = []

    for tp in root.findall('.//tcx:Trackpoint', ns):
        time = tp.find('tcx:Time', ns)
        hr = tp.find('tcx:HeartRateBpm/tcx:Value', ns)
        pos = tp.find('tcx:Position', ns)
        alt = tp.find('tcx:AltitudeMeters', ns)
        dist = tp.find('tcx:DistanceMeters', ns)

        speed = tp.find('tcx:Extensions/ns3:TPX/ns3:Speed', ns)
        cadence = tp.find('tcx:Extensions/ns3:TPX/ns3:RunCadence', ns)
        watts = tp.find('tcx:Extensions/ns3:TPX/ns3:Watts', ns)

        try:
            latitude = float(pos.find('tcx:LatitudeDegrees', ns).text) if pos is not None and pos.find('tcx:LatitudeDegrees', ns) is not None else None
            longitude = float(pos.find('tcx:LongitudeDegrees', ns).text) if pos is not None and pos.find('tcx:LongitudeDegrees', ns) is not None else None
        except:
            latitude = None
            longitude = None

        row = {
            'Time': time.text if time is not None else None,
            'HeartRate': hr.text if hr is not None else None,
            'Latitude': latitude,
            'Longitude': longitude,
            'Altitude': alt.text if alt is not None else None,
            'Distance': dist.text if dist is not None else None,
            'Speed': speed.text if speed is not None else None,
            'RunCadence': cadence.text if cadence is not None else None,
            'Watts': watts.text if watts is not None else None
        }
        data.append(row)

    return pd.DataFrame(data)

def parse_fit(file):
    fitfile = FitFile(io.BytesIO(file.read()))
    records = []

    for record in fitfile.get_messages('record'):
        data = record.get_values()
        row = {}

        if 'timestamp' in data:
            row['Time'] = pd.to_datetime(data['timestamp'])
        if 'heart_rate' in data:
            row['HeartRate'] = data['heart_rate']
        if 'position_lat' in data and data['position_lat'] is not None:
            row['Latitude'] = data['position_lat'] * (180 / 2**31)
        if 'position_long' in data and data['position_long'] is not None:
            row['Longitude'] = data['position_long'] * (180 / 2**31)
        if 'altitude' in data:
            row['Altitude'] = data['altitude']
        if 'distance' in data:
            row['Distance'] = data['distance']
        if 'speed' in data:
            row['Speed'] = data['speed']
        if 'cadence' in data:
            row['RunCadence'] = data['cadence']
        if 'power' in data:
            row['Watts'] = data['power']
        if 'temperature' in data:
            row['Temperature'] = data['temperature']

        if 'Time' in row:
            records.append(row)

    return pd.DataFrame(records)

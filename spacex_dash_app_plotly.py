import requests
import pandas as pd
import io
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.express as px

URL_outcomes = 'https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/IBM-DS0321EN-SkillsNetwork/datasets/dataset_part_2.csv'
response_outcomes = requests.get(URL_outcomes)
spacex_df = pd.read_csv(io.StringIO(response_outcomes.text))

site_mapping = {
    'CCAFS SLC-40': 'CCAFS SLC 40',
    'KSC LC-39A': 'KSC LC 39A',
    'VAFB SLC-4E': 'VAFB SLC 4E'
}
spacex_df['LaunchSite'] = spacex_df['LaunchSite'].replace(site_mapping)

ALLOWED_SITES = [
    'CCAFS SLC 40', 
    'VAFB SLC 4E', 
    'KSC LC 39A'
]

spacex_df = spacex_df[spacex_df['LaunchSite'].isin(ALLOWED_SITES)]

success_rates = spacex_df.groupby('LaunchSite')['Class'].agg(['count', 'mean'])
success_rates.columns = ['Total Launches', 'Success Rate']
success_rates['Success Rate'] = success_rates['Success Rate'] * 100
success_rates = success_rates.sort_values('Success Rate', ascending=False)

max_payload = spacex_df['PayloadMass'].max()
min_payload = spacex_df['PayloadMass'].min()

best_site = success_rates.index[0]

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1('SpaceX Launch Analysis Dashboard', style={'textAlign': 'center', 'color': '#503D36', 'fontSize': 40}),
    
    html.Div([
        html.Label("Payload Mass Range (Kg):"),
        dcc.RangeSlider(
            id='payload-slider',
            min=int(min_payload),
            max=int(max_payload),
            step=500,
            marks={
                int(min_payload): str(int(min_payload)),
                2500: '2,500',
                5000: '5,000',
                7500: '7,500',
                int(max_payload): str(int(max_payload))
            },
            value=[int(min_payload), int(max_payload)]
        )
    ], style={'margin': '20px'}),
    
    html.Div([
        dcc.Graph(id='payload-success-scatter')
    ]),
    
    html.Div([
        html.H3(f'Launch Outcomes for {best_site}', style={'textAlign': 'center'}),
        dcc.Graph(
            id='best-site-pie',
            figure=px.pie(
                values=spacex_df[spacex_df['LaunchSite'] == best_site]['Class'].value_counts().values,
                names=['Success', 'Failure'],  # Switched order
                title=f'Launch Outcomes for {best_site}',
                color_discrete_sequence=['#4ECDC4', '#FF6B6B'] 
            )
        )
    ]),
    
    html.Div([
        html.H3('Launch Success Count by Site', style={'textAlign': 'center'}),
        dcc.Graph(
            id='site-success-pie',
            figure=px.pie(
                values=spacex_df.groupby('LaunchSite')['Class'].sum().values,
                names=spacex_df.groupby('LaunchSite')['Class'].sum().index,
                title='Launch Success Count by Site',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
        )
    ])
])

@app.callback(
    Output('payload-success-scatter', 'figure'),
    Input('payload-slider', 'value')
)
def update_scatter(payload_range):
    filtered_df = spacex_df[
        (spacex_df['PayloadMass'] >= payload_range[0]) & 
        (spacex_df['PayloadMass'] <= payload_range[1])
    ]
    
    fig = px.scatter(
        filtered_df, 
        x='PayloadMass', 
        y='Class',
        color='LaunchSite',
        title='Payload Mass vs Launch Success',
        labels={'PayloadMass': 'Payload Mass (kg)', 'Class': 'Launch Success'},
        hover_data=['LaunchSite', 'BoosterVersion']
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)

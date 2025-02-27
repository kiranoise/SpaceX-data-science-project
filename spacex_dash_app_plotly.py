import requests
import pandas as pd
import io
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go

URL_sites = 'https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/IBM-DS0321EN-SkillsNetwork/datasets/spacex_launch_geo.csv'
response_sites = requests.get(URL_sites)
spacex_sites_df = pd.read_csv(io.StringIO(response_sites.text))

URL_outcomes = 'https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/IBM-DS0321EN-SkillsNetwork/datasets/dataset_part_2.csv'
response_outcomes = requests.get(URL_outcomes)
launch_outcomes_df = pd.read_csv(io.StringIO(response_outcomes.text))

print("Sites DataFrame Columns:", spacex_sites_df.columns.tolist())
print("Outcomes DataFrame Columns:", launch_outcomes_df.columns.tolist())

if 'LaunchSite' in launch_outcomes_df.columns and 'Launch Site' not in launch_outcomes_df.columns:
    launch_outcomes_df = launch_outcomes_df.rename(columns={'LaunchSite': 'Launch Site'})

if 'Class' in launch_outcomes_df.columns and 'class' not in launch_outcomes_df.columns:
    launch_outcomes_df = launch_outcomes_df.rename(columns={'Class': 'class'})

if 'LaunchSite' in spacex_sites_df.columns and 'Launch Site' not in spacex_sites_df.columns:
    spacex_sites_df = spacex_sites_df.rename(columns={'LaunchSite': 'Launch Site'})

if 'Class' in spacex_sites_df.columns and 'class' not in spacex_sites_df.columns:
    spacex_sites_df = spacex_sites_df.rename(columns={'Class': 'class'})

spacex_df = pd.merge(
    spacex_sites_df, 
    launch_outcomes_df, 
    on='Launch Site', 
    how='left',
    suffixes=('', '_y')
)

if 'class' in spacex_sites_df.columns and 'class' in launch_outcomes_df.columns:
    spacex_df['class'] = spacex_df['class_y'].fillna(spacex_df['class'])
    spacex_df = spacex_df.drop(columns=['class_y'])

success_rates = spacex_df.groupby('Launch Site')['class'].agg(['count', 'mean'])
success_rates.columns = ['Total Launches', 'Success Rate']
success_rates['Success Rate'] = success_rates['Success Rate'] * 100
success_rates = success_rates.sort_values('Success Rate', ascending=False)

max_payload = spacex_df['Payload Mass (kg)'].max()
min_payload = spacex_df['Payload Mass (kg)'].min()

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1('SpaceX Launch Records Dashboard', style={'textAlign': 'center', 'color': '#503D36', 'fontSize': 40}),
    
    html.Div([
        html.Label('Select Launch Site:'),
        dcc.Dropdown(
            id='site-dropdown',
            options=[{'label': 'All Sites', 'value': 'ALL'}] + [{'label': site, 'value': site} for site in spacex_df['Launch Site'].unique()],
            value='ALL',
            placeholder="Select a Launch Site here",
            searchable=True,
            className='dropdown'
        )
    ]),
    
    html.Div([
        html.Br(),
        dcc.Graph(id='success-pie-chart')
    ]),
    
    html.Div([
        html.Br(),
        html.Label("Payload Range (Kg):"),
        dcc.RangeSlider(
            id='payload-slider',
            min=0,
            max=10000,
            step=1000,
            marks={0: '0', 2500: '2500', 5000: '5000', 7500: '7500', 10000: '10000'},
            value=[min_payload, max_payload]
        )
    ]),
    
    html.Div([
        html.Br(),
        dcc.Graph(id='success-payload-scatter-chart')
    ]),
    
    html.Div([
        html.Br(),
        dcc.Graph(id='booster-version-chart')
    ]),
    
    html.Div([
        html.Br(),
        html.H3('Site Success Rate Comparison', style={'textAlign': 'center'}),
        dcc.Graph(
            id='success-rate-bar',
            figure=px.bar(
                success_rates.reset_index(),
                x='Launch Site',
                y='Success Rate',
                color='Success Rate',
                color_continuous_scale='Viridis',
                title='Success Rate by Launch Site',
                labels={'Launch Site': 'Launch Site', 'Success Rate': 'Success Rate (%)'}
            )
        )
    ])
])

@app.callback(
    Output(component_id='success-pie-chart', component_property='figure'),
    Input(component_id='site-dropdown', component_property='value')
)
def get_pie_chart(entered_site):
    if entered_site == 'ALL':
        successful_launches = spacex_df[spacex_df['class'] == 1]['Launch Site'].value_counts()
        fig = px.pie(
            names=successful_launches.index,
            values=successful_launches.values,
            title='Successful Launches by Launch Site',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        return fig
    else:
        site_data = spacex_df[spacex_df['Launch Site'] == entered_site]
        success_count = site_data['class'].value_counts().sort_index()
        fig = px.pie(
            names=['Failure', 'Success'] if len(success_count) > 1 else ['Success'] if 1 in success_count.index else ['Failure'],
            values=success_count.values,
            title=f'Launch Outcomes for {entered_site}',
            color_discrete_sequence=['#ff9999', '#66b3ff']
        )
        return fig

@app.callback(
    Output(component_id='success-payload-scatter-chart', component_property='figure'),
    [Input(component_id='site-dropdown', component_property='value'), 
     Input(component_id="payload-slider", component_property="value")]
)
def get_scatter_chart(entered_site, payload_range):
    filtered_df = spacex_df[(spacex_df['Payload Mass (kg)'] >= payload_range[0]) & 
                         (spacex_df['Payload Mass (kg)'] <= payload_range[1])]
    
    if entered_site == 'ALL':
        fig = px.scatter(
            filtered_df, 
            x='Payload Mass (kg)', 
            y='class',
            color='Launch Site',
            symbol='class',
            size='Payload Mass (kg)',
            size_max=15,
            hover_data=['Launch Site', 'Payload Mass (kg)', 'Booster Version'],
            title='Payload vs. Success for All Launch Sites',
            labels={'class': 'Success (1=Yes, 0=No)'}
        )
        return fig
    else:
        site_df = filtered_df[filtered_df['Launch Site'] == entered_site]
        fig = px.scatter(
            site_df, 
            x='Payload Mass (kg)', 
            y='class',
            color='Booster Version',
            symbol='class',
            size='Payload Mass (kg)',
            size_max=15,
            hover_data=['Payload Mass (kg)', 'Booster Version'],
            title=f'Payload vs. Success for {entered_site}',
            labels={'class': 'Success (1=Yes, 0=No)'}
        )
        return fig

@app.callback(
    Output(component_id='booster-version-chart', component_property='figure'),
    [Input(component_id='site-dropdown', component_property='value'), 
     Input(component_id="payload-slider", component_property="value")]
)
def get_booster_chart(entered_site, payload_range):
    filtered_df = spacex_df[(spacex_df['Payload Mass (kg)'] >= payload_range[0]) & 
                         (spacex_df['Payload Mass (kg)'] <= payload_range[1])]
    
    if entered_site != 'ALL':
        filtered_df = filtered_df[filtered_df['Launch Site'] == entered_site]
    
    fig = go.Figure()
    
    for site in filtered_df['Launch Site'].unique():
        site_data = filtered_df[filtered_df['Launch Site'] == site]
        
        successful_data = site_data[site_data['class'] == 1]
        if not successful_data.empty:
            fig.add_trace(go.Scatter(
                x=successful_data['Payload Mass (kg)'],
                y=successful_data['Booster Version'],
                mode='markers',
                name=f'{site} - Successful',
                marker=dict(color='green', size=10, opacity=0.7)
            ))
        
        unsuccessful_data = site_data[site_data['class'] == 0]
        if not unsuccessful_data.empty:
            fig.add_trace(go.Scatter(
                x=unsuccessful_data['Payload Mass (kg)'],
                y=unsuccessful_data['Booster Version'],
                mode='markers',
                name=f'{site} - Unsuccessful',
                marker=dict(color='red', size=10, opacity=0.7)
            ))
    
    site_label = entered_site if entered_site != 'ALL' else 'All Sites'
    
    fig.update_layout(
        title=f'Payload Mass vs Booster Version for {site_label}',
        xaxis_title='Payload Mass (kg)',
        yaxis_title='Booster Version',
        height=600
    )
    
    fig.update_layout(
        updatemenus=[{
            'buttons': [
                {'label': 'All Payload Ranges', 'method': 'relayout', 'args': [{'xaxis.range': [None, None]}]},
                {'label': '0-2000 kg', 'method': 'relayout', 'args': [{'xaxis.range': [0, 2000]}]},
                {'label': '2000-4000 kg', 'method': 'relayout', 'args': [{'xaxis.range': [2000, 4000]}]},
                {'label': '4000-6000 kg', 'method': 'relayout', 'args': [{'xaxis.range': [4000, 6000]}]}
            ],
            'direction': 'down',
            'showactive': True,
            'x': 0.1,
            'y': 1.1,
        }]
    )
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)

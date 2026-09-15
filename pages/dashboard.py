import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, ctx, dcc, html
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify
from plotly.subplots import make_subplots

from globals import (
    APP_TITLE,
    HELP_TEXT_DASHBOARD,
    PAGE_HEADER_STYLE,
    create_help_button,
    decode_text,
    encode_text,
    get_rater_selection,
)

dash.register_page(__name__, name='Dashboard', order=5, title=APP_TITLE)

# Page layout

layout = html.Div([

    # Header
    html.H2('Dashboard', style=PAGE_HEADER_STYLE), 
    html.Br(),
    
    # Content
    dbc.Row([

        # Graph
        dbc.Col([
            dcc.Graph(id='dashboard-graph', config={'staticPlot': True}, style={'visibility': 'hidden'})
        ], width=9),
        
        # Sidebar with info and tools
        dbc.Col([
            html.Div(id='client-info-container'),
            html.Br(),
            html.Div('Measures', className='mb-2'),
            html.Div(id='measure-switches-container'),
            html.Br(),
            html.Div(id='rater-switches-container'),
            html.Br(),
            html.Div('Y-Axis'),
            dmc.Select(
                id='yaxis-select',
                value='Normalized',
                data=[
                    {'value': 'Normalized'},
                    {'value': 'Raw'}
                ],
                w=200,
                persistence=True,
                allowDeselect=False
            ),
            html.Br(),
            html.Div('X-Axis'),
            dmc.Select(
                id='xaxis-select',
                value='Day',
                data=[
                    {'value': 'Day'},
                    {'value': 'Session'}
                ],
                w=200,
                persistence=True,
                allowDeselect=False
            )
        ]),
    ]),
    create_help_button(HELP_TEXT_DASHBOARD)
])

# Callbacks

# Display client info
@callback(
    Output('client-info-container', 'children'),
    Input('client-store', 'data'),
)
def display_client_info(client_info):
    avatar = dmc.Avatar(DashIconify(icon='ion:person-sharp'), color='grey', radius='xl')
    client_info = client_info[0]
    client_id = client_info['ID'] if client_info['ID'] else 'Client'
    client_age = f"{client_info['Age']} years" if client_info['Age'] else None
    client_gender = f"{client_info['Gender']}"
    client_focus = f"{client_info['Focus']}"
    style_info = {'margin-left': '55px', 'fontSize': 14}

    return dmc.Paper([
        dmc.Group(children=[avatar, html.Div(client_id)]),
        html.Div(client_age, style=style_info),
        html.Div(client_gender, style=style_info),
        html.Div(client_focus, style=style_info)
    ])

@callback(
    Output('measure-switches-container', 'children'),
    Input('measures-store', 'data'),
)
def create_measure_switches(measures_data):
    measures_data = [measure for measure in measures_data if measure['Name'] != 'New Measure']
    
    if not measures_data:
        return html.Div('No measures defined')
    
    switches = []
    for measure in measures_data:
        encoded_name = encode_text(measure['Name'])
        switch = dmc.Switch(
            id={'type': 'measure-switch', 'index': encoded_name},
            label=measure['Name'],
            size='sm',
            color=measure.get('Color', 'grey'),
            mb=10,
            checked=measure['SelectMeasure'],
        )
        switches.append(switch)
    return html.Div(switches)

@callback(
    Output('rater-switches-container', 'children'),
    Input('measures-store', 'data'),
)
def create_rater_switches(measures_data):
    measures_data = [measure for measure in measures_data if measure['Name'] != 'New Measure']
    if not measures_data:
        return html.Div('')
    
    rater_selection = get_rater_selection(measures_data)
    sorted_raters = sorted(rater_selection.keys())
    
    switches = []
    for rater in sorted_raters:
        switch = dmc.Switch(
            id={'type': 'rater-switch', 'index': rater},
            label=rater,
            size='sm',
            color='grey',
            mb=10,
            checked=rater_selection[rater],
        )
        switches.append(switch)
    return html.Div([html.Div('Rater', className='mb-2'), *switches])

@callback(
    Output('measures-store', 'data', allow_duplicate=True),
    Input({'type': 'rater-switch', 'index': ALL}, 'checked'),
    Input({'type': 'measure-switch', 'index': ALL}, 'checked'),
    State({'type': 'rater-switch', 'index': ALL}, 'id'),
    State({'type': 'measure-switch', 'index': ALL}, 'id'),
    State('measures-store', 'data'),
    prevent_initial_call=True
)
def handle_switch_changes(rater_states, measure_states, rater_ids, measure_ids, measures_data):
    trigger = ctx.triggered_id
    if not measures_data or trigger is None:
        raise PreventUpdate
    
    # Get the trigger context information
    trigger_type = trigger.get('type')
    trigger_index = trigger.get('index')
    trigger_value = ctx.triggered[0]['value']

    if trigger_index:
        trigger_index = decode_text(trigger_index)

    rater_selection = get_rater_selection(measures_data)
    measures_data_updated = []

    # Handle rater switch change
    if trigger_type == 'rater-switch':
        if rater_selection.get(trigger_index) == trigger_value:
            raise PreventUpdate
        
        rater_selection[trigger_index] = trigger_value

        for measure in measures_data:
            measure_copy = measure.copy()
            measure_copy['SelectMeasure'] = rater_selection[measure['Rater']]
            measure_copy['SelectRater'] = rater_selection[measure['Rater']]
            measures_data_updated.append(measure_copy)
        
    # Handle measure switch change
    elif trigger_type == 'measure-switch':
        for measure in measures_data:
            measure_copy = measure.copy()
            if measure_copy['Name'] == trigger_index:
                if measure_copy['SelectMeasure'] == trigger_value:
                    raise PreventUpdate
                measure_copy['SelectMeasure'] = trigger_value
            measure_copy['SelectRater'] = False
            measures_data_updated.append(measure_copy)
    
    return measures_data_updated if measures_data_updated else dash.no_update

# Dashboard graph
@callback(
    Output('dashboard-graph', 'figure'),
    Output('dashboard-graph', 'style'),
    Input('sessions-store', 'data'),
    Input('measures-store', 'data'),
    Input('practices-store', 'data'),
    Input('yaxis-select', 'value'),
    Input('xaxis-select', 'value')
)
def create_dashboard_graph(sessions_data, measures_data, practices_data, yaxis_select, xaxis_select):
    
    # Manage data
    practices_data = [practice for practice in practices_data if practice['Name'] != 'New Practice']
    num_practices = len(practices_data)

    # Determine heigth of subplots and figure
    measures_height = 300
    practice_height_per_item = 20
    total_practice_height = max(practice_height_per_item, num_practices * practice_height_per_item)
    total_height = measures_height + total_practice_height
    
    # Calculate height ratios
    practice_height_ratio = num_practices * 0.75 if num_practices else 0.75
    measures_height_ratio = 4
    
    # Create base figure with subplots
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=('Measures', 'Practices'),
        row_heights=[measures_height_ratio, practice_height_ratio],
    )

    # Convert sessions data to DataFrame and prepare x-axis
    df = pd.DataFrame(sessions_data)
    x_values = _prepare_x_axis(df, xaxis_select)

    # Handle measures
    selected_measures = [measure['Name'] for measure in measures_data if measure.get('SelectMeasure', False)]
    if not selected_measures:
        fig.add_trace(
            go.Scattergl(
                x=[1,1],
                y=[0,100],
                marker=dict(color='rgba(0, 0, 0, 0)'),
            ),
            row=1,
            col=1,
            )

    # Normalize data if required
    if yaxis_select == 'Normalized':
        df = _normalize_measures(df, measures_data, selected_measures)

    # Add measure traces
    _add_measure_traces(fig, df, measures_data, selected_measures, x_values, xaxis_select)

    # Handle practices
    _add_practice_traces(fig, df, practices_data, x_values, xaxis_select)

    # Update layout and axes
    _update_figure_layout(fig, yaxis_select, xaxis_select, df, x_values, total_height)
    
    return fig, {'visibility': 'visible'}

def _prepare_x_axis(df, xaxis_select):
    '''Prepare x-axis values based on selection'''
    if xaxis_select == 'Day':
        df['Date'] = pd.to_datetime(df['session_date'])
        first_session_date = df['Date'].min()
        df['Days'] = (df['Date'] - first_session_date).dt.days + 1

        return df['Days']

    return df['session_number']

def _normalize_measures(df, measures_data, selected_measures):
    '''Normalize selected measures'''
    df_normalized = df.copy()
    for measure in selected_measures:
        measure_data = next(m for m in measures_data if m['Name'] == measure)
        min_value = measure_data['Min']
        max_value = measure_data['Max'] if measure_data['Type'] == 'Scale' else df[measure].max()
        df_normalized[measure] = (df[measure] - min_value) / (max_value - min_value)
    return df_normalized

def _add_measure_traces(fig, df, measures_data, selected_measures, x_values, xaxis_select):
    '''Add measurement traces to the figure'''
    for measure in selected_measures:
        if measure in df.columns:
            measure_data = next(m for m in measures_data if m['Name'] == measure)
            if df[measure].isna().all():
                fig.add_trace(
                    go.Scattergl(
                        x=[1,1],
                        y=[measure_data['Min'],measure_data['Max']],
                        marker=dict(color='rgba(0, 0, 0, 0)'),
                    ),
                    row=1,
                    col=1,
                )
            else:
                fig.add_trace(
                    go.Scattergl(
                        name=measure,
                        x=x_values,
                        y=df[measure],
                        line=dict(color=measure_data.get('Color', 'grey')),
                        marker=dict(size=10),
                        mode='lines+markers',
                        connectgaps=True,
                        customdata=[xaxis_select] * len(x_values),
                        hovertemplate='%{customdata}: %{x}<br>Value: %{y:.2f}'
                    ),
                    row=1,
                    col=1,
                )                        

def _add_practice_traces(fig, df, practices_data, x_values, xaxis_select):
    '''Add practice traces to the figure'''
    if not practices_data:
        fig.add_trace(
            go.Scattergl(
                x=x_values,
                y=[None] * len(x_values),
                line=dict(color='lightgrey'),
                marker=dict(size=10),
                mode='lines+markers',
                showlegend=False,
            ),
            row=2,
            col=1,
        )

    for i_practice, practice in enumerate(practices_data[::-1]):
        if practice['Name'] in df.columns:
            y_values = [i_practice if val else None for val in df[practice['Name']]]
            fig.add_trace(
                go.Scattergl(
                    name=practice['Name'],
                    x=x_values,
                    y=y_values,
                    line=dict(color='lightgrey'),
                    marker=dict(size=10),
                    mode='lines+markers',
                    connectgaps=False,
                    customdata=[xaxis_select] * len(x_values),
                    hovertemplate='%{customdata}: %{x}'
                ),
                row=2,
                col=1,
            )

def _update_figure_layout(fig, yaxis_select, xaxis_select, df, x_values, total_height):
    '''Update the figure's layout and axes'''
    fig.update_layout(
        plot_bgcolor='white',
        showlegend=False,
        margin=dict(l=80, r=0, t=40, b=0),
        height=total_height + 100,
    )

    # Update measures subplot
    _update_measures_axis(fig, yaxis_select == 'Normalized')

    # Update practices subplot
    _update_practices_axis(fig, df)

    # Update x-axis
    _update_x_axis(fig, xaxis_select, x_values)

    # Adjust annotation positions
    for annotation in fig['layout']['annotations']:
        annotation['x'] = 0
        annotation['xanchor'] = 'right'
        if annotation['text'] == 'Measures':
            annotation['y'] = annotation['y'] + annotation['y'] * 0.04

def _update_measures_axis(fig, normalized):
    '''Update the measures (top) subplot y-axis'''
    fig.update_yaxes(
        row=1,
        col=1,
        ticks='outside',
        tickcolor='white',
        showgrid=True,
        gridcolor='lightgray',
        gridwidth=1,
        showline=False,
        zeroline=False,
        range=[-0.1, 1.1] if normalized else None,
    )

    if normalized:
        fig.update_yaxes(
            row=1,
            col=1,
            tickmode='array',
            tickvals=[0, 0.25, 0.5, 0.75, 1],
            ticktext=['Min', '', '', '', 'Max'],
        )

def _update_practices_axis(fig, df):
    '''Update the practices (bottom) subplot y-axis'''
    practice_cols = [col for col in df.columns if col not in ['session_date', 'session_number', 'Date']]
    practice_cols = [col for col in practice_cols if df[col].dtype == bool]
    
    if not practice_cols:
        ytick_vals = [0]
        ytick_texts = ['No practices defined']
        y_range = [-0.5, 0.5]
    else:
        ytick_vals = list(range(len(practice_cols)))
        ytick_texts = practice_cols[::-1]
        y_range = [-0.5, len(practice_cols) - 0.5]

    fig.update_yaxes(
        row=2,
        col=1,
        tickmode='array',
        tickvals=ytick_vals,
        ticktext=ytick_texts,
        showgrid=False,
        showline=False,
        zeroline=False,
        range=y_range,
    )

def _update_x_axis(fig, xaxis_select, x_values):
    '''Update the x-axis based on selection'''
    # Update both subplots' x-axes to ensure consistency
    for axis in ['xaxis', 'xaxis2']:
        title = xaxis_select if axis == 'xaxis2' else None
        fig.update_layout({
            axis: {
                'title': title,
                'showgrid': False,
                'showline': False,
                'zeroline': False,
                'type': 'linear',
                'tickmode': 'array',
                'dtick': None,
                'tickformat': None,
                'calendar': None,
                'hoverformat': None,
                'type': 'linear',
                'tickvals':x_values
            }
        })
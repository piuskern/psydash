import base64
import json
from datetime import date

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from globals import (
    APP_TITLE,
    COLORS_MEASURES,
    DEFAULT_CLIENT_INFO,
    DEFAULT_ROW_MEASURE,
    DEFAULT_ROW_PRACTICE,
    DEFAULT_ROW_SESSION,
    EXAMPLE_FILE_PATH,
    HELP_TEXT_HOME,
    INSTRUCTIONS,
    PAGE_HEADER_STYLE,
    create_help_button,
)

dash.register_page(__name__, path='/', name='Home', order=0, title=APP_TITLE)

# Page layout

layout = html.Div([

    # Header
    html.H2('Home', style=PAGE_HEADER_STYLE),
    
    # Instructions
    dcc.Markdown(INSTRUCTIONS),
    
    # Buttons
    html.Div(
        [
            dbc.Button('New Record', id='new-record-btn', color='danger', className='mt-2 me-2'),
            dcc.Upload(
                id='load-record-btn',
                children=dbc.Button('Load Record', className='mt-2 me-2'),
                multiple=False,
                accept='.json'
            ),
            dbc.Button('Save Record', id='save-record-btn', color='success', className='mt-2 me-2'),
            dcc.Download(id='download-json'),
            dbc.Button('Show example', id='show-example-btn', color='secondary', className='mt-2 me-2'),            
        ], 
        style={'display': 'flex', 'flex-wrap': 'wrap'}
    ),

    # Modal confirm new record
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle('New Record')),
        dbc.ModalBody('The current data will be deleted.'),
        dbc.ModalFooter([
            dbc.Button('Cancel', id='cancel-new-record-btn', color='secondary'),
            dbc.Button('Confirm', id='confirm-new-record-btn', color='danger')
        ]),
    ], id='new-record-modal', is_open=False),

    # Modal save record filename
    dbc.Modal([
        dbc.ModalHeader('Enter Filename'),
        dbc.ModalBody(
            dbc.Input(id='filename-input', placeholder='Enter filename', type='text')
        ),
        dbc.ModalFooter(
            dbc.Button('Save', id='confirm-save-btn', color='primary')
        ),
    ], id='filename-modal', is_open=False),

    # Alert
    dbc.Alert(id='data-alert', is_open=False, duration=4000, color='success', className='mt-2', style={'width': 'fit-content'}),
    create_help_button(HELP_TEXT_HOME)
])

# Callbacks

# Open filename modal
@callback(
    Output('filename-modal', 'is_open'),
    [Input('save-record-btn', 'n_clicks'), Input('confirm-save-btn', 'n_clicks')],
    [State('filename-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_modal(save_clicks, confirm_clicks, is_open):
    if save_clicks or confirm_clicks:
        return not is_open
    return is_open

# Save data
@callback(
    Output('download-json', 'data'),
    Output('data-alert', 'children', allow_duplicate=True),
    Output('data-alert', 'is_open', allow_duplicate=True),
    Output('data-alert', 'color', allow_duplicate=True),
    Input('confirm-save-btn', 'n_clicks'),
    State('filename-input', 'value'),
    State('client-store', 'data'),
    State('measures-store', 'data'),
    State('sessions-store', 'data'),
    State('practices-store', 'data'),
    prevent_initial_call=True
)
def save_data(n_clicks, filename, client_data, measures_data, sessions_data, practices_data):
    if n_clicks is None or not filename:
        return dash.no_update, 'Record not saved. Please enter a filename.', True, 'warning'
    
    # Default the filename if not provided
    if not filename.endswith('.json'):
        filename += '.json'

    combined_data = {
        'client': client_data,
        'measures': measures_data,
        'sessions': sessions_data,
        'practices': practices_data
    }
    
    # Sanitize data before saving
    sanitized_data = sanitize_data_types(combined_data)
    
    data_download = dict(
        content=json.dumps(sanitized_data, indent=2),
        filename=filename
    )
    
    return data_download, 'Record saved.', True, 'success'

# Show example
@callback(
    Output('client-store', 'data', allow_duplicate=True),
    Output('measures-store', 'data', allow_duplicate=True),
    Output('sessions-store', 'data', allow_duplicate=True),
    Output('practices-store', 'data', allow_duplicate=True),
    Output('data-alert', 'children', allow_duplicate=True),
    Output('data-alert', 'is_open', allow_duplicate=True),
    Output('data-alert', 'color', allow_duplicate=True),
    Input('show-example-btn', 'n_clicks'),
    prevent_initial_call=True
)
def show_example(show_example_clicks):

    if not show_example_clicks:
        raise PreventUpdate
    with open(EXAMPLE_FILE_PATH, 'r') as file:
        data = json.load(file)
    
    # Extract data from the JSON structure
    client_data = data.get('client', [])
    measures_data = data.get('measures', [])
    sessions_data = data.get('sessions', [])
    practices_data = data.get('practices', [])

    alert_message = 'Example loaded.'
    show_alert = True
    alert_color = 'success'
    
    return client_data, measures_data, sessions_data, practices_data, alert_message, show_alert, alert_color

# Load data
@callback(
    Output('client-store', 'data', allow_duplicate=True),
    Output('measures-store', 'data', allow_duplicate=True),
    Output('sessions-store', 'data', allow_duplicate=True),
    Output('practices-store', 'data', allow_duplicate=True),
    Output('data-alert', 'children', allow_duplicate=True),
    Output('data-alert', 'is_open', allow_duplicate=True),
    Output('data-alert', 'color', allow_duplicate=True),
    Input('load-record-btn', 'contents'),
    prevent_initial_call=True
)
def load_data(contents):
    if contents is None:
        raise PreventUpdate
    
    try:
        # Parse file contents
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        data = json.loads(decoded.decode('utf-8'))
        
        # Sanitize and validate data
        sanitized_data = sanitize_data_types(data)
        
        # Use defaults if sections are missing
        return (
            sanitized_data.get('client', [DEFAULT_CLIENT_INFO]),
            sanitized_data.get('measures', [DEFAULT_ROW_MEASURE]),
            sanitized_data.get('sessions', [DEFAULT_ROW_SESSION]),
            sanitized_data.get('practices', [DEFAULT_ROW_PRACTICE]),
            'Record uploaded.', True, 'success'
        )
    
    except json.JSONDecodeError:
        print("Invalid JSON format")
        return (
            dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            'Record not uploaded. Invalid JSON format.', True, 'danger'
        )
    except Exception as e:
        print(f"Error loading data: {e!s}")
        return (
            dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            'Record not uploaded. Invalid file format.', True, 'danger'
        )
    
# Start new record
@callback(
    Output('new-record-modal', 'is_open'),
    Output('data-alert', 'children', allow_duplicate=True),
    Output('data-alert', 'is_open', allow_duplicate=True),
    Output('data-alert', 'color', allow_duplicate=True),
    Output('client-store', 'data', allow_duplicate=True),
    Output('measures-store', 'data', allow_duplicate=True),
    Output('sessions-store', 'data', allow_duplicate=True),
    Output('practices-store', 'data', allow_duplicate=True),
    Input('new-record-btn', 'n_clicks'),
    Input('cancel-new-record-btn', 'n_clicks'),
    Input('confirm-new-record-btn', 'n_clicks'),
    State('client-store', 'data'),
    State('measures-store', 'data'),
    State('sessions-store', 'data'),
    State('practices-store', 'data'),
    prevent_initial_call=True
)
def start_new_record(new_clicks, cancel_clicks, confirm_clicks, 
                     client_data, measures_data, sessions_data, practices_data):
    trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    
    current_data_is_default = (
        client_data == [DEFAULT_CLIENT_INFO] and 
        measures_data == [DEFAULT_ROW_MEASURE] and 
        sessions_data == [DEFAULT_ROW_SESSION] and 
        practices_data == [DEFAULT_ROW_PRACTICE]
    )
    
    if trigger == 'new-record-btn' and current_data_is_default and new_clicks:
        return False, 'New record initialized.', True, 'success', *[dash.no_update] * 4
    
    if trigger == 'new-record-btn' and new_clicks:
        return True, *[dash.no_update] * 7  # Show modal
        
    if trigger == 'confirm-new-record-btn':
        return False, 'New record initialized.', True, 'success', [DEFAULT_CLIENT_INFO], [DEFAULT_ROW_MEASURE], [DEFAULT_ROW_SESSION], \
               [DEFAULT_ROW_PRACTICE]
    
    if trigger == 'cancel-new-record-btn':
        return False, *[dash.no_update] * 7
        
    raise PreventUpdate

def convert_to_float(value):
    """Safely convert a value to float."""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def convert_to_int(value, default=0):
    """Safely convert a value to integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def convert_to_bool(value):
    """Safely convert a value to boolean."""
    return bool(value) if value is not None else False

def convert_to_date(value):
    """Safely convert a value to ISO date string."""
    try:
        if value:
            return date.fromisoformat(str(value)).isoformat()
        return date.today().isoformat()
    except (ValueError, TypeError):
        return date.today().isoformat()

def sanitize_measure(measure):
    """Sanitize a single measure entry."""
    if not measure:
        return measure
    
    sanitized = measure.copy()
    measure_type = measure.get('Type', 'Scale')
    sanitized['SelectMeasure'] = convert_to_bool(measure.get('SelectMeasure'))
    sanitized['SelectRater'] = convert_to_bool(measure.get('SelectRater'))
    if measure_type == 'Count':
        sanitized['Min'] = 0
        sanitized['Max'] = None
    else: 
        min_value = convert_to_float(measure.get('Min'))
        sanitized['Min'] = 0 if min_value is None else min_value
        
        max_value = convert_to_float(measure.get('Max'))
        sanitized['Max'] = 100 if max_value is None else max_value
        
        if sanitized['Max'] <= sanitized['Min']:
            sanitized['Min'] = 0
            sanitized['Max'] = 100
    
    return sanitized

def sanitize_session(session, measures, practices):
    """Sanitize a single session entry."""
    if not session:
        return session
    
    sanitized = {
        'session_number': convert_to_int(session.get('session_number')),
        'session_date': convert_to_date(session.get('session_date'))
    }
    
    # Handle measure values
    for measure in measures:
        if measure['Name'] != 'New Measure':
            sanitized[measure['Name']] = convert_to_float(session.get(measure['Name']))
    
    # Handle practice values
    for practice in practices:
        if practice['Name'] != 'New Practice':
            sanitized[practice['Name']] = convert_to_bool(session.get(practice['Name']))
    
    return sanitized

def sanitize_practice(practice):
    """Sanitize a single practice entry."""
    if not practice:
        return practice
    
    return {
        'Name': str(practice.get('Name', '')),
        'Description': str(practice.get('Description', ''))
    }

def sanitize_data_types(data):
    """Sanitize all data types before saving or after loading."""
    if not data:
        return data

    sanitized = {}
    
    # Handle measures
    if 'measures' in data:
        sanitized['measures'] = [sanitize_measure(m) for m in data['measures']]
        # Backfill Color for measures saved before the field existed, or added by hand
        for i, measure in enumerate(sanitized['measures']):
            if not measure.get('Color'):
                measure['Color'] = COLORS_MEASURES[i % len(COLORS_MEASURES)]
    
    # Handle practices
    if 'practices' in data:
        sanitized['practices'] = [sanitize_practice(p) for p in data['practices']]
    
    # Handle sessions
    if 'sessions' in data:
        measures = data.get('measures', [])
        practices = data.get('practices', [])
        sanitized['sessions'] = [
            sanitize_session(s, measures, practices) 
            for s in data['sessions']
        ]
    
    # Pass through client data
    if 'client' in data:
        sanitized['client'] = data['client']
    
    return sanitized
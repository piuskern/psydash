import dash
from dash import html, dcc, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_ag_grid as dag
from datetime import date, timedelta
from dash_iconify import DashIconify

from globals import APP_TITLE, PAGE_HEADER_STYLE, DEFAULT_ROW_SESSION, AG_GRID_THEME, ALERT_DURATION, HELP_TEXT_SESSIONS, create_help_button

dash.register_page(__name__, name='Sessions', order=4, title=APP_TITLE)

# AG Grid configuration

ag_grid_config = {
    'dashGridOptions': {
        'animateRows': False,
        'rowSelection': 'multiple',
        'suppressRowClickSelection': True,
        'singleClickEdit': True,
        'tooltipShowDelay': 500,
        'suppressScrollOnNewData': True,
        'suppressFieldDotNotation': True
    },
    'defaultColDef': {
        'filter': False,
        'resizable': False,
        'sortable': False,
        'suppressMovable': True,
    },
    'className': AG_GRID_THEME,
    'style': {'height': 400, 'width': '100%', 'minWidth': 400},
}

# Page layout

layout = html.Div([
    html.H2('Sessions', style=PAGE_HEADER_STYLE),
    html.Div(dag.AgGrid(id='sessions-grid', **ag_grid_config), style={'height': 400}),
    html.Div(id='custom-component-checkbox-value-changed-1'),
    dbc.Button(
        'Add Row',
        id='add-row-sessions-btn',
        color='primary',
        className='mt-2 me-2', 
    ),
    dbc.Button(
        'Delete Selected',
        id='delete-row-sessions-btn',
        color='danger',
        className='mt-2', 
    ),
    dbc.Alert(
        id='sessions-alert',
        is_open=False,
        duration=ALERT_DURATION,
        color='warning',
        className='mt-2',
        style={'width': 'fit-content'}
    ),
    create_help_button(HELP_TEXT_SESSIONS)
])

# Callbacks

@callback(
    Output('sessions-store', 'data', allow_duplicate=True),
    Output('sessions-grid', 'rowData'),
    Output('sessions-grid', 'columnDefs'),
    Output('sessions-alert', 'children'),
    Output('sessions-alert', 'is_open'),
    Input('add-row-sessions-btn', 'n_clicks'),
    Input('delete-row-sessions-btn', 'n_clicks'),
    Input('sessions-grid', 'cellValueChanged'),
    State('sessions-grid', 'rowData'),
    State('sessions-grid', 'selectedRows'),
    State('measures-store', 'data'),
    State('sessions-store', 'data'),
    State('practices-store', 'data'),
    prevent_initial_call='initial_duplicate'
)
def update_sessions(add_clicks, delete_clicks, cell_changed, rows, selected_rows, measures_data, sessions_data, practices_data):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    alert = {'message': None, 'show': False}
    columnDefs = generate_column_defs(measures_data, practices_data)
    updated_sessions = rows or sessions_data or [DEFAULT_ROW_SESSION]

    if trigger_id == 'add-row-sessions-btn':
        updated_sessions = add_new_session(updated_sessions, columnDefs, practices_data)
    elif trigger_id == 'delete-row-sessions-btn' and selected_rows:
        updated_sessions = delete_sessions(updated_sessions, selected_rows)
        if not updated_sessions:
            updated_sessions = add_new_session(updated_sessions, columnDefs, practices_data)
    elif trigger_id == 'sessions-grid' and cell_changed:
        updated_sessions, alert = validate_and_update_cell(updated_sessions, cell_changed, measures_data, practices_data)
        
        if not alert['show']:
            return updated_sessions, dash.no_update, columnDefs, alert['message'], alert['show']
    
    return updated_sessions, updated_sessions, columnDefs, alert['message'], alert['show']

def generate_column_defs(measures_data, practices_data):
    
    columnDefs = [
        {
            'field': 'session_number',
            'headerName': 'Session', 
            'editable': False, 
            'checkboxSelection': True,
            'headerCheckboxSelection': True,
            'pinned': 'left',
            'width':125
        },
        {
            'field': 'session_date',
            'headerName': 'Date',
            'editable': True,
            'type': 'dateColumn',
            'pinned': 'left',
            'width':140
         }
    ]
    
    if measures_data:
        measure_columns = [
            {
                'field': measure['Name'],
                'editable': True,
                'type': 'numericColumn', 
                'cellEditor': 'agNumberCellEditor',
                'valueParser': 'Number(newValue) || undefined',
                'headerTooltip': f"Rater: {measure['Rater']}, {measure['Type']}, Min: {measure['Min']}, Max: {measure['Max']}",
                'width': 200
            }
            for measure in measures_data
            if measure['Name'] != 'New Measure'
        ]
        columnDefs.extend(measure_columns)
    
    if practices_data:
        practice_columns = [
            {
                'field': practice['Name'],
                'cellRenderer': 'Checkbox',
                'cellRendererParams': {'clicked': 'cellClicked'},
                'editable': False,
                'headerClass': 'ag-right-aligned-header',
            }
            for practice in practices_data
            if practice['Name'] != 'New Practice'
        ]
        columnDefs.extend(practice_columns)
    
    return columnDefs

def add_new_session(sessions, columnDefs, practices_data):
    
    new_row = {col['field']: None for col in columnDefs if col['field'] not in ['session_number', 'session_date']}
    new_row['session_number'] = len(sessions) + 1
    
    if sessions:
        last_session_date = date.fromisoformat(sessions[-1]['session_date'])
        new_row['session_date'] = (last_session_date + timedelta(days=1)).isoformat()
    else:
        new_row['session_date'] = date.today().isoformat()
    
    if practices_data:
        for practice in practices_data:
            if practice['Name'] != 'New Practice':
                new_row[practice['Name']] = False
    return sessions + [new_row]

def delete_sessions(sessions, selected_rows):
    updated_sessions = [row for row in sessions if row not in selected_rows]
    
    if not updated_sessions:
        return []
        
    # Otherwise renumber the remaining sessions
    for i, row in enumerate(updated_sessions, start=1):
        row['session_number'] = i
    return updated_sessions

def validate_and_update_cell(sessions, cell_changed, measures_data, practices_data):
    alert = {'message': None, 'show': False}
    
    if not cell_changed:
        return sessions, alert

    change = cell_changed[0]
    field = change['colId']
    new_value = change['value'] if 'value' in change else None
    row_index = change['rowIndex']

    if field == 'session_date':
        
        # Check if the new date maintains chronological order
        try:
            new_date = date.fromisoformat(new_value)
            
            # Check previous session's date if not first session
            if row_index > 0:
                prev_date = date.fromisoformat(sessions[row_index - 1]['session_date'])
                if new_date <= prev_date:
                    sessions[row_index][field] = change['oldValue']
                    alert['message'] = f'Date must be after previous date ({prev_date.isoformat()}).'
                    alert['show'] = True
                    return sessions, alert
            
            # Check next session's date if not last session
            if row_index < len(sessions) - 1:
                next_date = date.fromisoformat(sessions[row_index + 1]['session_date'])
                if new_date >= next_date:
                    sessions[row_index][field] = change['oldValue']
                    alert['message'] = f'Date must be before next date ({next_date.isoformat()}).'
                    alert['show'] = True
                    return sessions, alert
            
            # If all checks pass, update the date
            sessions[row_index][field] = new_value
            
        except ValueError:
            sessions[row_index][field] = change['oldValue']
            alert['message'] = 'Invalid date format. Please use YYYY-MM-DD format.'
            alert['show'] = True
            return sessions, alert
            
    elif any(measure['Name'] == field for measure in measures_data):
        measure = next(measure for measure in measures_data if measure['Name'] == field)
        if new_value is not None and new_value != '':
            value = float(new_value)
            min_val = float(measure['Min'])
            max_val = float(measure['Max']) if measure['Type'] == 'Scale' else float('inf')
            if min_val <= value <= max_val:
                sessions[row_index][field] = value
            else:
                sessions[row_index][field] = change['oldValue']
                alert['message'] = f'{value} out of range {min_val} - {max_val} in {field}.'
                alert['show'] = True
        else:
            sessions[row_index][field] = None
            alert['message'] = f'Invalid value for {field}. Please enter a numerical value and use dots for decimals.'
            alert['show'] = True
    
    elif any(practice['Name'] == field for practice in practices_data):
        sessions[row_index][field] = bool(new_value)

    return sessions, alert
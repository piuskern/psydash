import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html

from globals import (
    AG_GRID_THEME,
    ALERT_DURATION,
    APP_TITLE,
    DEFAULT_ROW_PRACTICE,
    HELP_TEXT_PRACTICES,
    PAGE_HEADER_STYLE,
    create_help_button,
)

dash.register_page(__name__, name='Practices', order=3, title=APP_TITLE)

# AG Grid configuration
ag_grid_config = {
    'dashGridOptions': {
        'animateRows': True,
        'rowSelection': 'multiple',
        'suppressRowClickSelection': True,
        'singleClickEdit': True,
        'rowDragManaged': True,
        'rowDragEntireRow': True,
        'suppressScrollOnNewData': True,
    },
    'defaultColDef': {
        'filter': False,
        'resizable': False,
        'suppressMovable': True,
        'pinned': 'left'
    },
    'columnDefs': [
        {
            'field': 'Name',
            'editable': True,
            'checkboxSelection': True,
            'headerCheckboxSelection': True,
            'width': 250
        },
        {
            'field': 'Description',
            'editable': True,
            'flex': 1,
            'pinned': False,
            'cellStyle': {
                'white-space': 'nowrap',
                'overflow': 'visible',
            },
        },
    ],
    'className': AG_GRID_THEME,
    'style': {'height': 400, 'width': '100%', 'minWidth': 250}
}

# Page layout
layout = html.Div([
    html.H2('Practices', style=PAGE_HEADER_STYLE),
    html.Div(dag.AgGrid(id='practices-grid', **ag_grid_config), style={'height': 400}),
    dbc.Button(
        'Add Row',
        id='add-row-practices-btn', 
        color='primary', 
        className='mt-2 me-2'),
    dbc.Button(
        'Delete Selected',
        id='delete-rows-practices-btn',
        color='danger',
        className='mt-2'
    ),
    dbc.Alert(
        id='practices-alert',
        is_open=False,
        duration=ALERT_DURATION,
        color='warning',
        className='mt-2',
        style={'width': 'fit-content'}
    ),
    create_help_button(HELP_TEXT_PRACTICES)
])

# Callbacks

@callback(
    Output('practices-store', 'data'),
    Output('practices-grid', 'rowData'),
    Output('sessions-store', 'data', allow_duplicate=True),
    Output('practices-alert', 'children'),
    Output('practices-alert', 'is_open'),

    Input('practices-grid', 'cellValueChanged'),
    Input('add-row-practices-btn', 'n_clicks'),
    Input('delete-rows-practices-btn', 'n_clicks'),
    Input('practices-grid', 'virtualRowData'),

    State('practices-grid', 'rowData'),
    State('practices-grid', 'selectedRows'),
    State('practices-store', 'data'),
    State('sessions-store', 'data'),
    prevent_initial_call='initial_duplicate'
)
def update_practices(cell_changed, add_clicks, delete_clicks, virtual_row_data, current_rows, selected_rows, practices_data, sessions_data):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id']
    alert = {'message': dash.no_update, 'show': dash.no_update}

    if trigger_id == 'practices-grid.virtualRowData' and virtual_row_data:
        updated_rows, sessions_data = reorder_practices(virtual_row_data, practices_data, sessions_data)
    elif trigger_id == 'practices-grid.cellValueChanged':
        updated_rows, alert = update_cell(cell_changed, practices_data, sessions_data)
        practices_data = updated_rows
    elif trigger_id == 'add-row-practices-btn.n_clicks':
        updated_rows = practices_data + [DEFAULT_ROW_PRACTICE.copy()]
    elif trigger_id == 'delete-rows-practices-btn.n_clicks':
        updated_rows, sessions_data = delete_row(selected_rows, practices_data, sessions_data)
    else:
        updated_rows = practices_data

    return updated_rows, updated_rows, sessions_data, alert['message'], alert['show']

def reorder_practices(virtual_row_data, practices_data, sessions_data):
    
    if virtual_row_data and virtual_row_data != practices_data:
        
        # Reorder practices in sessions data
        new_order = [row['Name'] for row in virtual_row_data]
        sessions_data_updated = []
    
        for session in sessions_data:
            reordered_session = {k: session[k] for k in session if k not in new_order}
            
            for practice in new_order:
                reordered_session[practice] = session.get(practice, None)
            
            sessions_data_updated.append(reordered_session)
        sessions_data = sessions_data_updated

    return virtual_row_data, sessions_data

def update_cell(cell_changed, rows, sessions_data):
    alert = {'message': '', 'show': False}
    
    if not cell_changed:
        return rows, alert
    
    # Create a deep copy of rows
    updated_rows = [row.copy() for row in rows]
    cell = cell_changed[0]
    index = cell['rowIndex']
    column = cell['colId']
    old_value = cell['oldValue']
    new_value = cell['value']
    
    if column == 'Name':
        # Keep old value until validation is complete
        updated_rows[index]['Name'] = old_value

        existing_names = [row['Name'] for row in rows if row['Name'] != old_value]
        if not is_valid_name(new_value, existing_names):
            alert['message'] = get_alert_message(new_value)
            alert['show'] = True
        else:
            updated_rows[index]['Name'] = new_value
            update_sessions_data(sessions_data, old_value, new_value)
    else:
        updated_rows[index][column] = new_value
    
    return updated_rows, alert

def is_valid_name(name, existing_names):
    return (
        name
        and name.strip()
        and '"' not in name
        and "'" not in name
        and name.lower() not in ['new practice', 'new measure']
        and name not in existing_names
    )

def get_alert_message(name):
    if not name or not name.strip():
        return 'Empty name not allowed. Please choose a different name.'
    elif name.lower() in ['new practice', 'new measure']:
        return 'Name not allowed. Please choose a different name.'
    elif '"' in name or  "'" in name:
        return 'Quotation marks not allowed. Please choose a different name.'
    else:
        return f'Name {name} already in use. Please choose a different name.'

def update_sessions_data(sessions_data, old_value, new_value):
    for session in sessions_data:
        if old_value in session:
            session[new_value] = session.pop(old_value)
        else:
            session[new_value] = False

def delete_row(selected_rows, practices_data, sessions_data):
    if selected_rows:
        updated_rows = [row for row in practices_data if row not in selected_rows]
        if not updated_rows:
            updated_rows = [DEFAULT_ROW_PRACTICE]

        delete_values = [row['Name'] for row in selected_rows]
        for value in delete_values:
            for session in sessions_data:
                session.pop(value, None)
    else:
        updated_rows = practices_data
    return updated_rows, sessions_data
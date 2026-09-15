import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html

from globals import (
    AG_GRID_THEME,
    ALERT_DURATION,
    APP_TITLE,
    COLORS_MEASURES,
    DEFAULT_ROW_MEASURE,
    HELP_TEXT_MEASURES,
    PAGE_HEADER_STYLE,
    create_help_button,
    get_rater_selection,
)

dash.register_page(__name__, name='Measures', order=2, title=APP_TITLE)

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
        'editable': True,
        'pinned': 'left'
    },
    # Define columns
    'columnDefs': [
        {
            'field': 'Name',
            'checkboxSelection': True,
            'headerCheckboxSelection': True,
            'width': 250,
        },
        {
            'field': 'Rater',
            'cellEditor': 'agSelectCellEditor',
            'cellEditorParams': {'values': ['Self', 'Caregiver', 'Educator', 'Therapist', 'Other']},
            'headerClass': 'ag-left-aligned-header',
            'cellStyle': {'textAlign': 'left'},
            'width': 120,
        },
        {
            'field': 'Type',
            'cellEditor': 'agSelectCellEditor',
            'cellEditorParams': {'values': ['Scale', 'Count']},
            'headerClass': 'ag-left-aligned-header',
            'cellStyle': {'textAlign': 'left'},
            'width': 100,
        },
        {
            'field': 'Min',
            'type': 'numericColumn',
            'valueParser': 'Number(newValue)',
            'width': 100,
        },
        {
            'field': 'Max',
            'type': 'numericColumn',
            'valueParser': 'Number(newValue)',
            'width': 100,
        },
        {
            'field': 'Description',
            'flex': 1,
            'pinned': False,
            'cellStyle': {
                'white-space': 'nowrap',
                'overflow': 'visible',
            },
        }
    ],
    'className': AG_GRID_THEME,
    'style': {'height': 400, 'width': '100%', 'minWidth': 400},
}

# Page layout
layout = html.Div([
    html.H2('Measures', style=PAGE_HEADER_STYLE),
    html.Div(dag.AgGrid(id='measures-grid', **ag_grid_config), style={'height': 400}),
    dbc.Button(
        'Add Row',
        id='add-row-measures-btn',
        color='primary',
        className='mt-2 me-2'
    ),
    dbc.Button(
        'Delete Selected', 
        id='delete-rows-measures-btn', 
        color='danger', 
        className='mt-2'
    ),
    dbc.Alert(
        id='measures-alert',
        is_open=False,
        duration=ALERT_DURATION,
        color='warning',
        className='mt-2',
        style={'width': 'fit-content'}
    ),
    create_help_button(HELP_TEXT_MEASURES)

])

# Callbacks

@callback(
    Output('measures-store', 'data', allow_duplicate=True),
    Output('measures-grid', 'rowData', allow_duplicate=True),
    Output('sessions-store', 'data', allow_duplicate=True),
    Output('measures-alert', 'children'),
    Output('measures-alert', 'is_open'),
    
    Input('measures-grid', 'cellValueChanged'),
    Input('add-row-measures-btn', 'n_clicks'),
    Input('delete-rows-measures-btn', 'n_clicks'),
    Input('measures-grid', 'virtualRowData'),
      
    State('measures-grid', 'rowData'),
    State('measures-grid', 'selectedRows'),
    State('measures-store', 'data'),
    State('sessions-store', 'data'),
    prevent_initial_call='initial_duplicate'
)
def update_measures(cell_changed, add_clicks, delete_clicks, virtual_row_data, current_rows, selected_rows, measures_data, sessions_data):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id']
    alert = {'message': dash.no_update, 'show': dash.no_update}

    if trigger_id == 'measures-grid.virtualRowData' and virtual_row_data:
        updated_rows, sessions_data = reorder_measures(virtual_row_data, measures_data, sessions_data)
    elif trigger_id == 'measures-grid.cellValueChanged':
        updated_rows, alert, sessions_data = update_cell(cell_changed, measures_data, sessions_data)
        measures_data = updated_rows
    elif trigger_id == 'add-row-measures-btn.n_clicks':
        updated_rows = measures_data + [DEFAULT_ROW_MEASURE.copy()]
    elif trigger_id == 'delete-rows-measures-btn.n_clicks':
        updated_rows, sessions_data = delete_rows(selected_rows, measures_data, sessions_data)
    else:
        updated_rows = measures_data

    return updated_rows, updated_rows, sessions_data, alert['message'], alert['show']

def update_cell(cell_changed, rows, sessions_data):
    alert = {'message': '', 'show': False}
    
    if not cell_changed:
        return rows, alert, sessions_data
    
    cell = cell_changed[0]
    index = cell['rowIndex']
    column = cell['colId']
    old_value = cell['oldValue']
    new_value = cell.get('value', None)
    
    # Create a deep copy of rows to ensure we're working with a new instance
    updated_rows = [row.copy() for row in rows]
    
    if column == 'Name':
        # Keep old value until validation is complete
        updated_rows[index]['Name'] = old_value
        updated_rows, alert = handle_name_change(index, old_value, new_value, updated_rows, sessions_data)
    elif column == 'Type':
        updated_rows = handle_type_change(index, new_value, updated_rows)
    elif column == 'Rater':
        updated_rows = handle_rater_change(index, new_value, updated_rows)
    elif column in ['Min', 'Max']:
        updated_rows, alert = handle_min_max_change(index, column, old_value, new_value, updated_rows, sessions_data)
        if alert['show']:
            # If validation failed, return immediately to prevent invalid value from being stored
            return updated_rows, alert, sessions_data
    
    # Only update the value if validation passed
    if not alert['show']:
        updated_rows[index][column] = new_value
    
    return updated_rows, alert, sessions_data
def handle_name_change(index, old_value, new_value, rows, sessions_data):
    alert = {'message': '', 'show': False}

    existing_names = [row['Name'] for row in rows if row['Name'] != old_value]

    if not is_valid_name(new_value, existing_names):
        alert['message'] = get_alert_message(new_value)
        alert['show'] = True
    else:
        rows[index]['Name'] = new_value
        update_sessions_measure_names(sessions_data, old_value, new_value)
        set_measure_colors(rows)

    return rows, alert

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
    elif name.lower() == 'new measure' or name.lower() == 'new practice':
        return 'Name not allowed. Please choose a different name.'
    elif '"' in name or  "'" in name:
        return 'Quotation marks not allowed. Please choose a different name.'
    else:
        return f'Name {name} already in use. Please choose a different name.'

def handle_type_change(index, new_value, rows):
    '''Handles changes to the 'Type' column, adjusting 'Min' and 'Max' values accordingly.'''
    if new_value == 'Count':
        rows[index]['Min'] = 0
        rows[index]['Max'] = None
    elif new_value == 'Scale' and rows[index]['Max'] is None:
        rows[index]['Min'] = 0
        rows[index]['Max'] = 100
    return rows

def handle_rater_change(index, new_value, rows):
    '''Handles changes to the 'Rater' column, adjusting 'SelectMeasure' and 'SelectRater' values accordingly.'''
    rater_selection = get_rater_selection(rows[:index] + rows[index + 1:])
    if new_value in rater_selection:
        rows[index]['SelectRater'] = rater_selection[new_value]
        rows[index]['SelectMeasure'] = rater_selection[new_value]
    elif not rows[index]['SelectRater']:
        rows[index]['SelectRater']  = False
        rows[index]['SelectMeasure'] = False

    return rows

def handle_min_max_change(index, column, old_value, new_value, rows, sessions_data):
    '''Handles validation for changes in 'Min' and 'Max' columns.'''
    alert = {'message': '', 'show': False}
    
    # If new_value is None or empty string, keep old value
    if new_value is None or new_value == '':
        rows[index][column] = old_value
        alert['message'] = f'Invalid input for {column}. Please enter a valid number and use dots for decimals.'
        alert['show'] = True
        return rows, alert

    # Check if new_value is a valid number
    if not is_valid_number(new_value):
        rows[index][column] = old_value
        alert['message'] = f'Invalid input for {column}. Please enter a valid number and use dots for decimals.'
        alert['show'] = True
        return rows, alert

    # Convert to float for comparison
    new_value_float = float(new_value)
    
    # Specific validations for 'Count' type
    if rows[index]['Type'] == 'Count':
        rows[index][column] = old_value
        alert['message'] = 'Min and Max are fixed for measures of Type Count.'
        alert['show'] = True
        return rows, alert
    
    # Get the other value (Min or Max) for comparison
    other_column = 'Max' if column == 'Min' else 'Min'
    other_value = rows[index][other_column]
    
    if other_value is not None:
        other_value_float = float(other_value)
        
        # Check for valid range between 'Min' and 'Max'
        if column == 'Min' and new_value_float >= other_value_float:
            rows[index][column] = old_value
            alert['message'] = 'Min must be smaller than Max.'
            alert['show'] = True
            return rows, alert
        elif column == 'Max' and new_value_float <= other_value_float:
            rows[index][column] = old_value
            alert['message'] = 'Max must be larger than Min.'
            alert['show'] = True
            return rows, alert
    
    # If we get here, the new value is valid
    rows[index][column] = new_value_float  # Store as float instead of string
    
    # Check if any session data needs updating
    alert = update_sessions_on_out_of_range(index, rows, sessions_data)
    
    return rows, alert

def update_sessions_on_out_of_range(index, rows, sessions_data):
    '''Checks if session data is out of the new Min/Max range and adjusts it.'''
    alert = {'message': '', 'show': False}
    measure_name = rows[index]['Name']
    min_value = float(rows[index]['Min'])
    max_value = float(rows[index]['Max'])

    for session in sessions_data:
        session_value = session.get(measure_name)
        if session_value is not None and not (min_value <= session_value <= max_value):
            session[measure_name] = None
            alert['message'] = f'Values of {measure_name} in sessions data were out of range and have been deleted.'
            alert['show'] = True

    return alert

def is_valid_number(value, allow_zero=True):
    '''Enhanced number validation function'''
    if value is None:
        return False
    
    # Handle string input
    if isinstance(value, str):
        # Remove whitespace
        value = value.strip()
        # Check if empty after stripping
        if not value:
            return False
        
    try:
        num = float(value)
        # Check if it's a valid number (not infinity or NaN)
        if not (isinstance(num, (int, float)) and (allow_zero or num != 0)):
            return False
        return True
    except (ValueError, TypeError):
        return False

def update_sessions_measure_names(sessions_data, old_value, new_value):
    for session in sessions_data:
        if old_value in session:
            session[new_value] = session.pop(old_value)
        else:
            session[new_value] = None

def set_measure_colors(rows):
    for i, measure in enumerate(rows):
        measure['Color'] = COLORS_MEASURES[i % len(COLORS_MEASURES)]

def delete_rows(selected_rows, measures_data, sessions_data):
    if selected_rows:
        updated_rows = [row for row in measures_data if row not in selected_rows]
        if not updated_rows:
            updated_rows = [DEFAULT_ROW_MEASURE.copy()]

        delete_values = [row['Name'] for row in selected_rows if row['Name'] != 'New Measure']
        for value in delete_values:
            for session in sessions_data:
                session.pop(value, None)
    else:
        updated_rows = measures_data
    return updated_rows, sessions_data

def reorder_measures(virtual_row_data, measures_data, sessions_data):
    if virtual_row_data and virtual_row_data != measures_data:

        new_order = [row['Name'] for row in virtual_row_data]
        sessions_data_updated = []
    
        for session in sessions_data:
            reordered_session = {k: session[k] for k in session if k not in new_order}
            
            for measure in new_order:
                reordered_session[measure] = session.get(measure, None)
            
            sessions_data_updated.append(reordered_session)
        sessions_data = sessions_data_updated

    return virtual_row_data, sessions_data
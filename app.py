import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import _dash_renderer, dcc, html

from globals import (
    DEFAULT_CLIENT_INFO,
    DEFAULT_ROW_MEASURE,
    DEFAULT_ROW_PRACTICE,
    DEFAULT_ROW_SESSION,
    PAGE_HEADER_STYLE,
)

_dash_renderer._set_react_version("18.2.0")

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    update_title=None,
    meta_tags=[{
        'name': 'viewport',
        'content': 'width=device-width, initial-scale=1.0'
    }]
)
app.title = 'PsyDash'

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        <link rel="apple-touch-icon" sizes="180x180" href="assets/icon/icon-apple-touch.png">
        {%css%}
        <style>
            :root { 
                font-size: 16px; 
            }

            @media (max-width: 768px) { 
                :root { 
                    font-size: 14px; 
                } 
            }

            ._dash-loading,
            #_dash-loading-callback,
            .ag-overlay-loading-wrapper,
            .ag-overlay-loading-center {
                display: none !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

sidebar_style = {
    'position': 'fixed',
    'top': 0,
    'left': 0,
    'bottom': 0,
    'width': '16rem',
    'padding': '2rem 1rem',
    'background-color': '#f8f9fa',
    'display': 'flex',
    'flex-direction': 'column',
}

logo_style = {
    'height': '3rem',
    'margin-right': '1rem',
    'object-fit': 'contain'
}

def create_header():
    return html.Div([
        html.Img(src='assets/icon-bw/icon-bw.png', style=logo_style),
        html.H2('PsyDash', style=PAGE_HEADER_STYLE)
    ], style={'display': 'flex', 'align-items': 'center'})

def create_nav():
    return dbc.Nav([
        dbc.NavLink(page['name'], href=page['path'], active='exact')
        for page in dash.page_registry.values()
    ], vertical=True, pills=True)

sidebar = html.Div([
    create_header(),
    html.Hr(),
    create_nav()
], style=sidebar_style)

content = html.Div(
    dash.page_container,
    style={
        'margin-left': '18rem',
        'margin-right': '2rem',
        'padding': '2rem 1rem',
    }
)

app.layout = dmc.MantineProvider(
    [
        dcc.Store(id='measures-store', data=[DEFAULT_ROW_MEASURE], storage_type='session'),
        dcc.Store(id='sessions-store', data=[DEFAULT_ROW_SESSION], storage_type='session'),
        dcc.Store(id='practices-store', data=[DEFAULT_ROW_PRACTICE], storage_type='session'),
        dcc.Store(id='client-store', data=[DEFAULT_CLIENT_INFO], storage_type='session'),
        html.Div(
            dag.AgGrid(id='ag-grid-warmup', rowData=[], columnDefs=[]),
            style={'position': 'absolute', 'width': 0, 'height': 0, 'overflow': 'hidden'}
        ),
        html.Div([sidebar, content])
    ],
    theme={'fontSizes': {
        'xs': '0.75rem',
        'sm': '0.875rem',
        'md': '1rem',
        'lg': '1.125rem',
        'xl': '1.25rem',
    }}
)

server = app.server

if __name__ == '__main__':
    app.run_server(debug=False)
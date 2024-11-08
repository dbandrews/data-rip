import base64
import io
import json
import os

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import openai
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output, State
from collections import deque
from datetime import datetime

from data_rip.prompts import FUNCTION_CALLING_FEW_SHOTS_DICT, FUNCTION_CALLING_SYS_PROMPT

# Initialize the OpenAI API
client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the Dash app
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://use.fontawesome.com/releases/v5.15.4/css/all.css"
    ]  # Using CYBORG as base theme for dark mode and Font Awesome for icons
)

# Define custom styles
VAPORWAVE_COLORS = {
    'background': '#000033',
    'primary': '#FF71CE',
    'secondary': '#01CDFE',
    'accent': '#B967FF',
    'text': '#FFFB96'
}

ASCII_HEADER = """
▓█████▄  ▄▄▄     ▄▄▄█████▓ ▄▄▄          ██▀███   ██▓ ██▓███  
▒██▀ ██▌▒████▄   ▓  ██▒ ▓▒▒████▄       ▓██ ▒ ██▒▓██▒▓██░  ██▒
░██   █▌▒██  ▀█▄ ▒ ▓██░ ▒░▒██  ▀█▄     ▓██ ░▄█ ▒▒██▒▓██░ ██▓▒
░▓█▄   ▌░██▄▄▄▄██░ ▓██▓ ░ ░██▄▄▄▄██    ▒██▀▀█▄  ░██░▒██▄█▓▒ ▒
░▒████▓  ▓█   ▓██▒ ▒██▒ ░  ▓█   ▓██▒   ░██▓ ▒██▒░██░▒██▒ ░  ░
 ▒▒▓  ▒  ▒▒   ▓▒█░ ▒ ░░    ▒▒   ▓▒█░   ░ ▒▓ ░▒▓░░▓  ▒▓▒░ ░  ░
 ░ ▒  ▒   ▒   ▒▒ ░   ░      ▒   ▒▒ ░     ░▒ ░ ▒░ ▒ ░░▒ ░     
 ░ ░  ░   ░   ▒    ░        ░   ▒        ░░   ░  ▒ ░░░       
   ░          ░  ░              ░  ░      ░      ░           
 ░                                                            
"""

# Define the layout
app.layout = dbc.Container(
    fluid=True,
    style={
        'background': f'linear-gradient(45deg, {VAPORWAVE_COLORS["background"]}, #330033)',
        'minHeight': '100vh',
        'color': VAPORWAVE_COLORS['text']
    },
    children=[
        # ASCII Art Header
        dbc.Row(
            dbc.Col(
                html.Pre(
                    ASCII_HEADER,
                    style={
                        'color': VAPORWAVE_COLORS['primary'],
                        'textAlign': 'center',
                        'fontFamily': 'monospace',
                        'whiteSpace': 'pre',
                        'margin': '20px 0',
                        'textShadow': f'2px 2px {VAPORWAVE_COLORS["secondary"]}',
                        'fontSize': '0.7em',
                        'letterSpacing': '1px',
                        'animation': 'glow 1.5s ease-in-out infinite alternate'
                    }
                ),
                className="text-center"
            )
        ),
        dbc.Row([
            dbc.Col(
                width=4,
                children=[
                    html.Div(
                        [
                            html.H5(
                                "Enter detailed instructions for what types of question you want answered",
                                style={
                                    'color': VAPORWAVE_COLORS['primary'],
                                    'textShadow': f'2px 2px {VAPORWAVE_COLORS["secondary"]}',
                                    'fontFamily': '"Press Start 2P", cursive',
                                    'marginBottom': '20px'
                                }
                            ),
                            dcc.Textarea(
                                id="input-box",
                                placeholder="Enter something...",
                                value="I want to extract user names, and ids from this data",
                                style={
                                    'width': '100%',
                                    'height': '200px',
                                    'resize': 'vertical',
                                    'marginBottom': '20px',
                                    'background': 'rgba(0, 0, 51, 0.7)',
                                    'color': VAPORWAVE_COLORS['text'],
                                    'border': f'2px solid {VAPORWAVE_COLORS["secondary"]}',
                                    'borderRadius': '5px',
                                    'padding': '10px'
                                }
                            ),
                            html.Button(
                                "Submit", 
                                id="submit-fewshot-instruct",
                                style={
                                    'backgroundColor': VAPORWAVE_COLORS['primary'],
                                    'border': 'none',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'borderRadius': '5px',
                                    'marginBottom': '10px',
                                    'width': '100%',
                                    'boxShadow': f'3px 3px {VAPORWAVE_COLORS["secondary"]}',
                                }
                            ),
                            html.Div(id="output-box"),
                            dcc.Store(id="data-store"),
                            html.Button(
                                "Run Structured Extraction", 
                                id="run-extraction-button",
                                style={
                                    'backgroundColor': VAPORWAVE_COLORS['secondary'],
                                    'border': 'none',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'borderRadius': '5px',
                                    'width': '100%',
                                    'boxShadow': f'3px 3px {VAPORWAVE_COLORS["primary"]}',
                                }
                            ),
                        ],
                        style={
                            "padding": "20px",
                            "background": "rgba(0, 0, 51, 0.5)",
                            "borderRadius": "10px",
                            "backdropFilter": "blur(5px)",
                            "border": f"1px solid {VAPORWAVE_COLORS['accent']}"
                        },
                    )
                ],
                style={"height": "100vh", "padding": "20px"},
            ),
            dbc.Col(
                width=8,
                children=[
                    html.Div(
                        [
                            dcc.Upload(
                                id="upload-data",
                                children=html.Div([
                                    "Drag and Drop or ", 
                                    html.A("Select CSV Files", style={'color': VAPORWAVE_COLORS['primary']})
                                ]),
                                style={
                                    "width": "100%",
                                    "height": "60px",
                                    "lineHeight": "60px",
                                    "borderWidth": "2px",
                                    "borderStyle": "dashed",
                                    "borderColor": VAPORWAVE_COLORS['secondary'],
                                    "borderRadius": "5px",
                                    "textAlign": "center",
                                    "margin": "10px",
                                    "background": "rgba(0, 0, 51, 0.7)",
                                },
                                multiple=False,
                            ),
                            dbc.Row([
                                dbc.Col(
                                    html.Label(
                                        "ID column",
                                        style={'color': VAPORWAVE_COLORS['primary']}
                                    ), 
                                    width=6
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="id-column-selector",
                                        options=[
                                            {"label": "Please Upload a File to choose columns", "value": "upload-file"},
                                        ],
                                        value="upload-file",
                                        style={
                                            'backgroundColor': 'rgba(0, 0, 51, 0.7)',
                                            'color': VAPORWAVE_COLORS['text']
                                        }
                                    ),
                                    width=6,
                                ),
                            ]),
                            dbc.Row([
                                dbc.Col(
                                    html.Label(
                                        "Text column",
                                        style={'color': VAPORWAVE_COLORS['primary']}
                                    ), 
                                    width=6
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="text-column-selector",
                                        options=[
                                            {"label": "Please Upload a File to choose columns", "value": "upload-file"},
                                        ],
                                        value="upload-file",
                                        style={
                                            'backgroundColor': 'rgba(0, 0, 51, 0.7)',
                                            'color': VAPORWAVE_COLORS['text']
                                        }
                                    ),
                                    width=6,
                                ),
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Progress(
                                        id="extraction-progress",
                                        style={
                                            "height": "20px",
                                            "marginBottom": "10px",
                                            "backgroundColor": "rgba(0, 0, 51, 0.7)",
                                            "borderRadius": "10px",
                                        },
                                        className="mb-3",
                                    ),
                                    html.Div(id="progress-text", style={
                                        "color": VAPORWAVE_COLORS['text'],
                                        "textAlign": "center",
                                        "marginBottom": "10px",
                                    }),
                                ])
                            ]),
                            dcc.Store(id="progress-store", data={"current": 0, "total": 0}),
                            dcc.Interval(id='progress-interval', interval=500, disabled=True),  # 500ms interval
                            dcc.Store(id='processing-state', data={'processing': False, 'queue': [], 'current_row': 0, 'total_rows': 0}),
                            dag.AgGrid(
                                id="ag-grid", 
                                columnDefs=[], 
                                rowData=[],
                                dashGridOptions={
                                    "defaultColDef": {
                                        "resizable": True,
                                        "sortable": True,
                                        "filter": True
                                    }
                                },
                                className="ag-theme-alpine-dark"
                            ),
                            dag.AgGrid(
                                id="ag-grid-out", 
                                columnDefs=[], 
                                rowData=[],
                                dashGridOptions={
                                    "defaultColDef": {
                                        "resizable": True,
                                        "sortable": True,
                                        "filter": True
                                    }
                                },
                                className="ag-theme-alpine-dark"
                            ),
                        ],
                        style={
                            "padding": "20px",
                            "background": "rgba(0, 0, 51, 0.5)",
                            "borderRadius": "10px",
                            "backdropFilter": "blur(5px)",
                            "border": f"1px solid {VAPORWAVE_COLORS['accent']}"
                        },
                    ),
                ],
            ),
        ])
    ],
)


@app.callback(
    [Output("output-box", "children"), Output("data-store", "data")],
    [Input("submit-fewshot-instruct", "n_clicks")],
    [State("input-box", "value")],
)
def generate_chat_completions(n_clicks, input_value):
    if n_clicks is not None:
        # Make the OpenAI chat completions call with gpt-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                FUNCTION_CALLING_SYS_PROMPT,
                *FUNCTION_CALLING_FEW_SHOTS_DICT,
                {"role": "user", "content": input_value},
            ],
        )

        # Extract the completed message from the response
        completed_message = response.choices[0].message.content
        
        # Clean and parse the JSON schema
        cleaned_schema = completed_message.replace("```json", "").replace("```", "").replace("'", '"')
        try:
            schema_json = json.loads(cleaned_schema)
            
            # Create a nicely formatted display of the schema
            schema_display = html.Div([
                html.H5("Extraction Schema", 
                    style={
                        'color': VAPORWAVE_COLORS['primary'],
                        'textShadow': f'1px 1px {VAPORWAVE_COLORS["secondary"]}',
                        'marginBottom': '15px'
                    }
                ),
                html.Div([
                    html.Div([
                        html.H6("Fields to Extract:", 
                            style={
                                'color': VAPORWAVE_COLORS['secondary'],
                                'marginBottom': '10px'
                            }
                        ),
                        html.Div([
                            html.Div([
                                html.Strong(field, 
                                    style={
                                        'color': VAPORWAVE_COLORS['accent'],
                                        'marginRight': '10px'
                                    }
                                ),
                                html.Span(
                                    f"({properties.get('type', 'any')})",
                                    style={'color': VAPORWAVE_COLORS['text'], 'fontSize': '0.9em'}
                                ),
                                html.Div(
                                    properties.get('description', ''),
                                    style={'color': VAPORWAVE_COLORS['text'], 'fontSize': '0.8em', 'marginLeft': '20px'}
                                )
                            ], 
                            style={
                                'marginBottom': '10px',
                                'padding': '10px',
                                'background': 'rgba(0, 0, 51, 0.3)',
                                'borderRadius': '5px',
                                'border': f'1px solid {VAPORWAVE_COLORS["secondary"]}'
                            })
                            for field, properties in schema_json['properties'].items()
                        ]),
                        html.H6("Required Fields:", 
                            style={
                                'color': VAPORWAVE_COLORS['secondary'],
                                'marginTop': '15px',
                                'marginBottom': '10px'
                            }
                        ),
                        html.Div(
                            ", ".join(schema_json.get('required', [])),
                            style={
                                'color': VAPORWAVE_COLORS['text'],
                                'padding': '10px',
                                'background': 'rgba(0, 0, 51, 0.3)',
                                'borderRadius': '5px',
                                'border': f'1px solid {VAPORWAVE_COLORS["accent"]}'
                            }
                        )
                    ], 
                    style={
                        'padding': '15px',
                        'background': 'rgba(0, 0, 51, 0.5)',
                        'borderRadius': '10px',
                        'backdropFilter': 'blur(5px)',
                        'border': f'1px solid {VAPORWAVE_COLORS["accent"]}'
                    })
                ])
            ])
            
            return [schema_display, completed_message]
            
        except json.JSONDecodeError:
            return [
                html.Div([
                    html.H5("Error parsing schema", style={'color': 'red'}),
                    html.Pre(completed_message)
                ]), 
                completed_message
            ]

    # If the submit button has not been clicked, return an empty div and None for the data store
    return [html.Div(), None]


@app.callback(
    [
        Output("id-column-selector", "options"),
        Output("text-column-selector", "options"),
        Output("ag-grid", "columnDefs"),
        Output("ag-grid", "rowData"),
    ],
    Input("upload-data", "contents"),
    [State("upload-data", "filename")]
)
def update_output(contents, filename):
    if contents is None:
        return [], [], [], []

    try:
        # Decode the file contents
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
        
        # Read the file into a pandas DataFrame
        if "csv" in filename.lower():
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        elif "xls" in filename.lower():
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return [], [], [], []

        # Create options for dropdowns
        options = [{"label": col, "value": col} for col in df.columns]
        
        # Create column definitions and row data for ag-grid
        column_defs = [{"headerName": col, "field": col} for col in df.columns]
        row_data = df.to_dict("records")

        return options, options, column_defs, row_data

    except Exception as e:
        print(f"Error processing file: {e}")
        return [], [], [], []


@app.callback(
    [
        Output("processing-state", "data"),
        Output("progress-interval", "disabled"),
    ],
    Input("run-extraction-button", "n_clicks"),
    [
        State("data-store", "data"),
        State("ag-grid", "rowData"),
        State("ag-grid", "columnDefs"),
        State("id-column-selector", "value"),
        State("text-column-selector", "value"),
    ],
    prevent_initial_call=True
)
def start_processing(n_clicks, data, row_data, column_defs, id_column, text_column):
    if n_clicks is not None and data is not None and row_data:
        # Clean and parse the schema
        cleaned_schema_json = data.replace("```json", "").replace("```", "").replace("'", '"')
        cleaned_schema_json = json.loads(cleaned_schema_json)
        
        function_name = "extraction_function"
        tools = [
            {
                "type": "function",
                "function": {
                    "name": f"{function_name}",
                    "description": "Extract data as per the schema provided",
                    "parameters": {
                        "type": "object",
                        "properties": cleaned_schema_json["properties"],
                        "required": cleaned_schema_json["required"],
                    },
                },
            }
        ]

        processing_queue = deque()
        for row in row_data:
            processing_queue.append({
                'row': row,
                'text_column': text_column,
                'tools': tools,
                'function_name': function_name
            })

        return {
            'processing': True,
            'queue': list(processing_queue),
            'current_row': 0,
            'total_rows': len(row_data),
            'column_defs': column_defs,
            'processed_rows': []
        }, False

    return {'processing': False, 'queue': [], 'current_row': 0, 'total_rows': 0}, True

@app.callback(
    [
        Output("ag-grid-out", "columnDefs"),
        Output("ag-grid-out", "rowData"),
        Output("extraction-progress", "value"),
        Output("extraction-progress", "label"),
        Output("progress-text", "children"),
        Output("processing-state", "data", allow_duplicate=True),
        Output("progress-interval", "disabled", allow_duplicate=True),
    ],
    Input("progress-interval", "n_intervals"),
    State("processing-state", "data"),
    prevent_initial_call=True
)
def process_next_batch(n_intervals, processing_state):
    if not processing_state['processing'] and not processing_state.get('processed_rows'):
        # Only return empty state if we've never processed anything
        return [], [], 0, "", "", processing_state, True

    # Process one row
    if processing_state['queue']:
        current_item = processing_state['queue'][0]
        row = current_item['row']
        
        # Process the row
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Only provide results you want to extract"},
                {"role": "user", "content": row[current_item['text_column']]},
            ],
            tools=current_item['tools'],
            tool_choice={"type": "function", "function": {"name": current_item['function_name']}},
        )
        
        tool_call = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        
        # Update column definitions if needed
        column_defs = processing_state.get('column_defs', []).copy()
        for key in tool_call.keys():
            if key not in [col["field"] for col in column_defs]:
                column_defs.append({"headerName": key, "field": key})
        
        # Add the processed row
        processed_row = {**row, **tool_call}
        processed_rows = processing_state.get('processed_rows', []) + [processed_row]
        
        # Update processing state
        new_queue = processing_state['queue'][1:]
        current_row = processing_state['current_row'] + 1
        total_rows = processing_state['total_rows']
        
        # Calculate progress
        progress = int((current_row / total_rows) * 100)
        
        # Update processing state
        new_state = {
            'processing': bool(new_queue),
            'queue': new_queue,
            'current_row': current_row,
            'total_rows': total_rows,
            'column_defs': column_defs,
            'processed_rows': processed_rows
        }
        
        return (
            column_defs,
            processed_rows,
            progress,
            f"{progress}%",
            f"Processing row {current_row} of {total_rows}",
            new_state,
            False
        )
    
    # If queue is empty, return the final state with the last processed data
    return (
        processing_state.get('column_defs', []),
        processing_state.get('processed_rows', []),
        100,
        "Complete!",
        f"Processed {processing_state['total_rows']} rows",
        {**processing_state, 'processing': False},
        True
    )


@app.callback(
    Output("upload-data", "children"),
    [Input("upload-data", "contents")],
    [State("upload-data", "filename")]
)
def update_upload_text(contents, filename):
    if contents is not None:
        return html.Div([
            html.I(className="fas fa-file-alt", style={'marginRight': '10px', 'color': VAPORWAVE_COLORS['secondary']}),
            f"Loaded: {filename}",
            html.Span(" (click or drag to replace)", style={'fontSize': '0.8em', 'color': VAPORWAVE_COLORS['accent']})
        ])
    return html.Div([
        "Drag and Drop or ",
        html.A("Select CSV Files", style={'color': VAPORWAVE_COLORS['primary']})
    ])


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)

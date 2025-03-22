# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "dash",
#     "dash-ag-grid",
#     "dash-bootstrap-components",
#     "openai",
#     "pandas",
#     "python-dotenv",
# ]
# ///
import base64
import io
import json
import os
import pathlib

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import openai
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output, State
from collections import deque
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# Check multiple locations for .env file
env_locations = [
    pathlib.Path.cwd() / '.env',  # Current working directory
    pathlib.Path(__file__).parent.parent / '.env',  # Project root directory
]

for env_path in env_locations:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break

# Prompts for function calling schema generation
FUNCTION_CALLING_SYS_PROMPT = {
    "role": "system",
    "content": """
# Instructions
You are a highly detailed researcher, who is trying to extract information from a large dataset.

You will be provided with high level instructions of what data to extract, and you are responsible
for creating JSON schema definitions for functions to extract the information you need.
""",
}

FUNCTION_CALLING_FEW_SHOTS_DICT = [
    {"role": "user", "content": "I need to extract the total population of all countries."},
    {
        "role": "assistant",
        "content": "{'properties': {'country': {'title': 'Country', 'type': 'string'}, 'population': {'title': 'Population', 'type': 'integer'}}, 'required': ['country', 'population'], 'title': 'CountryPopulation', 'type': 'object'}",
    },
    {
        "role": "user",
        "content": "I need to extract information about users. I want their id, name, signup timestamp and friends. Default name can be John Doe",
    },
    {
        "role": "assistant",
        "content": "{'properties': {'id': {'title': 'Id', 'type': 'integer'}, 'name': {'default': 'John Doe', 'title': 'Name', 'type': 'string'}, 'signup_ts': {'default': None, 'format': 'date-time', 'title': 'Signup Ts', 'type': 'string'}, 'friends': {'default': [], 'items': {'type': 'integer'}, 'title': 'Friends', 'type': 'array'}}, 'required': ['id'], 'title': 'User', 'type': 'object'}}",
    },
    {
        "role": "user",
        "content": "I need to extract information about survey responses, I want to extract a user name, their phone number if present, their satisfaction score, their criticisms. Make sure their satisfaction score is 1<=score<=10",
    },
    {
        "role": "assistant",
        "content": "{'properties': {'user_name': {'title': 'User Name', 'type': 'string'}, 'phone_number': {'default': None, 'title': 'Phone Number', 'type': 'string'}, 'satisfaction_score': {'title': 'Satisfaction Score', 'type': 'integer'}, 'criticisms': {'items': {'type': 'string'}, 'title': 'Criticisms', 'type': 'array'}}, 'required': ['user_name', 'satisfaction_score', 'criticisms'], 'title': 'SurveyResponse', 'type': 'object'}",
    },
]

# OpenAI client factory
def get_openai_client():
    # Check whether to use Azure OpenAI or regular OpenAI
    use_azure = os.getenv("USE_AZURE_OPENAI", "false").lower() == "true"
    
    if use_azure:
        # Azure OpenAI configuration
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
        
        # Verify required Azure settings
        if not api_key or not endpoint:
            raise ValueError("AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set when using Azure OpenAI")
            
        return openai.AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
    else:
        # Standard OpenAI configuration
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")  # Optional, for custom deployments
        
        # Verify required settings
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")
            
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
            
        return openai.Client(**client_kwargs)

# Model name mapping for Azure OpenAI deployments
def get_model_name(base_model_name):
    # Azure deployments may use different model names
    azure_model_mapping = {
        "gpt-4o": os.getenv("AZURE_GPT4O_DEPLOYMENT_NAME", "gpt-4o"),
        "gpt-4o-mini": os.getenv("AZURE_GPT4O_MINI_DEPLOYMENT_NAME", "gpt-4o-mini"),
    }
    
    use_azure = os.getenv("USE_AZURE_OPENAI", "false").lower() == "true"
    return azure_model_mapping.get(base_model_name, base_model_name) if use_azure else base_model_name

# Initialize the OpenAI API client
client = get_openai_client()

# Initialize the Dash app
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://use.fontawesome.com/releases/v5.15.4/css/all.css"
    ],  # Using CYBORG as base theme for dark mode and Font Awesome for icons
    assets_folder=str(pathlib.Path(__file__).parent / "assets")
)

# Define custom styles
# Standard dark mode color palette
COLORS = {
    'background': '#121212',
    'surface': '#1E1E1E',
    'primary': '#BB86FC',
    'secondary': '#03DAC6',
    'accent': '#3700B3',
    'error': '#CF6679',
    'text': '#FFFFFF',
    'text_secondary': '#B0B0B0'
}

# Keep original colors as reference
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
        'background': COLORS['background'],
        'minHeight': '100vh',
        'color': COLORS['text'],
        'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
    },
    children=[
        # ASCII Art Header
        dbc.Row(
            dbc.Col(
                html.Pre(
                    ASCII_HEADER,
                    style={
                        'color': COLORS['primary'],
                        'textAlign': 'center',
                        'fontFamily': 'monospace',
                        'whiteSpace': 'pre',
                        'margin': '20px 0',
                        'textShadow': f'2px 2px {COLORS["accent"]}',
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
                                    'color': COLORS['primary'],
                                    'fontWeight': '500',
                                    'marginBottom': '20px'
                                }
                            ),
                            dcc.Textarea(
                                id="input-box",
                                placeholder="Enter extraction instructions...",
                                value="I want to extract user names, and ids from this data",
                                style={
                                    'width': '100%',
                                    'height': '200px',
                                    'resize': 'vertical',
                                    'marginBottom': '20px',
                                    'background': COLORS['surface'],
                                    'color': COLORS['text'],
                                    'border': f'1px solid {COLORS["accent"]}',
                                    'borderRadius': '4px',
                                    'padding': '10px',
                                    'fontFamily': 'inherit'
                                }
                            ),
                            html.Button(
                                "Generate Schema", 
                                id="submit-fewshot-instruct",
                                style={
                                    'backgroundColor': COLORS['primary'],
                                    'border': 'none',
                                    'color': '#000',
                                    'padding': '10px 20px',
                                    'borderRadius': '4px',
                                    'marginBottom': '15px',
                                    'width': '100%',
                                    'fontWeight': '500',
                                    'cursor': 'pointer',
                                    'transition': 'all 0.2s ease'
                                }
                            ),
                            html.Div(id="output-box"),
                            dcc.Store(id="data-store"),
                        ],
                        style={
                            "padding": "20px",
                            "background": COLORS['surface'],
                            "borderRadius": "8px",
                            "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
                            "border": f"1px solid {COLORS['accent']}"
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
                                    html.A("Select CSV Files", style={'color': COLORS['primary']})
                                ]),
                                style={
                                    "width": "100%",
                                    "height": "60px",
                                    "lineHeight": "60px",
                                    "borderWidth": "2px",
                                    "borderStyle": "dashed",
                                    "borderColor": COLORS['secondary'],
                                    "borderRadius": "4px",
                                    "textAlign": "center",
                                    "margin": "10px 0 20px 0",
                                    "background": f"rgba(3, 218, 198, 0.1)",
                                },
                                multiple=False,
                            ),
                            dbc.Row([
                                dbc.Col(
                                    html.Label(
                                        "ID column",
                                        style={'color': COLORS['primary'], 'fontWeight': '500'}
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
                                            'backgroundColor': COLORS['surface'],
                                            'color': COLORS['text'],
                                            'border': f'1px solid {COLORS["accent"]}'
                                        }
                                    ),
                                    width=6,
                                ),
                            ]),
                            dbc.Row([
                                dbc.Col(
                                    html.Label(
                                        "Text column",
                                        style={'color': COLORS['primary'], 'fontWeight': '500'}
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
                                            'backgroundColor': COLORS['surface'],
                                            'color': COLORS['text'],
                                            'border': f'1px solid {COLORS["accent"]}'
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
                                            "backgroundColor": "rgba(187, 134, 252, 0.2)",
                                            "borderRadius": "4px",
                                        },
                                        className="mb-3",
                                        color="secondary",
                                    ),
                                    html.Div(id="progress-text", style={
                                        "color": COLORS['text_secondary'],
                                        "textAlign": "center",
                                        "marginBottom": "15px",
                                        "fontSize": "0.9rem"
                                    }),
                                ])
                            ]),
                            dcc.Store(id="progress-store", data={"current": 0, "total": 0}),
                            dcc.Interval(id='progress-interval', interval=500, disabled=True),  # 500ms interval
                            dcc.Store(id='processing-state', data={'processing': False, 'queue': [], 'current_row': 0, 'total_rows': 0}),
                            html.H5(
                                "Input Data",
                                style={
                                    'color': COLORS['primary'],
                                    'fontWeight': '500',
                                    'marginBottom': '15px'
                                }
                            ),
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
                                className="ag-theme-alpine-dark",
                                style={"marginBottom": "20px"}
                            ),
                            html.Button(
                                "Run Structured Extraction", 
                                id="run-extraction-button",
                                style={
                                    'backgroundColor': COLORS['secondary'],
                                    'border': 'none',
                                    'color': '#000',
                                    'padding': '10px 20px',
                                    'borderRadius': '4px',
                                    'width': '100%',
                                    'fontWeight': '500',
                                    'cursor': 'pointer',
                                    'transition': 'all 0.2s ease',
                                    'marginBottom': '20px'
                                }
                            ),
                            html.H5(
                                "Extraction Results",
                                style={
                                    'color': COLORS['primary'],
                                    'fontWeight': '500',
                                    'marginBottom': '15px'
                                }
                            ),
                            html.Div(id="column-summaries", style={
                                "marginBottom": "10px",
                                "padding": "10px",
                                "background": "rgba(3, 218, 198, 0.1)",
                                "borderRadius": "4px",
                                "border": f"1px solid {COLORS['secondary']}",
                                "display": "flex",
                                "flexWrap": "wrap",
                                "gap": "10px"
                            }),
                            dag.AgGrid(
                                id="ag-grid-out", 
                                columnDefs=[], 
                                rowData=[],
                                dashGridOptions={
                                    "defaultColDef": {
                                        "resizable": True,
                                        "sortable": True,
                                        "filter": True,
                                        "editable": True
                                    },
                                    "getRowId": "function(params) { return params.data.id || params.node.id; }"
                                },
                                dangerously_allow_code=True,
                                className="ag-theme-alpine-dark"
                            ),
                        ],
                        style={
                            "padding": "20px",
                            "background": COLORS['surface'],
                            "borderRadius": "8px",
                            "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
                            "border": f"1px solid {COLORS['accent']}"
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
            model=get_model_name("gpt-4o"),
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
                        'color': COLORS['primary'],
                        'fontWeight': '500',
                        'marginBottom': '15px'
                    }
                ),
                html.Div([
                    html.Div([
                        html.H6("Fields to Extract:", 
                            style={
                                'color': COLORS['secondary'],
                                'marginBottom': '10px',
                                'fontWeight': '500'
                            }
                        ),
                        html.Div([
                            html.Div([
                                html.Strong(field, 
                                    style={
                                        'color': COLORS['primary'],
                                        'marginRight': '10px'
                                    }
                                ),
                                html.Span(
                                    f"({properties.get('type', 'any')})",
                                    style={'color': COLORS['text_secondary'], 'fontSize': '0.9em'}
                                ),
                                html.Div(
                                    properties.get('description', ''),
                                    style={'color': COLORS['text'], 'fontSize': '0.8em', 'marginLeft': '20px'}
                                )
                            ], 
                            style={
                                'marginBottom': '10px',
                                'padding': '10px',
                                'background': 'rgba(187, 134, 252, 0.1)',
                                'borderRadius': '4px',
                                'border': f'1px solid {COLORS["accent"]}'
                            })
                            for field, properties in schema_json['properties'].items()
                        ]),
                        html.H6("Required Fields:", 
                            style={
                                'color': COLORS['secondary'],
                                'marginTop': '15px',
                                'marginBottom': '10px',
                                'fontWeight': '500'
                            }
                        ),
                        html.Div(
                            ", ".join(schema_json.get('required', [])),
                            style={
                                'color': COLORS['text'],
                                'padding': '10px',
                                'background': 'rgba(3, 218, 198, 0.1)',
                                'borderRadius': '4px',
                                'border': f'1px solid {COLORS["secondary"]}'
                            }
                        )
                    ], 
                    style={
                        'padding': '15px',
                        'background': COLORS['surface'],
                        'borderRadius': '8px',
                        'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
                        'border': f'1px solid {COLORS["accent"]}'
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

    # Process multiple rows in a batch
    if processing_state['queue']:
        # Define batch size - process up to 5 rows per interval
        batch_size = min(5, len(processing_state['queue']))
        batch_items = processing_state['queue'][:batch_size]
        
        # Initialize data for batch processing
        column_defs = processing_state.get('column_defs', []).copy()
        processed_rows = processing_state.get('processed_rows', []).copy()
        
        # Keep track of which columns are extracted and which are original
        extracted_columns = set()
        
        # Process batch of rows in parallel using asyncio if supported
        # For simplicity, we'll process them sequentially but in a batch
        for current_item in batch_items:
            row = current_item['row']
            
            try:
                # Process the row
                response = client.chat.completions.create(
                    model=get_model_name("gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": "Only provide results you want to extract"},
                        {"role": "user", "content": row[current_item['text_column']]},
                    ],
                    tools=current_item['tools'],
                    tool_choice={"type": "function", "function": {"name": current_item['function_name']}},
                )
                
                # Extract the tool call arguments from the API response
                if response.choices and response.choices[0].message.tool_calls:
                    tool_call = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
                    
                    # Track which columns are extracted
                    for key in tool_call.keys():
                        extracted_columns.add(key)
                        
                        # Update column definitions if needed
                        if key not in [col["field"] for col in column_defs]:
                            col_def = {
                                "headerName": key,
                                "field": key,
                            }
                            column_defs.append(col_def)
                    
                    # Create a processed row that merges original data with extracted data
                    processed_row = {**row}
                    
                    # Add extracted data to the row
                    for key, value in tool_call.items():
                        processed_row[key] = value
                    
                    processed_rows.append(processed_row)
                else:
                    # Handle case where no extraction was done (fallback)
                    processed_rows.append(row)
            except Exception as e:
                print(f"Error processing row: {e}")
                # Add the original row as a fallback if extraction fails
                processed_rows.append(row)
        
        # Update processing state
        new_queue = processing_state['queue'][batch_size:]
        current_row = processing_state['current_row'] + batch_size
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
            'processed_rows': processed_rows,
            'extracted_columns': list(extracted_columns)
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
            html.I(className="fas fa-file-alt", style={'marginRight': '10px', 'color': COLORS['secondary']}),
            f"Loaded: {filename}",
            html.Span(" (click or drag to replace)", style={'fontSize': '0.8em', 'color': COLORS['text_secondary']})
        ])
    return html.Div([
        "Drag and Drop or ",
        html.A("Select CSV Files", style={'color': COLORS['primary']})
    ])


# Hidden div to store column summary data
app.layout.children.append(html.Div(id="js-column-summaries", style={"display": "none"}))

# Interval for updating column summaries
app.layout.children.append(dcc.Interval(id="summaries-interval", interval=500, n_intervals=0))

# Callback to update column summaries display
@app.callback(
    Output("column-summaries", "children"),
    [Input("summaries-interval", "n_intervals"), Input("js-column-summaries", "children")]
)
def update_column_summaries(n_intervals, summaries_json):
    if not summaries_json:
        return []
    
    try:
        # Parse the JSON data
        summaries = json.loads(summaries_json)
        elements = []
        
        # Create a summary element for each column
        for col_id, summary in summaries.items():
            if col_id and summary:
                percentage = round(summary.get("fraction", 0) * 100)
                
                summary_div = html.Div(
                    [
                        html.Strong(f"{col_id}: "),
                        html.Span(f"{summary.get('checked', 0)}/{summary.get('total', 0)}"),
                        html.Span(f" ({percentage}%)", style={"marginLeft": "5px"})
                    ],
                    className="column-summary"
                )
                
                elements.append(summary_div)
        
        return elements
    except Exception as e:
        print(f"Error updating summaries: {e}")
        return []

# Run the app
if __name__ == "__main__":
    app.run(debug=True)

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

from data_rip.prompts import FUNCTION_CALLING_FEW_SHOTS_DICT, FUNCTION_CALLING_SYS_PROMPT

# Initialize the OpenAI API
client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define the layout
app.layout = dbc.Container(
    fluid=True,
    children=[
        dbc.Row([
            dbc.Col(
                width=4,
                children=[
                    html.Div(
                        [
                            html.H5("Enter detailed instructions for what types of question you want answered"),
                            dcc.Input(
                                id="input-box",
                                placeholder="Enter something...",
                                type="text",
                                value="I want to extract user names, and ids from this data",
                            ),
                            html.Button("Submit", id="submit-fewshot-instruct"),
                            html.Div(id="output-box"),  # Add the output div here
                            dcc.Store(id="data-store"),
                            html.Button("Run Structured Extraction", id="run-extraction-button"),
                        ],
                        style={"padding": "20px"},
                    )
                ],
                style={"background-color": "#f8f9fa", "height": "100vh"},
            ),
            dbc.Col(
                width=8,
                children=[
                    html.Div(
                        [
                            dcc.Upload(
                                id="upload-data",
                                children=html.Div(["Drag and Drop or ", html.A("Select CSV Files")]),
                                style={
                                    "width": "100%",
                                    "height": "60px",
                                    "lineHeight": "60px",
                                    "borderWidth": "1px",
                                    "borderStyle": "dashed",
                                    "borderRadius": "5px",
                                    "textAlign": "center",
                                    "margin": "10px",
                                },
                                multiple=False,
                            ),
                            dbc.Row([
                                dbc.Col(html.Label("ID column"), width=6),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="id-column-selector",
                                        options=[
                                            {"label": "Please Upload a File to choose columns", "value": "upload-file"},
                                        ],
                                        value="upload-file",
                                    ),
                                    width=6,
                                ),
                            ]),
                            dbc.Row([
                                dbc.Col(html.Label("Text column"), width=6),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="text-column-selector",
                                        options=[
                                            {"label": "Please Upload a File to choose columns", "value": "upload-file"},
                                        ],
                                        value="upload-file",
                                    ),
                                    width=6,
                                ),
                            ]),
                            dag.AgGrid(id="ag-grid", columnDefs=[], rowData=[]),
                            dag.AgGrid(id="ag-grid-out", columnDefs=[], rowData=[]),
                        ],
                        style={"padding": "20px"},
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

        # Return the completed message as the output and store it in the data store
        return [html.Div([html.H5("Completed Message:"), html.P(completed_message)]), completed_message]

    # If the submit button has not been clicked, return an empty div and None for the data store
    return [html.Div(), None]


@app.callback(
    [Output("id-column-selector", "options"), Output("text-column-selector", "options")],
    Input("upload-data", "contents"),
    [State("upload-data", "filename")],
)
def update_dropdowns(contents, filename):
    if contents is None:
        return [], []

    print(filename)
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        if "csv" in filename:
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        elif "xls" in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return [], []

        options = [{"label": col, "value": col} for col in df.columns]
        print(options)
        return options, options

    except Exception as e:
        print(e)
        return [], []


@app.callback(
    Output("ag-grid", "columnDefs"),
    Output("ag-grid", "rowData"),
    Input("id-column-selector", "value"),
    Input("text-column-selector", "value"),
    State("upload-data", "contents"),
    State("upload-data", "filename"),
)
def update_ag_grid(id_column, text_column, contents, filename):
    if id_column == "upload-file" or text_column == "upload-file" or contents is None:
        return [], []

    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        if "csv" in filename:
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        elif "xls" in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return [], []

        column_defs = [{"headerName": col, "field": col} for col in [id_column, text_column]]
        row_data = df[[id_column, text_column]].to_dict("records")

        return column_defs, row_data

    except Exception as e:
        print(e)
        return [], []


@app.callback(
    Output("ag-grid-out", "columnDefs"),
    Output("ag-grid-out", "rowData"),
    Input("run-extraction-button", "n_clicks"),
    State("data-store", "data"),
    State("ag-grid", "rowData"),
    State("ag-grid", "columnDefs"),
    State("id-column-selector", "value"),
    State("text-column-selector", "value"),
)
def run_structured_extraction(n_clicks, data, row_data, column_defs, id_column, text_column):
    if n_clicks is not None and data is not None and row_data:
        # Do this better....
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
        row_data_out = []
        for row in row_data:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Only provide results you want to extract"},
                    {"role": "user", "content": row[text_column]},
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": f"{function_name}"}},
            )
            tool_call = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
            # Extend the column defs with the new fields from the tool call
            for key in tool_call.keys():
                if key not in [col["field"] for col in column_defs]:
                    column_defs.append({"headerName": key, "field": key})
            # Append the row data with the new data from the tool call
            row_data_out.append({**row, **tool_call})
        return column_defs, row_data_out

    else:  # If the button has not been clicked or data is None or row_data is empty, return an empty div
        return [], []


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)

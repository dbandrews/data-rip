# data-rip

[![Release](https://img.shields.io/github/v/release/dbandrews/data-rip)](https://img.shields.io/github/v/release/dbandrews/data-rip)
[![Build status](https://img.shields.io/github/actions/workflow/status/dbandrews/data-rip/main.yml?branch=main)](https://github.com/dbandrews/data-rip/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/dbandrews/data-rip)](https://img.shields.io/github/commit-activity/m/dbandrews/data-rip)
[![License](https://img.shields.io/github/license/dbandrews/data-rip)](https://img.shields.io/github/license/dbandrews/data-rip)

A UI for structured data extraction using LLMs and function calling. Features include:

- Interactive data extraction with LLM-powered schema generation
- Support for both standard OpenAI and Azure OpenAI endpoints
- Rich extraction results with selectable items via checkboxes
- Column summary statistics showing fraction of selected items
- Dark mode UI with modern styling


# Env Setup

```
conda create -n data-rip python=3.11 -y # or pyenv etc
conda activate data-rip
pip install poetry==1.8.3
pip install -e .
```

# Running the App

## Package Version
```
python -m data_rip.app
```

## Standalone Version
A standalone single-file version is also available for easier deployment:

```
python app.py
```

The standalone version includes all the functionality in a single file and also supports environment variable configuration through .env files.

# Features

## Interactive Extraction
The app allows you to describe what data you'd like to extract in natural language. The LLM will generate a structured extraction schema based on your request.

## Checkbox Selection
Each cell in the extraction results includes a checkbox, allowing you to:
- Select/deselect specific data points of interest
- See the original extracted value alongside the checkbox
- Track selection statistics for each column

## Column Statistics
Above the extraction results grid, the app displays:
- The fraction of checked items for each column (e.g., "user_name: 3/10 (30%)")
- Updates in real-time as you toggle checkboxes
- Helps identify patterns and make data-driven decisions

## Screenshot

![Data-RIP Sample Screenshot](docs/data-rip-screenshot.png)

# Environment Variables

You can configure the application using environment variables or by creating a `.env` file in the project root directory. The application will automatically load variables from the .env file if it exists.

An example template is provided in `.env.example` - you can copy this file to `.env` and modify it with your own values.

## Example .env file

```
# OpenAI Configuration (Standard)
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://your-custom-endpoint.com/v1  # Optional

# Azure OpenAI Configuration
USE_AZURE_OPENAI=true  # Set to "true" to use Azure OpenAI
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_API_VERSION=2023-12-01-preview

# Azure Deployment Names
AZURE_GPT4O_DEPLOYMENT_NAME=your-gpt4o-deployment-name
AZURE_GPT4O_MINI_DEPLOYMENT_NAME=your-gpt4o-mini-deployment-name
```

## Available Environment Variables

### OpenAI Configuration
- `OPENAI_API_KEY`: Your OpenAI API key (required when using standard OpenAI)
- `OPENAI_BASE_URL`: Optional base URL for custom OpenAI-compatible endpoints

### Azure OpenAI Configuration
- `USE_AZURE_OPENAI`: Set to "true" to use Azure OpenAI instead of standard OpenAI
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key (required when using Azure)
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL (required when using Azure)
- `AZURE_OPENAI_API_VERSION`: Azure OpenAI API version (defaults to "2023-12-01-preview")

### Model Deployment Names (Azure OpenAI)
- `AZURE_GPT4O_DEPLOYMENT_NAME`: Deployment name for GPT-4o model in Azure (defaults to "gpt-4o")
- `AZURE_GPT4O_MINI_DEPLOYMENT_NAME`: Deployment name for GPT-4o-mini model in Azure (defaults to "gpt-4o-mini")

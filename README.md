# LawAsst Project Documentation

## Overview
The LawAsst project is a web application designed to assist users in managing documents and querying information using Snowflake's Cortex. The application leverages Streamlit for the user interface and integrates with Snowflake for data storage and processing.

## File Structure
- **`app.py`**: The main application script that sets up the Streamlit interface, handles file uploads, and processes user queries.
- **`dataingestion.py`**: Contains the function for uploading and chunking files into Snowflake.

## Main Components

### app.py
- **Snowflake Connection**
  - `init_snowflake_connection()`: Initializes a connection to Snowflake using credentials from Streamlit secrets.

- **Configuration Options**
  - `config_options()`: Provides a sidebar for model selection and category filtering.

- **Query Processing**
  - `get_similar_chunks_search_service(query)`: Queries the search service for similar chunks based on user input.
  - `create_prompt(myquestion)`: Constructs a prompt for querying Snowflake Cortex.
  - `complete(myquestion)`: Sends the prompt to Snowflake Cortex and retrieves the response.

- **File Upload**
  - `upload_to_snowflake(session, file, stage_name)`: Uploads a file to a specified Snowflake stage.

- **Main Function**
  - `main()`: Sets up the Streamlit interface, handles user input, and displays results.

### dataingestion.py
- **File Upload and Chunking**
  - `upload_and_chunk_file(session, file, stage_name)`: Uploads a file to Snowflake, determines its relative path, and chunks it into `docs_chunks_table`.

## Usage
1. Run the Streamlit application.
2. Upload documents to Snowflake using the file uploader.
3. Enter queries to retrieve information from the uploaded documents.

## Requirements
- Python 3.x
- Streamlit
- Snowflake Connector

## Setup
1. Ensure you have Python 3.x installed.
2. Install the required packages using `pip install -r requirements.txt`.
3. Set up Streamlit secrets for Snowflake connection credentials.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

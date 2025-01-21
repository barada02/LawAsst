import streamlit as st


def upload_and_chunk_file(session, file, stage_name):
    """Uploads a file to a Snowflake stage and chunks it into the docs_chunks_table for the uploaded file only."""
    try:
        # Save the uploaded file temporarily
        temp_file_path = file.name
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file.read())

        # Upload the file to the stage
        session.sql(f"PUT 'file://{temp_file_path}' {stage_name} AUTO_COMPRESS = FALSE").collect()
        st.success(f"File '{file.name}' uploaded successfully to stage {stage_name}.")
        
        # Find the relative path of the uploaded file
        relative_path_result = session.sql(f"LIST {stage_name}").collect()
        relative_path = None
        for row in relative_path_result:
            if row['name'].endswith(file.name):
                relative_path = row['name']
                break
        
        if not relative_path:
            raise Exception(f"Unable to find the relative path for '{file.name}' in stage {stage_name}.")
        
        # Chunk the specific file and insert into docs_chunks_table
        query = (f"""
        INSERT INTO docs_chunks_table (relative_path, size, file_url,
                                       scoped_file_url, chunk)
        SELECT '{relative_path}' AS relative_path,
               size,
               file_url, 
               build_scoped_file_url('{stage_name}', '{relative_path}') AS scoped_file_url,
               func.chunk AS chunk
        FROM 
            DIRECTORY('{stage_name}'),
            TABLE(text_chunker (TO_VARCHAR(SNOWFLAKE.CORTEX.PARSE_DOCUMENT('{stage_name}', 
                                      '{relative_path}', {{'mode': 'LAYOUT'}})))) AS func;
        """)
        session.sql(query).collect()
        st.success(f"File '{file.name}' has been chunked and inserted into docs_chunks_table.")
    
    except Exception as e:
        st.error(f"Error during upload or chunking: {e}")

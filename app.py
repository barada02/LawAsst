import streamlit as st
from snowflake.snowpark import Session
from snowflake.core import Root
import pandas as pd
import json
from dataingestion import upload_and_chunk_file

pd.set_option("max_colwidth",None)

### Default Values
NUM_CHUNKS = 3 # Num-chunks provided as context. Play with this to check how it affects your accuracy

# service parameters
CORTEX_SEARCH_DATABASE = "LAWASST_CORTEX_SEARCH"
CORTEX_SEARCH_SCHEMA = "DATA"
CORTEX_SEARCH_SERVICE = "CC_SEARCH_SERVICE_CS"
stage_name = "@docs"

######
######

# columns to query in the service
COLUMNS = [
    "chunk",
    "relative_path",
    "category"
]


@st.cache_resource
def init_snowflake_connection():
    """Initialize Snowflake connection with error handling"""
    try:
        # Get connection parameters from secrets
        snowflake_config = st.secrets["connections"]["snowflake"]
        
        # Create Snowpark session
        session = Session.builder.configs({
            "account": snowflake_config["account"],
            "user": snowflake_config["user"],
            "password": snowflake_config["password"],
            "role": snowflake_config["role"],
            "warehouse": snowflake_config["warehouse"],
            "database": snowflake_config["database"],
            "schema": snowflake_config["schema"]
        }).create()
        
        root = Root(session)
        svc = root.databases[CORTEX_SEARCH_DATABASE].schemas[CORTEX_SEARCH_SCHEMA].cortex_search_services[CORTEX_SEARCH_SERVICE]
        return session, root, svc
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        st.error("Please check your credentials in .streamlit/secrets.toml")
        return None, None, None

# Initialize connection
session, root, svc = init_snowflake_connection()

### Functions
     
def config_options():

    st.sidebar.selectbox('Select your model:',(
                                    'mixtral-8x7b',
                                    'snowflake-arctic',
                                    'mistral-large',
                                    'llama3-8b',
                                    'llama3-70b',
                                    'reka-flash',
                                     'mistral-7b',
                                     'llama2-70b-chat',
                                     'gemma-7b'), key="model_name")

    categories = session.sql("select category from docs_chunks_table group by category").collect()

    cat_list = ['ALL']
    for cat in categories:
        cat_list.append(cat.CATEGORY)
            
    st.sidebar.selectbox('Select what products you are looking for', cat_list, key = "category_value")

    st.sidebar.expander("Session State").write(st.session_state)

def get_similar_chunks_search_service(query):

    if st.session_state.category_value == "ALL":
        response = svc.search(query, COLUMNS, limit=NUM_CHUNKS)
    else: 
        filter_obj = {"@eq": {"category": st.session_state.category_value} }
        response = svc.search(query, COLUMNS, filter=filter_obj, limit=NUM_CHUNKS)

    st.sidebar.json(response.json())
    
    return response.json()  

def create_prompt (myquestion):

    if st.session_state.rag == 1:
        prompt_context = get_similar_chunks_search_service(myquestion)
  
        prompt = f"""
           You are an expert chat assistance that extracs information from the CONTEXT provided
           between <context> and </context> tags.
           When ansering the question contained between <question> and </question> tags
           be concise and do not hallucinate. 
           If you don´t have the information just say so.
           Only anwer the question if you can extract it from the CONTEXT provideed.
           
           Do not mention the CONTEXT used in your answer.
    
           <context>          
           {prompt_context}
           </context>
           <question>  
           {myquestion}
           </question>
           Answer: 
           """

        json_data = json.loads(prompt_context)

        relative_paths = set(item['relative_path'] for item in json_data['results'])
        
    else:     
        prompt = f"""[0]
         'Question:  
           {myquestion} 
           Answer: '
           """
        relative_paths = "None"
            
    return prompt, relative_paths

def complete(myquestion):

    prompt, relative_paths =create_prompt (myquestion)
    cmd = """
            select snowflake.cortex.complete(?, ?) as response
          """
    
    df_response = session.sql(cmd, params=[st.session_state.model_name, prompt]).collect()
    return df_response, relative_paths


def upload_to_snowflake(session, file, stage_name):
    """Uploads a file to a specified Snowflake stage."""
    try:
        # Save the uploaded file temporarily
        temp_file_path = f"temp_{file.name}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file.read())

        # Upload the file to the stage
        session.sql(f"PUT 'file://{temp_file_path}' {stage_name}").collect()
        st.success(f"File '{file.name}' uploaded successfully to stage {stage_name}.")

    except Exception as e:
        st.error(f"Error uploading file: {e}")




def main():
    
    st.title(f":speech_balloon: Chat Document Assistant with Snowflake Cortex")

    # File uploader
    uploaded_file = st.file_uploader("Choose a file to upload", type=["pdf", "csv", "txt", "json"])

    # Stage name input
    stage_name = st.text_input("Enter Snowflake Stage Name (e.g., @docs):", "@docs")

    # Upload button
    if st.button("Upload"):
        if uploaded_file and stage_name:
            upload_and_chunk_file(session, uploaded_file, stage_name)
        else:
            st.error("Please provide both a file and a stage name.")
    
    st.write("This is the list of documents you already have and that will be used to answer your questions:")
    docs_available = session.sql("ls @docs").collect()
    list_docs = []
    for doc in docs_available:
        list_docs.append(doc["name"])
    st.dataframe(list_docs)

    config_options()

    st.session_state.rag = st.sidebar.checkbox('Use your own documents as context?')

    question = st.text_input("Enter question", placeholder="Is there any special lubricant to be used with the premium bike?", label_visibility="collapsed")
    

    if question:
        response, relative_paths = complete(question)
        res_text = response[0].RESPONSE
        st.markdown(res_text)

        if relative_paths != "None":
            with st.sidebar.expander("Related Documents"):
                for path in relative_paths:
                    cmd2 = f"select GET_PRESIGNED_URL(@docs, '{path}', 360) as URL_LINK from directory(@docs)"
                    df_url_link = session.sql(cmd2).to_pandas()
                    url_link = df_url_link._get_value(0,'URL_LINK')
        
                    display_url = f"Doc: [{path}]({url_link})"
                    st.sidebar.markdown(display_url)
                
if __name__ == "__main__":
    main()
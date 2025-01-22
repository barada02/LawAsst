import streamlit as st
from snowflake.snowpark import Session
from snowflake.core import Root
import json

class RAG:
    def __init__(self, snowflake_config, model_name):
        self.session = self.init_snowflake_connection(snowflake_config)
        self.model_name = model_name

    def init_snowflake_connection(self, snowflake_config):
        try:
            session = Session.builder.configs(snowflake_config).create()
            return session
        except Exception as e:
            st.error(f"Failed to connect to Snowflake: {str(e)}")
            return None

    def retrieve_documents(self, query, limit=3):
        root = Root(self.session)
        svc = root.databases["LAWASST_CORTEX_SEARCH"].schemas["DATA"].cortex_search_services["CC_SEARCH_SERVICE_CS"]
        response = svc.search(query, ["chunk", "relative_path", "category"], limit=limit)
        return response.json()

    def generate_response(self, query, context):
        prompt = self.create_prompt(query, context)
        cmd = "select snowflake.cortex.complete(?, ?) as response"
        df_response = self.session.sql(cmd, params=[self.model_name, prompt]).collect()
        return df_response[0].RESPONSE

    def create_prompt(self, query, context):
        return f"""
        You are an expert chat assistant. Use the CONTEXT provided to answer the QUESTION.
        
        <context>
        {context}
        </context>
        <question>
        {query}
        </question>
        Answer:
        """

    def process_query(self, query):
        context = self.retrieve_documents(query)
        response = self.generate_response(query, context)
        return response

# Usage
snowflake_config = st.secrets["connections"]["snowflake"]
rag = RAG(snowflake_config, "mistral-large2")
response = rag.process_query("My client was charged with destroying an aircraft. What's the maximum penalty?")
st.markdown(response)

import os
import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain_core.prompts import ChatPromptTemplate
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from urllib.parse import quote_plus
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()
st.set_page_config(page_title="LangChain: Chat with SQL DB",page_icon="🦜")
st.title("🦜 LangChain: Chat with SQL DB")
LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQL"
radio_opt=["Use SQLLite 3 Database - Student.db","Connect to your MySQL Database"]
selected_opt=st.sidebar.radio(label="Choose the DB which you want to chat",options=radio_opt)
if radio_opt.index(selected_opt)==1:
    db_uri=MYSQL
    mysql_host=st.sidebar.text_input("Provide MySQL Host")
    mysql_user=st.sidebar.text_input("MYSQL User")
    mysql_password=st.sidebar.text_input("MYSQL password",type="password")
    mysql_db=st.sidebar.text_input("MySQL database")
else:
    db_uri=LOCALDB
api_key=st.secrets["GROQ_API_KEY"]
if not db_uri:
    st.info("Please enter the database information and uri")
if not api_key:
    st.info("Please add the groq api key")
## LLM model
llm=ChatGroq(groq_api_key=api_key,model_name="llama-3.1-8b-instant",streaming=True)
@st.cache_resource(ttl="2h")
def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/"Student.db").absolute()
        print(dbfilepath)
        creator=lambda:sqlite3.connect(f"file:{dbfilepath}?mode=ro",uri=True)
        return SQLDatabase(create_engine("sqlite:///",creator=creator))
    elif db_uri==MYSQL:
        if "@" in mysql_host:
            st.error(f"Invalid host: {mysql_host}")
            st.stop()
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))  
if db_uri==MYSQL:
    db=configure_db(db_uri,mysql_host,mysql_user,mysql_password,mysql_db)
else:
    db=configure_db(db_uri)
# Toolkit
toolkit=SQLDatabaseToolkit(db=db,llm=llm)
system_prompt = """
You are a highly accurate SQL assistant integrated into a chat application.
Your task is to understand user questions and generate correct SQL queries based on the given database schema, then provide clear answers from the results.
Rules you MUST follow:
- Always generate valid SQL queries compatible with the database.
- Use ONLY the provided database schema do not assume extra tables or columns.
- Prefer simple, optimized queries over complex ones.
- Always limit query results to a maximum of 10 rows unless the user explicitly requests more.
- Do NOT return unnecessary explanation of SQL unless asked.
- Do NOT ask the user to repeat or clarify unless the question is impossible to interpret.
- If the question is not clear make a reasonable assumption and proceed.
- Convert results into clear, short, human readable answers.
- Avoid long responses, keep answers concise and relevant.
- If no data is found, clearly say "No relevant data found in the database."

You are part of a Streamlit-based SQL chatbot powered by a language model.
"""
agent=create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    prefix=system_prompt
)
if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"]=[{"role":"assistant","content":"How can I help you?"}]
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])
user_query=st.chat_input(placeholder="Ask anything from the database")
if user_query:
    st.session_state.messages.append({"role":"user","content":user_query})
    st.chat_message("user").write(user_query)
    with st.chat_message("assistant"):
        streamlit_callback=StreamlitCallbackHandler(st.container())
        response=agent.run(user_query,callbacks=[streamlit_callback])
        st.session_state.messages.append({"role":"assistant","content":response})
        st.write(response)

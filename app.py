from dotenv import load_dotenv
from data_processor import run_chat
import streamlit as st

load_dotenv()


st.set_page_config(page_title='My App', page_icon=':smiley:')
st.title('My App')
st.sidebar.title('Settings')


with st.sidebar:
    index_name = st.text_input("Index name:", value="tester-01")
    namespace = st.text_input("namespace:", value="regulations")


run_chat(
    index_name=index_name,
    namespace=namespace
)

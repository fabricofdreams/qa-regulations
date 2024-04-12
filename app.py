from dotenv import load_dotenv, dotenv_values
from data_processor import run_chat, load_bucket_with_file
import streamlit as st

load_dotenv()

env_vars = dotenv_values('.env')
aws_bucket_name = env_vars.get('AWS_BUCKET_NAME')


st.set_page_config(page_title='My App', page_icon=':smiley:')
st.title('My App')
st.sidebar.title('Settings')


with st.sidebar:
    index_name = st.text_input("Index name:", value="tester-01")
    namespace = st.text_input("namespace:", value="regulations")
    selection = st.radio(
        label="Do you need to load additional data?",
        options=["No", "Yes"],
        key="options",
        horizontal=True
    )
    if selection == "Yes":
        pdf_file = st.file_uploader("Pdf file:")
        load_bucket_with_file(pdf_file=pdf_file, bucket_name=aws_bucket_name)


run_chat(
    index_name=index_name,
    namespace=namespace
)

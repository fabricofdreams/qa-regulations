import streamlit as st
from data_processor import load_bucket_with_file
from data_loader import get_metadata
from dotenv import dotenv_values
import json

from utils.processes import upload_fileobj_to_s3


vars_env = dotenv_values(".env")
aws_bucket_name = vars_env.get("AWS_BUCKET_NAME")

if "upload_ready" not in st.session_state:
    st.session_state.upload_ready = False

if "pdf_ready" not in st.session_state:
    st.session_state.pdf_ready = False

with open('dictionaries.json', 'r') as json_file:
    dictionaries = json.load(json_file)
genres_dict = dictionaries['genre_dict']
themes_dict = dictionaries['theme_dict']
status_dict = dictionaries['status_dict']
months_dict = dictionaries['months']

st.title("Upload Files")
index_name = st.text_input("Index name:", value="tester-01")
namespace = st.text_input("namespace:", value="regulations")

st.divider()

file_name = get_metadata(genres_dict, status_dict,
                         themes_dict, months_dict)

if file_name:
    st.write(file_name)
    pdf_file = st.file_uploader(
        "Pdf file:", accept_multiple_files=False, help="Select a PDF file only.")

    if pdf_file is not None:
        st.success("Ready")
        st.session_state.pdf_ready = False
    else:
        st.warning("Still waiting for PDF file")
        st.session_state.pdf_ready = True

    st.divider()
    st.subheader("Upload PDF file")

    print(f"Ready to upload file: {file_name}")

    if st.button('Load file', disabled=st.session_state.pdf_ready) and st.session_state.upload_ready is not True:
        with st.spinner('Processing...'):
            # to create s3 item
            if upload_fileobj_to_s3(file_obj=pdf_file, bucket_name=aws_bucket_name, object_name=file_name):
                st.success("File is already uploaded")
                st.session_state.upload_ready = True
                st.session_state.pdf_ready = False
                if st.button("Rerun"):
                    st.rerun()
            else:
                print("Faile to upload file to S3")
                st.session_state.upload_ready = False
                st.session_state.pdf_ready = True

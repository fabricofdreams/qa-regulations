import streamlit as st
from data_loader import assemble_metadata_and_return_filename, store_metadata_in_dynamodb, upsert_embeddings_to_pinecone
from dotenv import dotenv_values
import json
from utils.processes import upload_fileobj_to_s3


vars_env = dotenv_values(".env")
aws_bucket_name = vars_env.get("AWS_BUCKET_NAME")

if "pdf_ready" not in st.session_state:
    st.session_state.pdf_ready = False

if "metadata_ready" not in st.session_state:
    st.session_state.metadata_ready = False

if "bucket_ready" not in st.session_state:
    st.session_state.bucket_ready = False

if "bucket_button" not in st.session_state:
    st.session_state.bucket_button = False

if "database_button" not in st.session_state:
    st.session_state.database_button = False

if "vector_button" not in st.session_state:
    st.session_state.vector_button = False

with open('dictionaries.json', 'r') as json_file:
    dictionaries = json.load(json_file)
genres_dict = dictionaries['genre_dict']
themes_dict = dictionaries['theme_dict']
status_dict = dictionaries['status_dict']
months_dict = dictionaries['months']
index_dict = dictionaries['index_name']

index_values = [key for key in index_dict]

st.title("Upload Files")
with st.sidebar:
    index_name = st.selectbox("Index name:", options=index_values, index=0)
    namespace = st.text_input("namespace:", value="regulations")

    pdf_file = st.file_uploader(
        "Pdf file:", accept_multiple_files=False, help="Select a PDF file only.")
    if pdf_file is not None:
        upload_file_message = "PDF is ready!"
        st.success(upload_file_message)
        st.session_state.pdf_ready = True
    else:
        upload_file_message = "Load PDF file!"
        st.warning(upload_file_message)
        st.session_state.pdf_ready = False

tab1, tab2, tab3, tab4 = st.tabs(
    ["Metadata", "Bucket", "Database", "Vectorstore"])

with tab1:
    st.subheader("Assemble metadata")
    collection = assemble_metadata_and_return_filename(genres_dict, status_dict,
                                                       themes_dict, months_dict)
    if collection is not None:
        file_name, metadata = collection
        metadata_message = f"Ready to upload with file name: {file_name}"
        st.success(metadata_message)
        st.session_state.metadata_ready = True
    else:
        metadata_message = "Complete metadata!"
        st.session_state.metadata_ready = False

with tab2:
    st.subheader("Store PDF into an AWS Bucket")
    if st.session_state.pdf_ready and st.session_state.metadata_ready and st.session_state.bucket_button:
        st.session_state.bucket_button = False
    else:
        st.session_state.bucket_button = True

    if st.button('Load file', disabled=st.session_state.bucket_button, type="primary") and st.session_state.metadata_ready is True:
        with st.spinner('Uploading file...'):
            # to create s3 item
            if upload_fileobj_to_s3(file_obj=pdf_file, bucket_name=aws_bucket_name, object_name=file_name):
                st.success("File is already uploaded")
                st.session_state.bucket_ready = True
            else:
                print("Faile to upload file to S3")
                st.session_state.bucket_ready = False

        st.session_state.bucket_button = False

    if st.session_state.pdf_ready == False:
        st.warning(upload_file_message)
    else:
        st.success(upload_file_message)

    if st.session_state.metadata_ready == False:
        st.warning(metadata_message)
    else:
        st.success(metadata_message)

with tab3:
    st.subheader("Store metadata")
    if st.session_state.metadata_ready and st.session_state.database_button:
        st.session_state.database_button = False
    else:
        st.session_state.database_button = True

    if st.button('Feed database', type="primary", disabled=st.session_state.database_button):
        with st.spinner('Feeding database...'):
            response = store_metadata_in_dynamodb(table_name="EnvRegDB", region="us-east-2",
                                                  bucket_name=aws_bucket_name, file_name=file_name,
                                                  metadata=metadata, genres_dict=genres_dict,
                                                  status_dict=status_dict, themes_dict=themes_dict)
            if response == 200:
                st.success("Item inserted successfully")
            else:
                error = f"ERROR: {response}"
                st.error(error)
        st.session_state.database_button = False

    if st.session_state.metadata_ready == True:
        st.success(metadata_message)
    else:
        st.warning(metadata_message)

with tab4:
    st.subheader("Create Vectorstore")
    if st.session_state.pdf_ready and st.session_state.metadata_ready and st.session_state.vector_button:
        st.session_state.vector_button = False
    else:
        st.session_state.vector_button = True
    if st.button('Create vector and upsert it', type="primary", disabled=st.session_state.vector_button):
        with st.spinner('Upserting file...'):
            if upsert_embeddings_to_pinecone(
                    index_name=index_name, namespace=namespace, dimensions=1536, pdf_file=pdf_file, metadata=metadata):
                st.success("Vector already upserted!")
            else:
                st.error("Try again")

        st.session_state.vector_button = False

    if st.session_state.pdf_ready == False:
        st.warning(upload_file_message)
    else:
        st.success(upload_file_message)

    if st.session_state.metadata_ready == False:
        st.warning(metadata_message)
    else:
        st.success(metadata_message)

import streamlit as st
import time
from langchain_core.messages import AIMessage, HumanMessage
from utils.processes import (get_text_from_pdf,
                             openai_embed_data,
                             split_text_into_chunks,
                             create_records_to_upsert,
                             pinecone_store_data,
                             get_response,
                             upload_fileobj_to_s3,
                             openai_embed_document,
                             create_vector_from_documents_to_upsert)


@st.cache_resource(show_spinner=False)
def prepare_data(pdf_file, index_name, namespace, metadata):
    with st.sidebar:
        with st.spinner('Preparing data...'):
            time.sleep(0.5)
            docs = get_text_from_pdf(pdf_file=pdf_file)
            st.success('Data loaded.')
            time.sleep(0.5)
            lst_of_chunks = split_text_into_chunks(docs=docs)
            st.success('Data chunked.')
            time.sleep(0.5)
            emmbeddings = openai_embed_data(lst_chunks=lst_of_chunks)
            st.success('Data emmbedded.')
            time.sleep(0.5)
            vector = create_records_to_upsert(
                lst_of_chunks=lst_of_chunks,
                embeddings=emmbeddings,
                metadata=metadata
            )
            st.success('Data prepared.')
            pinecone_store_data(vectors=vector,
                                index_name=index_name,
                                namespace=namespace,
                                dimension=1536)
            data_prepared = True
            return data_prepared


def run_chat(index_name, namespace):
    """
    Facilitates a chat interaction between a user and an AI. It manages user input, chat history,
    and AI responses, updating the conversation dynamically within a Streamlit application.

    Args:
    index_name (str): The name of the index for the AI to use in generating responses.
    namespace (str): The context or scope within which the AI generates responses.

    This function uses the Streamlit library to manage the web application's state and UI components.
    """
    st.write('This is the main content.')
    user_question = st.chat_input('Ask me a question.')

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    if user_question is not None and user_question != "":
        input_message = HumanMessage(content=user_question)
        st.session_state["chat_history"].append(input_message)
        response = AIMessage(content=get_response(
            query=user_question,
            index_name=index_name,
            namespace=namespace))
        st.session_state["chat_history"].append(response)

        for msg in st.session_state["chat_history"]:
            if isinstance(msg, HumanMessage):
                with st.chat_message("Human"):
                    st.write(msg.content)
            else:
                with st.chat_message("AI"):
                    st.write(msg.content)


def load_bucket_with_file(pdf_file, bucket_name, file_name):
    if st.button('Load file'):
        with st.spinner('Processing...'):

            if upload_fileobj_to_s3(file_obj=pdf_file, bucket_name=bucket_name, object_name=file_name):
                return True
            else:
                print("Faile to upload file to S3")
                return False

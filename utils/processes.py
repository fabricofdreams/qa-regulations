from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings
import voyageai
from pinecone import Pinecone, ServerlessSpec
import time
from uuid import uuid4
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain_community.document_loaders import AmazonTextractPDFLoader
import boto3
from botocore.exceptions import NoCredentialsError
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
import requests

"""Functions for main processes:
    1- Get text from a PDF file
    2- Split text into chunks/documents for embedding preparation
    3- Embeding chunks using Anthropic, SentenceTransformer
    4- Store vector into Pinecone index
    5- Delete all vector from Pinecone Index
    6- Get context from Pinecone Index
    7- Get response to user query by augmenting it with text from Pinecone Index
    8- Create iterable object to upsert to Pinecone Index
    9- Prepare data to upsert
    """

load_dotenv()


def get_text_from_pdf(pdf_file):
    """
    Get the text from a PDF
    """
    reader = PdfReader(pdf_file)
    page = reader.pages
    all_text = ""
    for p in range(len(page)):
        all_text += page[p].extract_text()
    return all_text


def split_text_into_chunks(docs, chunk_size=1000, chunk_overlap=100):
    """
    Split PDF text into chunks of specified size for embedding
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return text_splitter.split_text(docs)


def split_text_into_documents(docs, chunk_size=1000, chunk_overlap=100):
    """
    Split PDF text into chunks of specified size for embedding
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return text_splitter.split_documents(docs)


def anthropic_emmbed_data(lst_of_chunks):
    """
    Embed chunks of text using Anthropic model and
    feed with the text from chunks the metadata.
    """
    vo = voyageai.Client()
    result = vo.embed(lst_of_chunks, model="voyage-large-2",
                      input_type=None)
    return result.embeddings


def sentence_transformer_embed_data(lst_of_chunks):
    """
    Embed chunks of text using SentenceTransformer model.
    Sentences are passed as a list of string.

    Args:
        lst_of_chunks (list): List of chunks of text.
    Returns:
        vector (float): List of values from 0 to 1.
    """
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode(lst_of_chunks)


def pinecone_store_data(vectors, index_name, namespace, dimensions=1536):
    """
    Store vectors into Pinecone index.
    """
    pc = Pinecone()
    if index_name not in pc.list_indexes().names():
        # create index
        pc.create_index(
            name=index_name,
            dimension=dimensions,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1",
            ),
        )
    # wait for index to be initialized
    while not pc.describe_index(name=index_name).status['ready']:
        time.sleep(1)
    index = pc.Index(name=index_name)
    # time.sleep(1)
    # print("Before upserting: ", index.describe_index_stats())
    # upsert vectors
    index.upsert(vectors=vectors, namespace=namespace)
    time.sleep(10)
    print("Ready upsertion: ", index.describe_index_stats())


def pinecone_delete_all_from_namespace(index_name, namespace):
    """
    Delete all vectors from Pinecone index with given namespace
    """
    pc = Pinecone()
    index = pc.Index(index_name)
    index.delete(delete_all=True, namespace=namespace)


def pinecone_get_context(index_name, namespace, query_vector, top_k=10):
    pc = Pinecone()
    index = pc.Index(index_name)
    # stats = index.describe_index_stats()
    # dimension = stats['dimension']
    # index_fullness = stats['index_fullness']
    # namespaces = stats['namespaces']
    # total_vector_count = stats['total_vector_count']
    # print(
    #     f"Index dimension: {dimension} | Index fullnesss: {index_fullness} | Total vectors: {total_vector_count} | Namespaces: {namespaces}")
    if pc.describe_index(index_name).status['ready']:
        try:
            results = index.query(
                namespace=namespace,
                vector=query_vector,
                top_k=top_k,
                include_values=False,
                include_metadata=True,
                filter=None
            )

        except Exception as e:
            print(e)
            return None
    else:
        print("Index not ready yet")

    return results


def get_response(query, index_name, namespace):
    """
    Generates a response to a user query by augmenting it with contextual information from a Pinecone database
    and using an OpenAI model to generate a tailored answer.

    Args:
        query (str): The text of the user's query.
        index_name (str): Pinecone index name from which to retrieve contextual data.
        namespace (str): Pinecone namespace associated with the index.

    Returns:
        str: The AI-generated response to the query.
    """
    query_vector = openai_embed_data(lst_chunks=[query])
    context = pinecone_get_context(index_name=index_name,
                                   namespace=namespace,
                                   query_vector=query_vector)
    contexts = [item['metadata']['text'] for item in context['matches']]
    augmented_query = "\n\n---\n\n".join(contexts)+"\n\n-----\n\n"+query
    primer = f"""You are Q&A senir expert legal advisor bot. A highly 
    intelligent system that answers user questions based on the information 
    provided by the user above each question. If the information can not be found
    in the information provided by the user you truthfully say "I don't know. Check if the
    database us uptodated.".
    
    YOU MUST translate de answer to Spanish.

    Please provide the following information:

    **Regulation Title**: [Enter the title]
    **Agency**: [The name of the regulatory agency]
    **Promulgated on**: [Date of promulgation]
    **Code**: [Code number]
    **Article Number**: [Enter the number of the article you're inquiring about.]
    **Subsection Numbers**: [Enter the numbers of the subsections.]
    """
    client = OpenAI()

    res = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": primer},
            {"role": "user", "content": augmented_query}
        ]
    )
    return res.choices[0].message.content


def create_records_to_upsert(lst_of_chunks, embeddings, metadata):
    """
    Create a list of dictionaries with metadata and embeddings.

    Args:
        lst_of_chunks (str): List of chunks of text before to embed.
        embeddings (float): List of vectors or embeddings that maps to the list of chunks.
        metadata (json): Json file with the metadata related to the list of chunks.
    Returns:
        list (iterables): List with index, vector and metadata.

    """
    ids = []
    metadatas = []
    for i in range(len(lst_of_chunks)):
        ids.append(f"{metadata['code']}-{str(uuid4())}")
        metadatas.append({
            ** metadata,
            'text': lst_of_chunks[i]
        })
    return list(zip(ids, embeddings, metadatas))


def create_vector_from_documents_to_upsert(documents, embeddings, metadata):
    """
    Takes Document type file, converts to list of texts, include embeddings
    and metadata to create a list ready to upsert in a Pinecone index

    Args:
        documents (Document): Output of text_splitter.
        embeddings (float): List of floats with a dimension.
        metadata (json): Json file with metadata.
    Returns:
        list (iterables): List with index, vector and metadata.
    """
    ids = []
    metadatas = []
    content = [doc.page_content for doc in documents]
    for i in range(len(content)):
        ids.append(f"{metadata['code']}-{str(uuid4())}")
        metadatas.append({
            ** metadata,
            'text': content[i]
        })
    return list(zip(ids, embeddings, metadatas))


def openai_embed_data(lst_chunks, dimensions=1536):
    """Embed text using the model name provided by OpenAI

    Args:
        lst_chunks (str): List of chunks of text
        dimensions (int, optional): Vector size. Defaults to 1536.

    Returns:
        list (float): List of floats from 0 to 1.
    """
    model_name = 'text-embedding-3-small'
    embeddings = OpenAIEmbeddings(
        model=model_name,
        dimensions=dimensions
    )
    vectorstore = embeddings.embed_documents(lst_chunks)
    return vectorstore


def openai_embed_document(documents, dimensions=1536):
    """
    Generates embeddings for a list of documents using OpenAI's embedding model.

    Args:
        documents (list): A list of documents where each document is expected to have a 'page_content' attribute.
        dimensions (int, optional): The number of dimensions for each embedding vector. Defaults to 1536.

    Returns:
        list of list of float: A list containing the embedding vectors for each document's content.
    """
    model_name = "text-embedding-3-small"
    embeddings = OpenAIEmbeddings(
        model=model_name,
        dimensions=dimensions
    )
    content = [doc.page_content for doc in documents]
    return embeddings.embed_documents(content)


def upload_file_to_s3(file_name, bucket_name, object_name=None):
    """
    Upload a file to an S3 bucket

    Args:
        file_name (str): File to upload
        bucket_name (str): Bucket to upload to
        object_name (str): S3 object name. If not specified, file_name is used
    Returns: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket_name, object_name)
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def upload_fileobj_to_s3(file_obj, bucket_name, object_name=None):
    """
    Upload a file-like object to an S3 bucket

    Args:
        file_obj (file-like object): File-like object to upload
        bucket_name (str): Bucket to upload file to
        object_name (str): S3 object name. If not specified, a name must be provided
    Returns: True if file was uploaded, else False
    """
    # Ensure object_name is provided since file_obj doesn't have a 'name' attribute
    if object_name is None:
        raise ValueError(
            "object_name must be provided when uploading a file-like object")

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_fileobj(file_obj, bucket_name, object_name)
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    return True


def upload_file_from_url(url, bucket_name, object_name=None):
    """
    Upload a file from a URL to an S3 bucket

    Args:
        url (str): URL of the file to download
        bucket_name (str): Bucket to upload to
        object_name (str): S3 object name. If not specified, file_name is used
    Returns: True if file was uploaded, else False
    """
    s3_client = boto3.client('s3')

    try:
        # Retrieve file from URL
        response = requests.get(url)
        response.raise_for_status()  # raises exception when not a 2xx response
        if response.status_code == 200:
            # Upload the file
            s3_client.upload_fileobj(response.raw, bucket_name, object_name)
            return True
    except requests.exceptions.RequestException as e:
        print(f'Request failed: {e}')
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False


def upsert_files_pinecone(index_name, namespace, pdf, metadata, dimensions):
    """
    Process, extract text, generate embeddings, and upsert documents into a Pinecone index.

    This function automates the workflow of processing PDF files, extracting text from them,
    generating embeddings for the extracted text, and finally upserting the data into a specified
    Pinecone vector database. It utilizes Amazon Textract for text extraction and expects the use
    of an embedding model through the `openai_embed_document` function.

    Args:
        index_name (str): The name of the Pinecone index where the documents are to be upserted.
                          This index should already be created and configured in Pinecone.
        namespace (str): A specific namespace within the Pinecone index to organize the data.
                         This allows for segmenting data within the same index, useful for multi-tenant
                         applications or differentiating datasets.
        pdf (str): The file path to the PDF document that needs to be processed and indexed.
                   The PDF is processed by Amazon Textract to extract text.
        metadata (dict): A dictionary containing metadata related to the PDF document. This metadata
                         is associated with the document's vector in Pinecone and can include information
                         such as the document's title, author, publication date, etc.
        dimensions (int): The dimensionality of the vectors generated by the embedding model. This must
                          match the dimensionality configured for the Pinecone index. It's essential for
                          the vector space model's performance and accuracy.

    Process:
        1. Initialize the Amazon Textract client and process the PDF to extract text.
        2. Split the extracted text into smaller chunks to prepare for embedding. This involves
           segmenting the text while allowing for overlap between chunks to maintain context.
        3. Generate embeddings for each text chunk using a specified embedding model.
           This step transforms the textual data into vector space.
        4. Create vectors for upserting into Pinecone by combining the embeddings with their
           corresponding metadata.
        5. Upsert the generated vectors into the specified Pinecone index and namespace.

    Returns:
        None: This function does not return a value. It performs the upsert operation directly
              on the Pinecone index.
    """
    textract_client = boto3.client("textract", region_name="us-east-2")
    loader = AmazonTextractPDFLoader(file_path=pdf, client=textract_client)
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents=documents)

    embeddings = openai_embed_document(documents=docs, dimensions=dimensions)
    vector = create_vector_from_documents_to_upsert(
        documents=docs, embeddings=embeddings, metadata=metadata)
    pinecone_store_data(vectors=vector, index_name=index_name,
                        namespace=namespace, dimensions=dimensions)


def create_vector_for_pinecone(pdf_file, metadata):
    """
    Prepare data for Pinecone index.
    """
    # get text from PDF
    docs = get_text_from_pdf(pdf_file)
    print("Total length of document: ", len(docs))
    # split text into chunks
    lst_of_chunks = split_text_into_chunks(docs)
    print("Total of chunks: ", len(lst_of_chunks),
          "| Type: ", type(lst_of_chunks))
    # embed chunks of text
    embeddings = openai_embed_data(lst_of_chunks)
    print("Total embeddings: ", len(embeddings), " | Type: ", type(embeddings))
    # create records
    vector = create_records_to_upsert(lst_of_chunks, embeddings, metadata)
    return vector

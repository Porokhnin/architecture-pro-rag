from flask import Flask
import os, logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

KNOWLEDGE_BASE_DIR = 'knowledge_base'
EMBEDDING_MODEL = 'Qwen/Qwen3-Embedding-0.6B'
NORMALIZE = False;
CHUNK_SIZE = 400;
CHUNK_OVERLAP = 50;
BASE_URL = 'https://lotr.fandom.com/wiki'
LOG_FILE = 'vector_index.log'
INDEX_DIR = 'vector_index'


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, filename=LOG_FILE, filemode='w', format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__)

# Initialize the text splitter with specific parameters.
text_splitter = RecursiveCharacterTextSplitter(
    # Set the chunk size for splitting text.
    chunk_size=CHUNK_SIZE,
    # Sets the number of overlapping characters between chunks.
    chunk_overlap=CHUNK_OVERLAP,
    # Specifies a function to calculate the length of the string.
    length_function=len,
    # track index in original document
    add_start_index=True,  
    # Sets whether to use regular expressions as delimiters.
    is_separator_regex=False,
)


def generate_index(documents: list[Document]):

    chunks = text_splitter.split_documents(documents)
    logger.info(f"LENGTH OF CHUNKS: {len(chunks)}")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL, encode_kwargs = {"normalize_embeddings": NORMALIZE})
    
    logger.info(f"Start generating index")
    vector_store = FAISS.from_documents(chunks, embeddings)
    logger.info(f"Generating index is succsses")

    logger.info(f"Start save index")
    vector_store.save_local(f'{INDEX_DIR}')
    logger.info(f"Saving index is succsses")

    return


def load_documents(knowledge_base_dir: str) -> list[Document]:
    documents = []

    for file in os.listdir(knowledge_base_dir):
        with open(f'{knowledge_base_dir}/{file}', 'r', encoding='utf-8') as input_file:
            file_text = input_file.read()          
            documents.append(
                Document(
                    page_content=file_text, 
                    metadata=
                    {
                        "source": file, 
                        "path": f'{knowledge_base_dir}/{file}',
                        "url": f'{BASE_URL}/{os.path.splitext(file)[0]}',                         
                        "updated": os.path.getatime(f'{knowledge_base_dir}/{file}'),
                        "length": len(file_text)
                    },))
            
    return documents
    
        
def generate_vector_index():
    logger.info(f"Start generating vector index")

    try:
        documents = load_documents(KNOWLEDGE_BASE_DIR)
        generate_index(documents)

        logger.info(f"Generating vector index is succsses")
    except Exception as e:
        logger.error(e)  

    return


def main():
    logger.debug(f"KNOWLEDGE_BASE_DIR: {KNOWLEDGE_BASE_DIR}")
    logger.debug(f"EMBEDDING_MODEL: {EMBEDDING_MODEL}")

    if os.path.exists(KNOWLEDGE_BASE_DIR):
        generate_vector_index()
    else:
        logger.error(f"Knowledge base directory '{KNOWLEDGE_BASE_DIR}' does not exist.")


def load_vector_store() -> FAISS:
    # Load the vector store from the local index directory
    vector_store = FAISS.load_local(INDEX_DIR, 
                    HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL, encode_kwargs = {"normalize_embeddings": NORMALIZE}, ), 
                    allow_dangerous_deserialization =True)
    
    return vector_store


def some_test():
    questions = ["Who is Pendalf?", "What is the Moya Prelest?", "Who are the members of the OPG?" ]

    vector_store = load_vector_store()
    for question in questions:
        print(f"Question: {question}")
        logger.info(f"Question: {question}")
        
        documents = vector_store.similarity_search(question, k=4)
        for document in documents:
            print(f"Answer: {document.page_content, document.metadata}")
            logger.info(f"Answer: {document.page_content, document.metadata}")


if __name__ == '__main__':
    main()
    some_test()
    #app.run(host="0.0.0.0", port=5000, debug=True)
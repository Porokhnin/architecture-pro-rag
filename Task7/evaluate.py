from flask import Flask
import json, os, logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFacePipeline
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import RetrievalQA


#https://habr.com/ru/companies/raft/articles/875758/
#https://docs.langchain.com/oss/python/integrations/providers/huggingface
#https://docs.langchain.com/oss/python/langchain/rag
#https://docs.langchain.com/oss/python/integrations/vectorstores/faiss

KNOWLEDGE_BASE_DIR = 'knowledge_base'

NORMALIZE = False;
CHUNK_SIZE = 400;
CHUNK_OVERLAP = 50;

EMBEDDING_MODEL = 'Qwen/Qwen3-Embedding-0.6B'
MODEL = 'Qwen/Qwen3-1.7B'
TRUST_REMOTE_CODE = True;
INDEX_DIR = 'vector_index'
BASE_URL = 'https://lotr.fandom.com/wiki'

LOG_FILE = 'logs.log'



# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, 
    filename=LOG_FILE, filemode='w', 
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)

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

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL, 
                                       encode_kwargs = {"normalize_embeddings": NORMALIZE}, 
                                       model_kwargs={"trust_remote_code":TRUST_REMOTE_CODE})
    
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

    logger.debug(f"KNOWLEDGE_BASE_DIR: {KNOWLEDGE_BASE_DIR}")
    logger.debug(f"EMBEDDING_MODEL: {EMBEDDING_MODEL}")

    try:

        if os.path.exists(KNOWLEDGE_BASE_DIR) == True:
            documents = load_documents(KNOWLEDGE_BASE_DIR)
            generate_index(documents)
            logger.info(f"Generating vector index is succsses")
        else:
            logger.error(f"Knowledge base directory '{KNOWLEDGE_BASE_DIR}' does not exist.")

    except Exception as e:
        logger.error(e)  

    return


def load_vector_store() -> FAISS:
    # Load the vector store from the local index directory
    vector_store = FAISS.load_local(INDEX_DIR, 
                    HuggingFaceEmbeddings(
                        model_name=EMBEDDING_MODEL, 
                        encode_kwargs = {"normalize_embeddings": NORMALIZE},
                        model_kwargs={"trust_remote_code":TRUST_REMOTE_CODE} 
                    ), 
                    allow_dangerous_deserialization =True)
    
    return vector_store


def get_prompt_template() -> PromptTemplate:

    template = """
System
You are a bot assistant who thinks first and then give Answer based only information from Context. 
If the information is not available in the Context, respond with “I'm sorry, I don't have any information on that.”

Context
<<<
{context}
>>>

Question
{question}

Answer:
"""

    prompt_template = PromptTemplate(
        input_variables=["context", "question"], 
        template=template, 
        validate_template=True)    
    
    return prompt_template


def loadJsonFile(file_path):
    with open(file_path, mode='r', encoding='utf-8') as input_file:
        return json.load(input_file)

def test_agent():

    golden_questions = loadJsonFile("golden_questions.json")

    llm = HuggingFacePipeline.from_model_id(model_id=MODEL, 
                                            task="text-generation", 
                                            model_kwargs={"trust_remote_code":TRUST_REMOTE_CODE},
                                            pipeline_kwargs={"return_full_text":False} )

    retriever = load_vector_store().as_retriever()
    prompt = get_prompt_template()    
    
    qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )


    for question, answer in golden_questions.items():
        print(f"Question: {question}")

        response = qa_chain.invoke({"query":question})

        print(f"Answer:{response['result']}")

        logger.info(f"Question: {response['query']} \n Answer: {response['result']} \n Success: { response['result'].find(answer) > 0 } \n Source: {response['source_documents']}")


if __name__ == '__main__':
    #generate_vector_index()

    test_agent()

from flask import Flask
import json, os, logging

KNOWLEDGE_BASE_ORIGINAL_DIR = 'knowledge_base_original'
KNOWLEDGE_BASE_DIR = 'knowledge_base'
TERMS_MAP_FILE_PATH = 'terms_map.json'
LOG_FILE = 'knowledge_base.log'

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, filename=LOG_FILE, filemode='w', format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__)


def rename_terms_in_the_file_text(file_text, rename_rules):
    logger.info(f"Start rename terms in the file text")

    for origin, renaming in rename_rules.items():
        file_text = file_text.replace(origin,renaming)

        origin_lowercase = origin.lower()
        renaming_lowercase = renaming.lower()

        file_text = file_text.replace(origin_lowercase, renaming_lowercase)
        
    logger.info(f"Renaming terms in the file text is succsses")

    return file_text 


def rename_terms_in_the_file(file, rename_rules) -> str:
    logger.info(f"Start renaming terms in the file {file}")

    with open(file, 'r', encoding='utf-8') as input_file:
        file_text = input_file.read()
        renamed_text = rename_terms_in_the_file_text(file_text, rename_rules)

    logger.info(f"Renaming terms in the file {file} is succsses")

    return renamed_text 


def save_file_in_knowledge_base(file_path, renamed_text):
    logger.info(f"Start saving file in knowledge base: {file_path}")

    with open(file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(renamed_text)

    logger.info(f"File saved in knowledge base: {file_path}")

    return file_path


def openJsonFile(file_path):
    with open(file_path, mode='r', encoding='utf-8') as input_file:
        return json.load(input_file)


def generate_knowledge_base():
    logger.info(f"Start generating knowledge base")

    rename_rules = openJsonFile(TERMS_MAP_FILE_PATH)
    logger.debug(f"rename_rules: {rename_rules}")

    try:
        for file in os.listdir(KNOWLEDGE_BASE_ORIGINAL_DIR):
            logger.info(f"Start rocessing file: {file}")

            renamed_text = rename_terms_in_the_file(f'{KNOWLEDGE_BASE_ORIGINAL_DIR}/{file}', rename_rules)
            save_file_in_knowledge_base(f'{KNOWLEDGE_BASE_DIR}/{file}', renamed_text)

            logger.info(f"Processed file saved: {file}")

    except Exception as e:
        logger.error(e)  

    logger.info(f"Generating knowledge base is succsses")

    return


def main():
    logger.debug(f"KNOWLEDGE_BASE_ORIGINAL_DIR: {KNOWLEDGE_BASE_ORIGINAL_DIR}")
    logger.debug(f"KNOWLEDGE_BASE_DIR: {KNOWLEDGE_BASE_DIR}")
    logger.debug(f"TERMS_MAP_FILE_PATH: {TERMS_MAP_FILE_PATH}")

    generate_knowledge_base()


if __name__ == '__main__':
    main()
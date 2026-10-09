import os
from dotenv import load_dotenv
load_dotenv('.env')
from langchain_community.utilities import SQLDatabase
db = SQLDatabase.from_uri(os.environ['POSTGRES_URI'], schema='silver')
with open('schema.txt', 'w', encoding='utf-8') as f:
    f.write(db.get_table_info())

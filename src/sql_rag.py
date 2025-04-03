# import os
# from langchain_community.utilities.sql_database import SQLDatabase
# # from urllib.parse import quote_plus
# from langchain.chains import create_sql_query_chain
# # from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_groq import ChatGroq
#
# db_user = "root"
# db_password = "12345678"
# db_host = "localhost"
# db_name = "dataset_4980"
#
# db = SQLDatabase.from_uri(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")
# # print(db.dialect)
# # print(db.get_usable_table_names())
# # print(db.table_info)
#
# # llm = ChatOpenAI(model="gpt-3.5-turbo",
# #                   temperature=0)
# # generate_query = create_sql_query_chain(llm, db)
# # query = generate_query.invoke({"question": "List All Atributes of Abrasive Disc"})
# # print(query)
#
#
# llm = ChatGroq(temperature=0, groq_api_key="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",
#                model_name="llama3-70b-8192")
# # system = "You are a helpful assistant."
# # human = "{text}"
# # prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
#
# # chain = prompt | llm
# # response=chain.invoke({"text": "Explain the importance of low latency LLMs."})
#
# user_prompt = "LIST ALL THE ATTRIBUTES AND VALUES FOR ITEMCODE:QCM100004093"
# generate_query = create_sql_query_chain(llm, db)
# query = generate_query.invoke({"question": user_prompt})
#
#
# int_index = query.index("SQLQuery") + len("SQLQuery")-1
# sql_query = query[int_index:]
# sql_query = sql_query.replace("y:", "")
# if "LIMIT" in sql_query:
#     limit_index = sql_query.index("LIMIT")
#     sql_query = sql_query[:limit_index]
# print(sql_query)
#
# from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
#
# execute_query = QuerySQLDataBaseTool(db=db)
# output = execute_query.invoke(sql_query)
# print(output)
#
# system = "You are a helpful assistant."
# human = "{text}"
# prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
#
# chain = prompt | llm
# response = chain.invoke({f"text": f"user prompt is {user_prompt} is and generated SQl resut is {output}, show the result in interactive human readable way"})
#
# print(response.content)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_groq import ChatGroq
from langchain_community.tools import QuerySQLDatabaseTool
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os

# Load environment variables
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can restrict this if needed)
    allow_credentials=True,
    allow_methods=["*"],   # Allow all HTTP methods
    allow_headers=["*"],   # Allow all headers
)

# Database connection details
db_user = "root"
db_password = "12345678"
db_host = "localhost"
db_name = "data_s"

db = SQLDatabase.from_uri(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")

# Load LLM model
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not set in the environment variables")

llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name="llama3-70b-8192")

class QueryRequest(BaseModel):
    message: str

@app.post("/chat")
def query_database(request: QueryRequest):
    if not request:
        return {"errorLog": "please provide valid prompt"}
    try:
        user_prompt = request.message
        generate_query = create_sql_query_chain(llm, db)
        query = generate_query.invoke({"question": user_prompt})

        # Extract SQL query
        def reformat_sql_query(input_query):
            int_index = input_query.index("SQLQuery") + len("SQLQuery: ")
            input_query = input_query[int_index:]
            if "LIMIT" in input_query:
                limit_index = input_query.index("LIMIT")
                input_query = input_query[:limit_index]
            return input_query

        sql_query=reformat_sql_query(query)
        print(f"sql query is {sql_query}")

        # Execute the query
        execute_query = QuerySQLDatabaseTool(db=db)
        output = execute_query.invoke(sql_query)
        print(output)

        # Format response using LLM
        system = "You are a helpful assistant."
        human = "{text}"
        prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
        chain = prompt | llm
        response = chain.invoke({"text": f"User prompt: {user_prompt} , SQL result: {output}. Present in a user-friendly format and do not as sql response show as machine response type. "})
        print(response)
        return {"response": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


import uuid

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
from langchain_community.chat_message_histories import ChatMessageHistory
from pinecone import Pinecone
import os
from flask import Flask,request,jsonify
from flask_cors import CORS
import uuid

#global session
session_id = str(uuid.uuid1())

load_dotenv(dotenv_path="D:\python_project\MlToSql\.env")

app=Flask(__name__)
CORS(app,resources={r"/*":{"origins":"*"}})

pinecone = Pinecone(api_key=os.getenv("PINECONE_API_KEY"), environment="us-east-1")
index = pinecone.Index("pickleindex")

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama3-70b-8192"
)

with open(r"D:\python_project\MlToSql\tfidf_vectorizer.pkl", "rb") as f:
    vectorizer: TfidfVectorizer = pickle.load(f)

def retrieve_context(query: str, top_k=5):
    query_vec = vectorizer.transform([query])
    coo = query_vec.tocoo()
    sparse_query = {
        "indices": coo.col.tolist(),
        "values": coo.data.tolist()
    }

    response = index.query(
        vector=None,
        sparse_vector=sparse_query,
        top_k=top_k,
        include_metadata=True
    )

    context = "\n---\n".join(match["metadata"]["text"] for match in response["matches"])
    return context

chat_history_storage={}

def trim_to_last_k_messages(messages, k=10):
    return messages[-k:] if len(messages) > k else messages

def get_session_history(session_id:str)->ChatMessageHistory:
    if session_id not in chat_history_storage:
        chat_history_storage[session_id]=ChatMessageHistory()
    return chat_history_storage[session_id]

def get_trimmed_session_history(session_id)->ChatMessageHistory:
    full_history=get_session_history(session_id)
    full_history.messages=trim_to_last_k_messages(full_history.messages,10)
    return full_history

def rewrite_query_with_history(session_id: str, current_query: str) -> str:
    history = get_trimmed_session_history(session_id).messages

    # Format the history as text
    history_text = "\n".join(
        f"{msg.type.capitalize()}: {msg.content}" for msg in history
    )
    print(f"History text is {history_text}....\n")

    prompt = ChatPromptTemplate.from_template("""
    You are a helpful assistant. Based on the conversation so far and the user's latest query,
    rewrite the query to be more complete and self-contained for search retrieval.
    Use the **entire conversation history** (both human and AI) to create a **self-contained query**.
    return only rewritten query and not any extra sentences that might be un-necessary

    Conversation History:
    {history}

    Current Query:
    {query}

    Rewritten Query:
    """)

    chain = prompt | llm | StrOutputParser()
    rewritten_query = chain.invoke({"history": history_text, "query": current_query})
    return rewritten_query.strip()

prompt = ChatPromptTemplate.from_template("""
Use the following context to answer the question. 
If the answer is not in the context, then if possible extract relevant answers from web.

Context:
{context}

Question:
{question}

Answer:
""")

def rag_answer(session_id: str, question: str):
    rewritten_query = rewrite_query_with_history(session_id, question)
    print(f"rewritten query is {rewritten_query}...\n")
    context = retrieve_context(rewritten_query)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context, "question": question})

@app.route("/chat",methods=["POST"])
def chat_bot():
    request_body=request.get_json()
    if not request:
        return jsonify({"log":"Invalid prompt"}),404
    question=request_body.get("message")
    if question in ['thanks','exit','bye']:
        return jsonify({"response":"Thanks for chatting!"})
    answer=rag_answer(session_id, question)
    get_session_history(session_id).add_user_message(question)
    get_session_history(session_id).add_ai_message(answer)
    return jsonify({"response":answer})

if __name__ =="__main__":
    app.run(debug=True,host="0.0.0.0")
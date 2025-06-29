from fastapi import FastAPI
from pydantic import BaseModel
from chatbot import main as chatbot_main, settings  # Use your chatbot logic here

app = FastAPI()

class Query(BaseModel):
    query: str

@app.post("/chat")
def chat(query: Query):
    # You need to adapt this to call your RetrievalQA chain and return the answer
    # For demo, just echo:
    return {"answer": f"You asked: {query.query}"}
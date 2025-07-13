from fastapi import FastAPI
from pydantic import BaseModel
from chatbot import get_answer

app = FastAPI()

class Query(BaseModel):
    query: str

@app.post("/chat")
def chat(query: Query):
    answer = get_answer(query.query)
    return {"answer": answer}
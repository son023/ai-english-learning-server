from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="AI English Learning Server",
    description="A basic FastAPI server for English learning",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Welcome to AI English Learning Server!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Server is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

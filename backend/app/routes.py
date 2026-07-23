from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import uuid
import json
import asyncio
from app.rag_engine import RAGEngine
from app.document_processor import DocumentProcessor
from app.db import save_chat, get_chat, get_all_chats, delete_chat
from app.models import ChatRequest, ChatResponse

router = APIRouter()
rag_engine = RAGEngine()
doc_processor = DocumentProcessor()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed = {".pdf", ".docx", ".txt", ".md"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(400, "Only PDF, DOCX, TXT, MD supported")

    doc_id = str(uuid.uuid4())[:12]
    content = await file.read()
    filename = file.filename

    try:
        chunks = doc_processor.process(content, filename, doc_id)
        rag_engine.create_vector_store(doc_id, chunks)
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")

    chat_id = str(uuid.uuid4())[:12]
    save_chat(chat_id, doc_id, filename, [])

    return {
        "chat_id": chat_id,
        "document_id": doc_id,
        "filename": filename,
        "chunks": len(chunks)
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(400, "No messages provided")

    user_message = request.messages[-1].content
    doc_id = request.document_id
    chat_id = request.chat_id
    explanation_level = request.explanation_level.value if request.explanation_level else "detailed"

    if doc_id:
        history = [m.dict() for m in request.messages[:-1]] if len(request.messages) > 1 else []
        result = rag_engine.query(doc_id, user_message, explanation_level, history)
        response_text = result["response"]
        sources = result["sources"]
    else:
        sources = []
        response_text = "Please upload a document first so I can help you understand it."

    if chat_id:
        existing = get_chat(chat_id)
        fname = existing["filename"] if existing else ""
        all_msgs = [m.dict() for m in request.messages] + [{"role": "assistant", "content": response_text, "sources": sources}]
        save_chat(chat_id, doc_id, fname, all_msgs)

    return ChatResponse(
        response=response_text,
        sources=sources,
        chat_id=chat_id or "current"
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.messages:
        raise HTTPException(400, "No messages provided")

    doc_id = request.document_id
    chat_id = request.chat_id
    explanation_level = request.explanation_level.value if request.explanation_level else "detailed"

    def generate():
        full_response = ""
        sources = []
        for event in rag_engine.query_stream(doc_id, request.messages[-1].content, explanation_level,
                                             [m.dict() for m in request.messages[:-1]] if len(request.messages) > 1 else None):
            if event["type"] == "token":
                full_response += event["content"]
                yield f"data: {json.dumps({'type': 'token', 'content': event['content']})}\n\n"
            elif event["type"] == "done":
                sources = event.get("sources", [])
                yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"

        if chat_id:
            existing = get_chat(chat_id)
            fname = existing["filename"] if existing else ""
            all_msgs = [m.dict() for m in request.messages] + [{"role": "assistant", "content": full_response, "sources": sources}]
            save_chat(chat_id, doc_id, fname, all_msgs)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/chats")
async def list_chats():
    chats = get_all_chats()
    return {"chats": chats}


@router.get("/chat/{chat_id}")
async def get_chat_history(chat_id: str):
    chat = get_chat(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")
    return chat


@router.delete("/chat/{chat_id}")
async def remove_chat(chat_id: str):
    delete_chat(chat_id)
    return {"status": "deleted"}

import os
import uuid
import json
import threading
import sqlite3
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# Pinecone client
from pinecone import Pinecone, ServerlessSpec

# LangChain imports
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_pinecone import PineconeVectorStore

# Document loaders
from pypdf import PdfReader
from docx import Document

# --- Pinecone init ---
pc = Pinecone(
    api_key=os.getenv("PINECONE_API_KEY")
)
INDEX_NAME = "briefing-index-2"
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

# --- Embedding + LLM clients ---
embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(model_name="gpt-4.1", temperature=0.3)

# --- DB (SQLite) helpers ---
DB_PATH = os.path.join(os.path.dirname(__file__), "reports.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    title TEXT,
    prompt TEXT,
    files TEXT,
    createdAt TEXT,
    status TEXT,
    error TEXT,
    download_path TEXT
)
"""
)
conn.commit()

def list_available_files():
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return os.listdir(UPLOAD_DIR)


def index_file(filepath: str):
    """Parse PDF/DOCX/TXT, split & index into Pinecone."""
    if filepath.lower().endswith(".pdf"):
        reader = PdfReader(filepath)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif filepath.lower().endswith(".docx"):
        doc = Document(filepath)
        text = "\n".join(p.text for p in doc.paragraphs)
    elif filepath.lower().endswith(".txt"):
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)
    metas = [{"source": os.path.basename(filepath)}] * len(chunks)

    # Use updated PineconeVectorStore
    vectorstore = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embeddings,
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
    )
    vectorstore.add_texts(texts=chunks, metadatas=metas)


def generate_briefing(report_id: str):
    cur = conn.cursor()
    cur.execute("SELECT prompt, files FROM reports WHERE id=?", (report_id,))
    row = cur.fetchone()
    if not row:
        return
    prompt, files_json = row
    files = json.loads(files_json)

    try:
        # Build retriever with metadata filter
        retriever = PineconeVectorStore(
            index_name=INDEX_NAME,
            embedding=embeddings,
            pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        ).as_retriever(search_kwargs={"k": 10, "filter": {"source": {"$in": files}}})

        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff"
        )

        meta = f"""
Generate a briefing with sections:
1) Actividades recientes
2) Problemas o bloqueos
3) Interacciones con otros equipos
4) KPIs
5) Tareas planificadas


---
If there is no information for a section, please write "No hay información disponible".
---

Prompt: {prompt}
"""
        result = chain.run(meta).strip()

        out_dir = os.path.join(os.path.dirname(__file__), "reports")
        os.makedirs(out_dir, exist_ok=True)
        outfile = os.path.join(out_dir, f"{report_id}.txt")
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(result)

        cur.execute(
            """
            UPDATE reports
            SET status='complete', download_path=?
            WHERE id=?
            """, (outfile, report_id)
        )
        conn.commit()

    except Exception as e:
        cur.execute(
            """
            UPDATE reports
            SET status='failed', error=?
            WHERE id=?
            """, (str(e), report_id)
        )
        conn.commit()
        print(f"Error generating report {report_id}: {e}")


def create_report(title: str, prompt: str, files: list[str]) -> dict:
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
    for file in files:
        filepath = os.path.join(UPLOAD_DIR, file)
        if os.path.exists(filepath):
            index_file(filepath)

    report_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reports
        (id, title, prompt, files, createdAt, status)
        VALUES (?, ?, ?, ?, ?, 'generating')
        """, (report_id, title, prompt, json.dumps(files), now)
    )
    conn.commit()

    thread = threading.Thread(target=generate_briefing, args=(report_id,))
    thread.daemon = True
    thread.start()

    return {
        "id": report_id,
        "title": title,
        "prompt": prompt,
        "files": files,
        "createdAt": now,
        "status": "generating"
    }


def list_reports() -> list[dict]:
    cur = conn.cursor()
    cur.execute("SELECT id, title, prompt, files, createdAt, status, download_path, error FROM reports")
    rows = cur.fetchall()
    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "title": r[1],
            "prompt": r[2],
            "files": json.loads(r[3]),
            "createdAt": r[4],
            "status": r[5],
            "downloadUrl": r[6] if r[6] else None,
            "error": r[7] if r[7] else None
        })
    return result


def get_report_path(report_id: str) -> str | None:
    cur = conn.cursor()
    cur.execute("SELECT download_path FROM reports WHERE id=?", (report_id,))
    row = cur.fetchone()
    return row[0] if row else None

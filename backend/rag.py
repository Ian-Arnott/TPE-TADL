import os
import uuid
import json
import threading
import sqlite3
from datetime import datetime

# Pinecone client (unchanged – comes from the pinecone-client package)
from pinecone import Pinecone, ServerlessSpec

import pandas as pd

# LangChain imports with correct namespaces
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Pinecone as LangchainPinecone

# Document loaders and parsers
from pypdf import PdfReader
from docx import Document

from dotenv import load_dotenv
load_dotenv()

# --- Pinecone init ---
pc = Pinecone(
    api_key=os.getenv("PINECONE_API_KEY")
)
INDEX_NAME = "briefing-index-2"
if INDEX_NAME not in pc.list_indexes().names():  # Fixed: Changed to .names() method
    pc.create_index(
        name=INDEX_NAME,  # Fixed: Added 'name=' parameter
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

# --- Embedding + LLM clients ---
embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.3)  # Fixed: Changed to gpt-4-turbo as gpt-4.1 doesn't exist

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
""")
conn.commit()

def list_available_files():
    """Return list of filenames in files/uploads."""
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return os.listdir(UPLOAD_DIR)

def index_file(filepath: str):
    """Parse PDF/DOCX, split & index into Pinecone."""
    # load text
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

    # split & embed
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)
    metas = [{"source": os.path.basename(filepath)}]*len(chunks)

    vectorstore = LangchainPinecone.from_existing_index(
        index_name=INDEX_NAME,
        embedding=embeddings
    )
    vectorstore.add_texts(chunks, metadatas=metas)

def generate_briefing(report_id: str):
    """Background thread to perform RAG + write out a txt file."""
    # fetch report record
    cur = conn.cursor()
    cur.execute("SELECT prompt, files FROM reports WHERE id=?", (report_id,))
    row = cur.fetchone()
    if not row:
        return
    prompt, files_json = row
    files = json.loads(files_json)

    try:
        # build retriever filtered by source metadata
        vectorstore = LangchainPinecone.from_existing_index(
            index_name=INDEX_NAME,
            embedding=embeddings
        ).as_retriever(search_kwargs={"k": 10, "filter": {"source": {"$in": files}}})  # Fixed: Added filter by source
        
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=vectorstore,
            chain_type="stuff"
        )

        # craft meta-prompt
        meta = f"""
Generate a briefing with sections:
1) Actividades recientes
2) Problemas o bloqueos
3) Interacciones con otros equipos
4) KPIs
5) Tareas planificadas

Prompt: {prompt}
"""  # Fixed: Removed the misleading "Limit retrieval to sources" since we're using filter

        result = chain.run(meta).strip()

        # save out to disk
        out_dir = os.path.join(os.path.dirname(__file__), "reports")
        os.makedirs(out_dir, exist_ok=True)
        outfile = os.path.join(out_dir, f"{report_id}.txt")
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(result)

        # update DB
        cur.execute("""
            UPDATE reports
            SET status='complete', download_path=?
            WHERE id=?
        """, (outfile, report_id))
        conn.commit()

    except Exception as e:
        cur.execute("""
            UPDATE reports
            SET status='failed', error=?
            WHERE id=?
        """, (str(e), report_id))
        conn.commit()

def create_report(title: str, prompt: str, files: list[str]) -> dict:
    """Insert new report record & launch background generation."""
    # First make sure all files are indexed
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
    for file in files:
        filepath = os.path.join(UPLOAD_DIR, file)
        if os.path.exists(filepath):
            index_file(filepath)
    
    report_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports
        (id, title, prompt, files, createdAt, status)
        VALUES (?, ?, ?, ?, ?, 'generating')
    """, (report_id, title, prompt, json.dumps(files), now))
    conn.commit()

    # start background thread
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
    """Fetch all reports from SQLite."""
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
    """Return the file path for download, or None."""
    cur = conn.cursor()
    cur.execute("SELECT download_path FROM reports WHERE id=?", (report_id,))
    row = cur.fetchone()
    return row[0] if row else None
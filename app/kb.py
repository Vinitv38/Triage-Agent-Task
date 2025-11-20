import json
from pathlib import Path
from typing import List, Optional
import chromadb
from chromadb.config import Settings
from .models import KBEntry
import os

KB_PATH = "data/knowledge_base.json"

class KnowledgeBase:
    def __init__(self, path: Path = KB_PATH):
        self.client = chromadb.PersistentClient(path="data/chroma")
        self.collection = self.client.get_or_create_collection("support_kb")
        
        # Load and index the knowledge base if the collection is empty
        if not self.collection.count():
            self._index_knowledge_base(path)
    
    def _index_knowledge_base(self, path: Path):
        """Load and index the knowledge base into ChromaDB"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Prepare data for insertion
        ids = []
        documents = []
        metadatas = []
        
        for item in data:
            ids.append(str(item["id"]))
            documents.append(f"{item['title']} {item['content']}")  # Combine title and content for better search
            metadatas.append({
                "category": item["category"],
                "title": item["title"]
            })
        
        # Insert into ChromaDB
        if ids:  # Only insert if we have data
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            self.client.persist()
    
    def search(self, query: str, top_k: int = 3) -> List[KBEntry]:
        """
        Search the knowledge base using ChromaDB's semantic search.
        Returns top_k most relevant KB entries.
        """
        # Perform the search
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        # Convert results to KBEntry objects
        entries = []
        for i in range(len(results['ids'][0])):
            entry_data = {
                'id': results['ids'][0][i],
                'title': results['metadatas'][0][i]['title'],
                'content': results['documents'][0][i],
                'category': results['metadatas'][0][i]['category']
            }
            entries.append(KBEntry(**entry_data))
        
        return entries
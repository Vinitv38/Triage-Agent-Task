import json
from pathlib import Path
from typing import List
import chromadb
from .models import KBEntry
from .utils import logger

KB_PATH = "data/knowledge_base.json"

class KnowledgeBase:
    def __init__(self, path: Path = KB_PATH):
        logger.info("Initializing KnowledgeBase path=%s", path)
        
        self.client = chromadb.PersistentClient(path="data/chroma")
        self.collection = self.client.get_or_create_collection("support_kb")
        
        # Load and index the knowledge base if the collection is empty
        count = self.collection.count()
        logger.debug("Chroma collection count=%d", count)
        if not count:
            logger.info("Collection empty, indexing KB from %s", path)
            self._index_knowledge_base(path)
        else:
            logger.info("KB collection already populated, count=%d", count)
    
    def _index_knowledge_base(self, path: Path):
        """Load and index the knowledge base into ChromaDB"""
        logger.info("Indexing knowledge base from %s", path)
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Prepare data for insertion
        ids = []
        documents = []
        metadatas = []
        
        logger.debug("Preparing %d KB entries for upsert", len(data))
        for item in data:
            ids.append(str(item["id"]))
            # Combine title, symptoms, and recommended_action for better semantic search
            symptoms_text = " ".join(item.get("symptoms", []))
            combined_text = f"{item['title']} {symptoms_text} {item.get('recommended_action', '')}"
            documents.append(combined_text)
            metadatas.append({
                "category": item["category"],
                "title": item["title"],
                "recommended_action": item.get("recommended_action", "")
            })
        
        # Insert into ChromaDB
        if ids:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info("Upserted %d KB entries into ChromaDB", len(ids))

    def search(self, query: str, top_k: int = 3) -> List[KBEntry]:
        """
        Search the knowledge base using ChromaDB's semantic search.
        Returns top_k most relevant KB entries.
        """
        logger.debug("Searching KB with query=%s top_k=%d", query, top_k)
        
        # Perform the search
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        logger.debug("KB search results: %d entries returned", len(results['ids'][0]) if results['ids'] else 0)
        
        # Convert results to KBEntry objects
        entries = []
        for i in range(len(results['ids'][0])):
            # Filter by distance threshold (ChromaDB uses cosine distance)
            if results['distances'][0][i] > 1.3:
                logger.debug("Skipping entry (distance too high): %s", results['ids'][0][i])
                break
            
            entry_data = {
                'id': results['ids'][0][i],
                'title': results['metadatas'][0][i]['title'],
                'content': results['documents'][0][i],
                'category': results['metadatas'][0][i]['category'],
            }
            entries.append(KBEntry(**entry_data))
            logger.debug("Added KB entry: %s (category=%s)", entry_data['id'], entry_data['category'])
        
        logger.info("KB search completed: %d relevant entries found", len(entries))
        return entries
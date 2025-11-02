import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os
import numpy as np


def chunk_text(text, max_chars=24000):
    """
    Divide texto en chunks cuando excede el límite.
    Aproximación conservadora: ~3 caracteres por token
    max_chars=24000 ≈ 8000 tokens
    """
    if len(text) <= max_chars:
        return [text]
    
    # Dividir el texto en chunks de max_chars caracteres
    chunks = []
    for i in range(0, len(text), max_chars):
        chunk = text[i:i + max_chars]
        chunks.append(chunk)
    
    return chunks


class TennisSituationMemory:
    def __init__(self, name, config):

        self.embedding = "text-embedding-3-small"
        self.client = OpenAI(base_url=config["backend_url"])
        self.use_openai = True
    
        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        self.match_collection = self.chroma_client.create_collection(name=name)

    def get_embedding(self, text):
        """Get OpenAI embedding for a text, handling long texts by splitting and averaging embeddings"""
        # text-embedding-3-small has a max context length of 8192 tokens
        # Conservative estimate: ~3 characters per token for safety margin
        max_chars = 24000  # ~8000 tokens * 3 chars/token
        
        if len(text) <= max_chars:
            # Text is short enough, get embedding directly
            response = self.client.embeddings.create(
                model=self.embedding, input=text
            )
            return response.data[0].embedding
        
        # Text is too long, split into chunks and average embeddings
        chunks = chunk_text(text, max_chars=max_chars)
        
        chunk_embeddings = []
        for i, chunk in enumerate(chunks):
            try:
                response = self.client.embeddings.create(
                    model=self.embedding, input=chunk
                )
                chunk_embeddings.append(response.data[0].embedding)
            except Exception as e:
                print(f"Failed to get embedding for chunk {i}: {e}")
                continue
        
        if not chunk_embeddings:
            raise ValueError("Failed to get embeddings for any chunks")
        
        # Average the embeddings (simple approach)
        averaged_embedding = np.mean(chunk_embeddings, axis=0).tolist()
        
        return averaged_embedding

    def add_situations(self, situations_and_advice):
        """
        Añade situaciones de partidos pasados junto con las predicciones o recomendaciones realizadas.
        El parámetro es una lista de tuplas: (situación_textual, recomendación_textual)
        """

        situaciones = []
        consejos = []
        ids = []
        embeddings = []

        offset = self.match_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situaciones.append(situation)
            consejos.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.match_collection.add(
            documents=situaciones,
            metadatas=[{"recommendation": rec} for rec in consejos],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        """
        Recupera recomendaciones similares a partir de una situación de partido actual
        usando embeddings de similitud semántica.
        """
        query_embedding = self.get_embedding(current_situation)

        results = self.match_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matched_results = []
        for i in range(len(results["documents"][0])):
            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": results["metadatas"][0][i]["recommendation"],
                    "similarity_score": 1 - results["distances"][0][i],
                }
            )

        return matched_results

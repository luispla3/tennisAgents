import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os


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
        """Obtener el embedding de una descripción de partido/contexto de apuestas"""
        if self.use_openai:
            response = self.client.embeddings.create(
                model=self.embedding, input=text
            )
            return response.data[0].embedding
        else:
            # Use Google's embedding model
            return self.embedding_model.embed_query(text)

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
        Chunkea automáticamente las recomendaciones largas para evitar exceder límites de tokens.
        """
        query_embedding = self.get_embedding(current_situation)

        results = self.match_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        # Para prompts con límite de 8192 tokens, usar chunk más pequeño
        # Conservador: ~3 chars por token, para 3000 tokens ≈ 9000 chars por recomendación
        max_chars_per_recommendation = 9000

        matched_results = []
        for i in range(len(results["documents"][0])):
            recommendation = results["metadatas"][0][i]["recommendation"]
            
            # Chunkea la recomendación si es muy larga
            # Toma solo el primer chunk (más relevante) para mantener el prompt manejable
            chunks = chunk_text(recommendation, max_chars=max_chars_per_recommendation)
            if len(chunks) > 1:
                # Si hay múltiples chunks, toma el primero y añade indicador
                chunked_recommendation = chunks[0] + "\n\n[...texto truncado para evitar exceder el límite de tokens...]"
            else:
                chunked_recommendation = chunks[0]
            
            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": chunked_recommendation,
                    "similarity_score": 1 - results["distances"][0][i],
                }
            )

        return matched_results

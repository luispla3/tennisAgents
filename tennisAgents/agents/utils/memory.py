import chromadb
from chromadb.config import Settings
from openai import OpenAI
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os


class TennisSituationMemory:
    def __init__(self, name, config):
        if config["backend_url"] == "http://localhost:11434/v1":
            self.embedding = "nomic-embed-text"
            self.client = OpenAI(base_url=config["backend_url"])
            self.use_openai = True
        else:
            # For Google's embedding models, we need to use a different approach
            if config["llm_provider"].lower() == "google":
                # Configure Google API
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                # Use Google's embedding model
                self.embedding_model = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=os.getenv("GOOGLE_API_KEY")
                )
                self.use_openai = False
            else:
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

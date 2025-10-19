"""
RAG Manager for Tennis Agents
Manages document processing and querying using RAGAnything for CSV and tabular data.
"""
import asyncio
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from raganything import RAGAnything, RAGAnythingConfig
    from lightrag.llm.openai import openai_complete_if_cache, openai_embed
    from lightrag.utils import EmbeddingFunc
    RAGANYTHING_AVAILABLE = True
except ImportError:
    RAGANYTHING_AVAILABLE = False
    print("Warning: raganything not installed. Install with: pip install raganything")


class RAGManager:
    """
    Simplified RAG Manager for processing CSV and tabular data files.
    """
    
    def __init__(
        self,
        working_dir: str = "./rag_storage",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        llm_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-large",
        embedding_dim: int = 3072,
    ):
        """
        Initialize RAG Manager.
        
        Args:
            working_dir: Directory to store RAG data
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Optional custom API base URL
            llm_model: LLM model to use for queries
            embedding_model: Embedding model to use
            embedding_dim: Embedding dimension
        """
        if not RAGANYTHING_AVAILABLE:
            raise ImportError(
                "raganything library is not installed. "
                "Install it with: pip install raganything"
            )
        
        self.working_dir = working_dir
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Create configuration for CSV/tabular data processing
        # No need for image, equation, or complex table processing
        self.config = RAGAnythingConfig(
            working_dir=self.working_dir,
            parser="mineru",  # Docling can handle CSV and tabular data well
            parse_method="auto",  # Use text parsing for CSV
            enable_image_processing=False,  # Not needed for CSV
            enable_table_processing=True,  # Keep table processing for CSV structure
            enable_equation_processing=False,  # Not needed for CSV
        )
        
        # Initialize RAG instance
        self.rag = RAGAnything(
            config=self.config,
            llm_model_func=self._llm_model_func,
            embedding_func=self._embedding_func(),
        )
    
    def _llm_model_func(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: List[Dict] = None,
        **kwargs
    ) -> str:
        """LLM model function for text completion."""
        if history_messages is None:
            history_messages = []
        
        return openai_complete_if_cache(
            self.llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs,
        )
    
    def _embedding_func(self) -> EmbeddingFunc:
        """Create embedding function."""
        return EmbeddingFunc(
            embedding_dim=self.embedding_dim,
            max_token_size=8192,
            func=lambda texts: openai_embed(
                texts,
                model=self.embedding_model,
                api_key=self.api_key,
                base_url=self.base_url,
            ),
        )
    
    async def process_file(
        self,
        file_path: str,
        output_dir: str = "./output",
        parse_method: str = "txt"
    ) -> Dict[str, Any]:
        """
        Process a single file (CSV, XLSX, JSONL, etc.).
        
        Args:
            file_path: Path to the file to process
            output_dir: Directory to store processed output
            parse_method: Parse method (txt, auto, ocr)
            
        Returns:
            Dictionary with processing results
        """
        print(f"Processing file: {file_path}")
        
        result = await self.rag.process_document_complete(
            file_path=file_path,
            output_dir=output_dir,
            parse_method=parse_method
        )
        
        print(f"✓ Completed processing: {file_path}")
        return result
    
    async def process_dataset_folder(
        self,
        dataset_path: str = "./dataset/dataset",
        output_dir: str = "./output",
        file_extensions: List[str] = None,
        recursive: bool = True,
        max_workers: int = 2
    ) -> Dict[str, Any]:
        """
        Process all data files in the dataset folder.
        
        Args:
            dataset_path: Path to dataset folder
            output_dir: Directory to store processed output
            file_extensions: List of file extensions to process (default: CSV, XLSX, JSONL)
            recursive: Whether to search subdirectories
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with processing results
        """
        if file_extensions is None:
            file_extensions = [".pdf", ".txt"]
        
        print(f"Starting batch processing of dataset folder: {dataset_path}")
        print(f"File extensions: {file_extensions}")
        print(f"Recursive: {recursive}")
        
        result = await self.rag.process_folder_complete(
            folder_path=dataset_path,
            output_dir=output_dir,
            file_extensions=file_extensions,
            recursive=recursive,
            max_workers=max_workers
        )
        
        print("✓ Completed batch processing")
        return result
    
    async def query(
        self,
        question: str,
        mode: str = "local",
        top_k: int = 10
    ) -> str:
        """
        Query the RAG system with a text question.
        
        Args:
            question: Question to ask
            mode: Query mode (hybrid, local, global, naive)
            top_k: Number of top results to retrieve
            
        Returns:
            Answer string
        """
        result = await self.rag.aquery(
            question,
            mode=mode,
            top_k=top_k
        )
        return result
    
    async def query_about_matches(self, question: str) -> str:
        """
        Convenience method to query about tennis matches.
        
        Args:
            question: Question about tennis matches
            
        Returns:
            Answer string
        """
        return await self.query(question, mode="local")
    
    async def query_about_odds(self, question: str) -> str:
        """
        Convenience method to query about betting odds.
        
        Args:
            question: Question about odds
            
        Returns:
            Answer string
        """
        return await self.query(question, mode="local")
    
    async def query_about_weather(self, question: str) -> str:
        """
        Convenience method to query about weather data.
        
        Args:
            question: Question about weather
            
        Returns:
            Answer string
        """
        return await self.query(question, mode="local")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the RAG storage.
        
        Returns:
            Dictionary with storage statistics
        """
        storage_path = Path(self.working_dir)
        if not storage_path.exists():
            return {"status": "empty", "files": 0}
        
        files = list(storage_path.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        
        return {
            "status": "initialized",
            "working_dir": self.working_dir,
            "file_count": file_count,
        }
    
    def is_initialized(self) -> bool:
        """
        Check if RAG manager is properly initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return hasattr(self, 'rag') and self.rag is not None


async def initialize_rag(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    working_dir: str = "./rag_storage",
    process_datasets: bool = False,
    dataset_path: str = "./dataset/dataset",
    llm_model: str = "gpt-4o-mini",
    embedding_model: str = "text-embedding-3-large",
) -> Optional[RAGManager]:
    """
    Initialize RAG system and optionally process datasets.
    
    Args:
        api_key: OpenAI API key
        base_url: Optional custom API base URL
        working_dir: Directory to store RAG data
        process_datasets: Whether to process dataset files on initialization
        dataset_path: Path to dataset folder
        llm_model: LLM model to use
        embedding_model: Embedding model to use
        
    Returns:
        Initialized RAGManager instance or None if initialization fails
    """
    try:
        # Create RAG Manager
        rag_manager = RAGManager(
            working_dir=working_dir,
            api_key=api_key,
            base_url=base_url,
            llm_model=llm_model,
            embedding_model=embedding_model,
        )
        
        # Process datasets if requested
        if process_datasets:
            dataset_full_path = Path(dataset_path)
            if dataset_full_path.exists():
                print(f"Processing datasets from: {dataset_full_path}")
                await rag_manager.process_dataset_folder(
                    dataset_path=str(dataset_full_path),
                    output_dir="./output",
                    file_extensions=[".pdf", ".txt"],
                    recursive=True,
                    max_workers=1
                )
            else:
                print(f"Warning: Dataset path not found: {dataset_full_path}")
        
        return rag_manager
        
    except Exception as e:
        print(f"Error initializing RAG: {e}")
        return None


def is_initialized(rag_manager: Optional[RAGManager]) -> bool:
    """
    Check if RAG manager is properly initialized.
    
    Args:
        rag_manager: RAGManager instance to check
        
    Returns:
        True if initialized, False otherwise
    """
    return rag_manager is not None and hasattr(rag_manager, 'rag')


if __name__ == "__main__":
    # Example usage
    async def example_usage():
        # Initialize RAG with dataset processing
        rag = await initialize_rag(
            process_datasets=True,
            dataset_path="./dataset/dataset"
        )
        
        if rag:
            # Query the RAG
            result = await rag.query("What is the latest tennis match data?")
            print(result)
    
    asyncio.run(example_usage())


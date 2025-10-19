"""
Example script demonstrating how to use the RAG Manager
to process and query tennis dataset files.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tennisAgents.utils.rag_manager import RAGManager


async def main():
    """Main example function."""
    
    print("=" * 80)
    print("Tennis Agents RAG Manager - Example")
    print("=" * 80)
    
    # Initialize RAG Manager
    print("\n1. Initializing RAG Manager...")
    rag_manager = RAGManager(
        working_dir="./rag_storage",
        llm_model="gpt-4o-mini",
    )
    print("✓ RAG Manager initialized")
    
    # Check current stats
    stats = rag_manager.get_stats()
    print(f"\nCurrent RAG storage stats: {stats}")
    
    # Process dataset folder
    print("\n2. Processing dataset files...")
    print("-" * 80)
    
    try:
        result = await rag_manager.process_dataset_folder(
            dataset_path="./dataset/dataset",
            output_dir="./output",
            file_extensions=[".csv", ".xlsx", ".jsonl"],
            recursive=True,
            max_workers=2
        )
        print(f"\n✓ Processing completed: {result}")
    except Exception as e:
        print(f"Error during processing: {e}")
        print("Note: Make sure the dataset folder exists and contains files")
    
    # Example queries
    print("\n3. Running example queries...")
    print("-" * 80)
    
    try:
        # Query about ATP matches
        print("\nQuery 1: ATP Matches Statistics")
        result = await rag_manager.query_about_matches(
            "What statistics are tracked in the ATP matches dataset?"
        )
        print(f"Answer: {result[:500]}..." if len(result) > 500 else f"Answer: {result}")
        
        # Query about odds
        print("\nQuery 2: Betting Odds")
        result = await rag_manager.query_about_odds(
            "What years of odds data are available?"
        )
        print(f"Answer: {result[:500]}..." if len(result) > 500 else f"Answer: {result}")
        
        # Query about weather
        print("\nQuery 3: Weather Data")
        result = await rag_manager.query_about_weather(
            "What weather information is available in the dataset?"
        )
        print(f"Answer: {result[:500]}..." if len(result) > 500 else f"Answer: {result}")
        
        # General query
        print("\nQuery 4: General Dataset Query")
        result = await rag_manager.query(
            "Give me a summary of all the tennis data available in the dataset",
            mode="hybrid"
        )
        print(f"Answer: {result[:500]}..." if len(result) > 500 else f"Answer: {result}")
        
    except Exception as e:
        print(f"Error during querying: {e}")
        print("Note: Make sure files have been processed first")
    
    # Final stats
    print("\n4. Final storage statistics")
    print("-" * 80)
    stats = rag_manager.get_stats()
    print(f"Storage stats: {stats}")
    
    print("\n" + "=" * 80)
    print("Example completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())


import json
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from tennisAgents.default_config import DEFAULT_CONFIG

class EarningsManager:
    """
    Manages the calculation and storage of betting earnings.
    Uses a direct linear approach: Web Search (via Google requests) -> LLM Verification.
    """

    def __init__(self, config=None):
        print("Initializing EarningsManager (Linear Mode)...")
        self.config = config or DEFAULT_CONFIG.copy()
        
        current_file = Path(__file__).resolve()
        self.project_root = current_file.parent.parent.parent
        print(f"Project root resolved to: {self.project_root}")
        
        self.results_dirs = [
            self.project_root / "web" / "results",
            self.project_root / "results"
        ]
        
        web_data_dir = self.project_root / "web" / "data"
        web_data_dir.mkdir(parents=True, exist_ok=True)
        self.earnings_file = web_data_dir / "earnings_history.json"
        
        self.llm = self._init_llm()

    def _init_llm(self):
        try:
            provider = self.config.get("llm_provider", "openai").lower()
            model = self.config.get("deep_think_llm", "gpt-4o")
            base_url = self.config.get("backend_url")
            
            if provider in ["openai", "ollama", "openrouter"]:
                return ChatOpenAI(model=model, base_url=base_url)
            elif provider == "anthropic":
                return ChatAnthropic(model=model, base_url=base_url)
            elif provider == "google":
                return ChatGoogleGenerativeAI(model=model)
            else:
                return ChatOpenAI(model=model)
        except Exception as e:
            print(f"Error initializing LLM: {e}")
            return None

    def _perform_web_search(self, query: str) -> str:
        """
        Robust web search using Google fallback directly.
        Returns text content of results.
        """
        import requests
        print(f"DEBUG: Searching for: {query}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

        try:
            # Google Search
            cookies = {"CONSENT": "YES+cb.20210720-07-p0.en+FX+410"}
            resp = requests.get(
                f"https://www.google.com/search?q={query}&hl=en&num=10", 
                headers=headers, 
                cookies=cookies, 
                timeout=15
            )
            
            if resp.status_code == 200:
                text = resp.text
                # Basic cleanup to reduce token usage and noise
                clean_text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
                clean_text = re.sub(r'<style.*?>.*?</style>', '', clean_text, flags=re.DOTALL)
                clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                # If too short, might be blocked or empty
                if len(clean_text) < 200:
                    return f"Search returned too little data ({len(clean_text)} chars)."
                    
                return clean_text[:12000] # Increased context for LLM
            else:
                return f"Google search failed: {resp.status_code}"
                
        except Exception as e:
            return f"Search exception: {str(e)}"

    async def calculate_earnings(self) -> Dict[str, Any]:
        earnings_data = self._load_earnings()
        processed_count = 0
        
        for results_dir in self.results_dirs:
            if not results_dir.exists(): continue

            for match_dir in results_dir.iterdir():
                if not match_dir.is_dir(): continue
                
                for date_dir in match_dir.iterdir():
                    if not date_dir.is_dir(): continue
                    
                    analysis_date = date_dir.name
                    reports_dir = date_dir / "reports"
                    if not reports_dir.exists(): continue

                    run_id = f"{match_dir.name}_{analysis_date}"
                    bet_files = list(reports_dir.glob("final_bet_decision*.md"))
                    if not bet_files: continue
                    
                    # Clean match name
                    match_name = match_dir.name.split("_")[0] if "_" in match_dir.name else match_dir.name
                    print(f"Processing: {match_name} ({analysis_date})")

                    match_bets = []
                    
                    for bet_file in bet_files:
                        try:
                            content = bet_file.read_text(encoding="utf-8")
                            filename = bet_file.name
                            
                            # Model type
                            if "aggressive" in filename.lower(): model_type = "Aggressive"
                            elif "conservative" in filename.lower() or "safe" in filename.lower(): model_type = "Safe"
                            elif "neutral" in filename.lower(): model_type = "Neutral"
                            elif "expected" in filename.lower(): model_type = "Expected"
                            else: model_type = "General"

                            # 1. Extract Bets
                            bet_list = await self._extract_bet_details(content)
                            if not bet_list: continue
                                
                            for bet_item in bet_list:
                                stake = float(bet_item.get("stake", 10.0))
                                odds = float(bet_item.get("odds", 0.0))
                                selection = bet_item.get("selection", "Unknown")
                                
                                print(f"  > Verifying: {selection} (Odds: {odds})")

                                # 2. Verify with Linear Search+LLM
                                outcome_status, reason = await self._verify_bet_linear(
                                    selection, match_name, analysis_date
                                )
                                print(f"    Result: {outcome_status} ({reason[:50]}...)")
                                
                                revenue = 0.0
                                if outcome_status == "Won":
                                    revenue = stake * odds
                                
                                match_bets.append({
                                    "model_type": model_type,
                                    "stake": stake,
                                    "odds": odds,
                                    "selection": selection,
                                    "revenue": revenue,
                                    "status": outcome_status,
                                    "filename": filename,
                                    "match_result_context": reason
                                })
                            
                        except Exception as e:
                            print(f"Error processing {bet_file}: {e}")
                            continue

                    if match_bets:
                        # Update/Add logic...
                        existing_idx = -1
                        for i, entry in enumerate(earnings_data):
                            if entry.get("run_id") == run_id:
                                existing_idx = i
                                break
                        
                        entry_data = {
                            "run_id": run_id,
                            "match_name": match_dir.name,
                            "analysis_date": analysis_date,
                            "bets": match_bets,
                            "last_updated": datetime.now().isoformat()
                        }
                        
                        if existing_idx >= 0:
                            earnings_data[existing_idx] = entry_data
                        else:
                            earnings_data.append(entry_data)
                        processed_count += 1

        self._save_earnings(earnings_data)
        return {"success": True, "processed": processed_count, "data": earnings_data}

    async def _verify_bet_linear(self, selection: str, match_name: str, date: str) -> Tuple[str, str]:
        """
        Perform search -> LLM verify directly.
        """
        # Search query optimized: Remove specific date to find the actual latest match
        query = f"latest tennis match score {match_name} result"
        search_text = self._perform_web_search(query)
        
        # If search failed completely
        if "failed" in search_text.lower() and len(search_text) < 100:
            return "Pending", "Search failed"

        prompt = f"""
        You are a sports betting verifier.
        
        Bet Details:
        - Match: {match_name}
        - Folder Date: {date} (Might be a future simulation date)
        - Selection: "{selection}"
        
        Web Search Results (Raw Text):
        {search_text}
        
        Task:
        Determine if the bet WON or LOST based on the search results for the MOST RECENT match played between these players.
        
        Rules:
        - IGNORE the Folder Date year if it is in the future (e.g. 2025). Verify against the real match found in search results (e.g. from 2024).
        - Look for "def." (defeated), scores (e.g. 6-3 6-4), or "won".
        - If the bet is for a specific Set (e.g. "Set 2"), look for the score of that set.
        
        Output ONLY a JSON object:
        {{
            "status": "Won" | "Lost" | "Unknown",
            "reason": "Short explanation with score found"
        }}
        """
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            # Clean json
            content = content.replace("```json", "").replace("```", "").strip()
            if "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
                
            data = json.loads(content)
            return data.get("status", "Unknown"), data.get("reason", "No reason provided")
            
        except Exception as e:
            return "Unknown", f"LLM Error: {str(e)}"

    async def _extract_bet_details(self, content: str) -> List[Dict[str, Any]]:
        if not self.llm: return []
        prompt = f"""
        Extract ALL distinct betting recommendations from the text.
        Text: {content[:6000]}
        
        Return JSON LIST:
        [
            {{ "selection": "string", "odds": float, "stake": float (default 10.0) }}
        ]
        """
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            text = response.content.replace("```json", "").replace("```", "").strip()
            if "[" in text:
                text = text[text.find("["):text.rfind("]")+1]
            return json.loads(text)
        except Exception:
            return []

    def _load_earnings(self) -> List[Dict[str, Any]]:
        if self.earnings_file.exists():
            try:
                with open(self.earnings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return []
        return []

    def _save_earnings(self, data: List[Dict[str, Any]]):
        try:
            with open(self.earnings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving: {e}")

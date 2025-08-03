#!/usr/bin/env python3
"""
Test script to verify get_atp_rankings is working correctly
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'tennisAgents'))

from dataflows.interface import get_atp_rankings, search_player_id

def test_get_atp_rankings():
    print("=== Testing get_atp_rankings ===")
    result = get_atp_rankings()
    print(result)
    print("\n" + "="*50 + "\n")

def test_search_player_id():
    print("=== Testing search_player_id for 'Jannik Sinner' ===")
    result = search_player_id("Jannik Sinner")
    print(result)
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    test_get_atp_rankings()
    test_search_player_id() 
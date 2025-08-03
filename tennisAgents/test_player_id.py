#!/usr/bin/env python3
"""
Script de prueba para verificar que fetch_player_id funciona correctamente.
"""

import sys
import os

# Agregar el directorio raíz al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dataflows.player_utils import fetch_player_id

def test_player_id():
    """Prueba la función fetch_player_id con diferentes jugadores."""
    
    print("=== PRUEBA DE FETCH_PLAYER_ID ===")
    
    # Lista de jugadores para probar
    test_players = [
        "Carlos Alcaraz",
        "Novak Djokovic", 
        "Jannik Sinner",
        "Daniil Medvedev"
    ]
    
    for player in test_players:
        print(f"\n--- Probando con {player} ---")
        try:
            player_id = fetch_player_id(player)
            if player_id:
                print(f"✅ ID encontrado: {player_id}")
            else:
                print(f"❌ No se pudo encontrar ID para {player}")
        except Exception as e:
            print(f"❌ Error al buscar ID para {player}: {e}")
    
    print("\n=== FIN DE PRUEBA ===")

if __name__ == "__main__":
    test_player_id() 
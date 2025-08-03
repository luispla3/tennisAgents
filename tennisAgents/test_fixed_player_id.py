#!/usr/bin/env python3
"""
Script de prueba simple para verificar que fetch_player_id funciona con la corrección.
"""

import sys
import os

# Agregar el directorio raíz al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dataflows.player_utils import fetch_player_id

def test_fixed_player_id():
    """Prueba la función fetch_player_id con la corrección."""
    
    print("=== PRUEBA DE FETCH_PLAYER_ID (CORREGIDO) ===")
    
    # Probar con un jugador específico
    test_player = "Carlos Alcaraz"
    
    print(f"\n--- Probando con {test_player} ---")
    try:
        player_id = fetch_player_id(test_player)
        if player_id:
            print(f"✅ ID encontrado: {player_id}")
            
            # Probar también get_recent_matches
            from dataflows.interface import get_recent_matches
            result = get_recent_matches(test_player, 3)
            print(f"\n--- Resultado de get_recent_matches ---")
            print(result)
        else:
            print(f"❌ No se pudo encontrar ID para {test_player}")
    except Exception as e:
        print(f"❌ Error al buscar ID para {test_player}: {e}")
    
    print("\n=== FIN DE PRUEBA ===")

if __name__ == "__main__":
    test_fixed_player_id() 
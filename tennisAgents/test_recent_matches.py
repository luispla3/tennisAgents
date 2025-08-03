#!/usr/bin/env python3
"""
Script de prueba para verificar que get_recent_matches funciona correctamente.
"""

import sys
import os

# Agregar el directorio raíz al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dataflows.interface import get_recent_matches

def test_recent_matches():
    """Prueba la función get_recent_matches con diferentes jugadores."""
    
    print("=== PRUEBA DE GET_RECENT_MATCHES ===")
    
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
            result = get_recent_matches(player, 5)
            print(result)
        except Exception as e:
            print(f"❌ Error al obtener partidos para {player}: {e}")
    
    print("\n=== FIN DE PRUEBA ===")

if __name__ == "__main__":
    test_recent_matches() 
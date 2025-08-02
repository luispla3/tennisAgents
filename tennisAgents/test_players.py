#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema de players.
Ejecuta: python test_players.py
"""

import sys
import os

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tennisAgents.dataflows.player_utils import test_player_utils

if __name__ == "__main__":
    print("🔍 Iniciando prueba del sistema de players...")
    print("=" * 50)
    
    success = test_player_utils()
    
    if success:
        print("\n✅ Todas las pruebas completadas exitosamente!")
    else:
        print("\n❌ Algunas pruebas fallaron. Revisa la configuración.")
    
    print("\n📝 Para configurar las API keys:")
    print("1. Copia env_example.txt como .env")
    print("2. Configura tus API keys en el archivo .env")
    print("3. Ejecuta este script nuevamente") 
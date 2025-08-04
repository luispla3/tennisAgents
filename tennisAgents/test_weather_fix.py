#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad meteorológica con coordenadas correctas.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tennisAgents.dataflows.interface import get_weather_forecast

def test_weather_with_correct_coordinates():
    """Prueba la funcionalidad meteorológica con coordenadas correctas de torneos."""
    print("🌤️ Probando funcionalidad meteorológica con coordenadas correctas...\n")
    
    # Coordenadas correctas de torneos importantes
    tournaments = [
        {
            "name": "Wimbledon",
            "latitude": 51.4344,
            "longitude": -0.2145,
            "location": "Londres, Reino Unido"
        },
        {
            "name": "US Open",
            "latitude": 40.7505,
            "longitude": -73.8456,
            "location": "Nueva York, Estados Unidos"
        },
        {
            "name": "Roland Garros",
            "latitude": 48.8467,
            "longitude": 2.2474,
            "location": "París, Francia"
        },
        {
            "name": "Australian Open",
            "latitude": -37.8228,
            "longitude": 144.9784,
            "location": "Melbourne, Australia"
        }
    ]
    
    for tournament in tournaments:
        print(f"📍 Probando: {tournament['name']} ({tournament['location']})")
        print(f"   Coordenadas: {tournament['latitude']}, {tournament['longitude']}")
        
        try:
            # Probar con una fecha futura
            result = get_weather_forecast(
                tournament=tournament['name'],
                fecha_hora="2025-07-15 14:00",
                latitude=tournament['latitude'],
                longitude=tournament['longitude']
            )
            
            print("✅ Datos obtenidos correctamente:")
            print(result)
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 80)
        print()

if __name__ == "__main__":
    print("=" * 80)
    print("🌤️ PRUEBA DE FUNCIONALIDAD METEOROLÓGICA")
    print("=" * 80)
    print()
    
    try:
        test_weather_with_correct_coordinates()
        print("✅ Prueba completada")
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}") 
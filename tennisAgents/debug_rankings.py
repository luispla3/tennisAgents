#!/usr/bin/env python3
"""
Script específico para diagnosticar el problema con los rankings ATP.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_rankings_detailed():
    """
    Prueba detallada del endpoint de rankings ATP.
    """
    print("=== DIAGNÓSTICO DETALLADO DE RANKINGS ATP ===\n")
    
    # Verificar API key
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("❌ RAPIDAPI_KEY no configurada")
        return False
    
    print(f"✅ API Key configurada: {api_key[:20]}...")
    
    # URL correcta según RapidAPI
    url = "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v2/atp/ranking/singles/"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "tennis-api-atp-wta-itf.p.rapidapi.com"
    }
    
    print(f"🔄 Probando endpoint: {url}")
    print(f"Headers: {headers}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Conexión exitosa!")
            
            # Obtener los datos
            data = response.json()
            
            print(f"\n📊 ESTRUCTURA DE DATOS:")
            print(f"Tipo de respuesta: {type(data)}")
            
            if isinstance(data, dict):
                print(f"Keys disponibles: {list(data.keys())}")
                
                # Mostrar el contenido completo
                print(f"\n📋 CONTENIDO COMPLETO:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Intentar extraer rankings
                rankings = []
                
                # Buscar en diferentes estructuras posibles
                possible_keys = ["rankings", "data", "players", "results", "rankings"]
                
                for key in possible_keys:
                    if key in data:
                        print(f"\n🔍 Encontrado en key '{key}': {type(data[key])}")
                        if isinstance(data[key], list):
                            print(f"  Número de elementos: {len(data[key])}")
                            if len(data[key]) > 0:
                                print(f"  Primer elemento: {data[key][0]}")
                                rankings = data[key]
                                break
                        else:
                            print(f"  No es una lista: {data[key]}")
                
                if rankings:
                    print(f"\n🎾 RANKINGS ENCONTRADOS ({len(rankings)} jugadores):")
                    for i, player in enumerate(rankings[:5]):
                        print(f"  {i+1}. {player}")
                else:
                    print(f"\n❌ No se encontraron rankings en ninguna estructura esperada")
                    
            elif isinstance(data, list):
                print(f"Respuesta es una lista con {len(data)} elementos")
                if len(data) > 0:
                    print(f"Primer elemento: {data[0]}")
                    
            else:
                print(f"Tipo de respuesta inesperado: {type(data)}")
                print(f"Contenido: {data}")
            
            return True
            
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_rankings_detailed()
    if success:
        print("\n🎉 Diagnóstico completado")
    else:
        print("\n❌ Problema detectado") 
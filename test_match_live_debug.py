"""
Script de debug para diagnosticar problemas con la búsqueda de partidos en vivo
"""

from tennisAgents.dataflows.match_live_utils import (
    list_all_live_matches,
    fetch_match_live_data
)


def main():
    print("=" * 80)
    print("DIAGNÓSTICO DE PARTIDOS EN VIVO - SPORTRADAR API")
    print("=" * 80)
    print()
    
    # Paso 1: Mostrar todos los partidos disponibles
    print("PASO 1: Listando todos los partidos en vivo disponibles...")
    print("-" * 80)
    matches_list = list_all_live_matches()
    print(matches_list)
    print()
    
    # Paso 2: Intentar buscar un partido específico (modifica estos valores)
    print("PASO 2: Buscando un partido específico...")
    print("-" * 80)
    
    # ⚠️ MODIFICA ESTOS VALORES CON LOS NOMBRES QUE ESTÁS BUSCANDO ⚠️
    player_a = "Djokovic"  # 👈 Cambia esto
    player_b = "Nadal"     # 👈 Cambia esto
    tournament = ""         # 👈 Opcional: especifica el torneo o deja vacío
    
    print(f"Buscando: {player_a} vs {player_b}")
    if tournament:
        print(f"Torneo: {tournament}")
    print()
    
    # Ejecutar búsqueda con DEBUG activado
    result = fetch_match_live_data(player_a, player_b, tournament if tournament else None, debug=True)
    
    print()
    print("=" * 80)
    print("RESULTADO DE LA BÚSQUEDA:")
    print("=" * 80)
    
    if result.get("success"):
        print("✓ ÉXITO: Partido encontrado!")
        print(f"\nJugadores: {result.get('player_a')} vs {result.get('player_b')}")
        print(f"Torneo: {result.get('tournament')}")
        print(f"\nDatos del partido:")
        print(result.get("formatted_data", "N/A")[:500])  # Primeros 500 caracteres
    else:
        print("✗ ERROR: No se encontró el partido")
        print(f"\nError: {result.get('error')}")
        if result.get('note'):
            print(f"Nota: {result.get('note')}")
        
        print("\n⚠️ SUGERENCIAS:")
        print("1. Verifica que los nombres de los jugadores sean correctos")
        print("2. Revisa la lista de partidos disponibles arriba")
        print("3. Intenta usar solo el apellido del jugador")
        print("4. Verifica que el partido esté en curso (no programado o finalizado)")


if __name__ == "__main__":
    main()


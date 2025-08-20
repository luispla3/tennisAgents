"""
Ejemplos de uso de la anatomía de prompts para analistas de tenis
Este archivo muestra cómo implementar la nueva estructura de prompts recomendada por OpenAI
"""

from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def example_player_analyst_prompt():
    """
    Ejemplo de cómo crear un prompt para analista de jugadores usando la anatomía
    """
    
    # 1. Obtener la anatomía predefinida
    anatomy = TennisAnalystAnatomies.player_analyst()
    
    # 2. Definir información de herramientas
    tools_info = """
    • get_atp_rankings() - Obtiene el ranking ATP actual con top 400 jugadores
    • get_injury_reports() - Obtiene reportes de lesiones y jugadores que regresan
    • get_recent_matches(player_name, opponent_name, num_matches) - Últimos partidos de ambos jugadores
    • get_surface_winrate(player_name, surface) - Winrate del jugador en una superficie específica
    • get_head_to_head(player_name, opponent_name) - Historial de enfrentamientos entre ambos
    """
    
    # 3. Definir contexto adicional específico
    additional_context = """
    PROCESO RECOMENDADO:
    1. Comienza obteniendo el ranking ATP para contextualizar la posición de ambos jugadores
    2. Consulta reportes de lesiones para evaluar el estado físico actual
    3. Analiza partidos recientes de ambos jugadores (últimos 20-30 partidos)
    4. Evalúa el rendimiento específico en la superficie del torneo
    5. Revisa el historial head-to-head para patrones históricos
    
    REGLAS IMPORTANTES:
    • Las herramientas usan OpenAI con búsqueda web, proporcionando información actualizada
    • No hay un orden estricto - usa las herramientas según la información que necesites
    • Para get_recent_matches, puedes especificar el número de partidos (por defecto 30)
    • Para get_surface_winrate, usa la superficie exacta del torneo (clay, hard, grass)
    • Todas las herramientas devuelven análisis detallados, no solo datos crudos
    
    ANÁLISIS REQUERIDO:
    • Ranking actual y evolución reciente de posiciones
    • Estado físico y reportes de lesiones recientes
    • Rendimiento en partidos recientes (últimos 20-30 partidos)
    • Eficiencia específica sobre la superficie del torneo
    • Comparación de winrates entre ambos jugadores en la superficie
    • Estadísticas head-to-head y su relevancia histórica
    • Factores que puedan influir en el resultado del partido
    
    IMPORTANTE: Proporciona análisis específico y cuantitativo, no generalidades. 
    Incluye estadísticas concretas, fechas relevantes y contexto específico. 
    Las herramientas te darán información detallada y actualizada.
    """
    
    # 4. Crear el prompt estructurado
    prompt = PromptBuilder.create_structured_prompt(
        anatomy=anatomy,
        tools_info=tools_info,
        additional_context=additional_context
    )
    
    return prompt

def example_news_analyst_prompt():
    """
    Ejemplo de cómo crear un prompt para analista de noticias usando la anatomía
    """
    
    # 1. Obtener la anatomía predefinida
    anatomy = TennisAnalystAnatomies.news_analyst()
    
    # 2. Definir información de herramientas
    tools_info = """
    • get_news() - Obtiene noticias recientes sobre jugadores y torneos de tenis
    """
    
    # 3. Definir contexto adicional específico
    additional_context = """
    OBJETIVO: Identificar información crítica que pueda influir en el rendimiento de los jugadores, incluyendo:
    • Lesiones recientes o problemas físicos, sobretodo en los partidos anteriores de ese torneo si los hay
    • Cambios de entrenador o equipo técnico
    • Declaraciones polémicas o presión mediática
    • Estado mental o motivacional
    • Rendimiento en torneos recientes
    • Rivalidades o historial personal
    
    INSTRUCCIONES TÉCNICAS:
    • Para búsquedas con get_news: usa ÚNICAMENTE el nombre del jugador
    • Incluye noticias generales del circuito ATP/WTA si son relevantes para el análisis del partido
    
    IMPORTANTE: Proporciona análisis granular y específico, no generalidades como 'las tendencias son mixtas'. 
    Incluye fechas, citas relevantes y contexto específico.
    """
    
    # 4. Crear el prompt estructurado
    prompt = PromptBuilder.create_structured_prompt(
        anatomy=anatomy,
        tools_info=tools_info,
        additional_context=additional_context
    )
    
    return prompt

def example_custom_anatomy():
    """
    Ejemplo de cómo crear una anatomía personalizada para un nuevo tipo de analista
    """
    
    from tennisAgents.agents.utils.prompt_anatomy import PromptAnatomy
    
    # Crear una anatomía personalizada para un analista de estadísticas
    custom_anatomy = PromptAnatomy(
        role="Analista especializado en estadísticas avanzadas de tenis y métricas de rendimiento",
        
        task="Analizar estadísticas avanzadas y métricas de rendimiento para evaluar el nivel actual de los jugadores",
        
        task_steps=[
            "Obtener estadísticas de servicio y recepción",
            "Analizar métricas de break points y conversión",
            "Evaluar estadísticas de juegos y sets",
            "Revisar tendencias de rendimiento en diferentes superficies",
            "Sintetizar análisis en métricas clave"
        ],
        
        context="Análisis de estadísticas avanzadas de tenis para evaluar el rendimiento actual y potencial de los jugadores",
        
        exclusions=[
            "Estadísticas básicas sin contexto",
            "Métricas desactualizadas o no verificadas",
            "Análisis que no considere la superficie específica"
        ],
        
        reasoning_priorities=[
            "Priorizar métricas más relevantes para el resultado",
            "Enfocarse en tendencias recientes y consistentes",
            "Considerar contexto de superficie y torneo",
            "Identificar patrones estadísticos significativos"
        ],
        
        verification_requirements=[
            "Verificar fuentes de estadísticas",
            "Confirmar fechas y períodos de análisis",
            "Validar cálculos y métricas",
            "Contrastar con datos históricos"
        ],
        
        output_format="Informe estructurado con análisis de estadísticas clave, tendencias y predicciones basadas en métricas",
        
        output_structure="1. Resumen estadístico\n2. Análisis por categoría\n3. Tendencias identificadas\n4. Predicciones basadas en datos\n5. Tabla de métricas clave",
        
        completion_criteria=[
            "Análisis completo de estadísticas relevantes",
            "Identificación de tendencias significativas",
            "Predicciones fundamentadas en métricas",
            "Informe estructurado con datos verificados"
        ]
    )
    
    return custom_anatomy

def demonstrate_prompt_structure():
    """
    Función que demuestra la estructura del prompt generado
    """
    
    # Crear un prompt de ejemplo
    prompt = example_player_analyst_prompt()
    
    # Mostrar la estructura del prompt
    print("=== ESTRUCTURA DEL PROMPT GENERADO ===")
    print("El prompt sigue la anatomía recomendada por OpenAI:")
    print("1. ROL - Define claramente el papel del agente")
    print("2. TAREA - Especifica qué debe hacer exactamente")
    print("3. CONTEXTO - Proporciona información de fondo relevante")
    print("4. RAZONAMIENTO - Establece prioridades y requisitos de verificación")
    print("5. FORMATO DE SALIDA - Define cómo debe estructurarse la respuesta")
    print("6. CONDICIONES DE FINALIZACIÓN - Especifica cuándo está completo")
    
    return prompt

if __name__ == "__main__":
    # Ejecutar demostración
    prompt = demonstrate_prompt_structure()
    print("\nPrompt creado exitosamente usando la anatomía recomendada!")

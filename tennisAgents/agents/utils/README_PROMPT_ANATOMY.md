# Anatomía de Prompts para Analistas de Tenis

Este módulo implementa la anatomía de prompts recomendada por OpenAI para GPT-5 y modelos avanzados de IA, aplicada específicamente a los analistas de tenis del sistema.

## Estructura de la Anatomía

La anatomía de un prompt efectivo se compone de 6 elementos principales:

### 1. **ROL (Role)**
Define claramente quién es el agente y cuál es su especialización.
- Ejemplo: "Analista deportivo experto en tenis especializado en análisis profundo de rendimiento de jugadores"

### 2. **TAREA (Task)**
Especifica exactamente qué debe hacer el agente.
- Descripción clara de la tarea principal
- Lista de pasos específicos a seguir (3-7 pasos)
- Enfoque en planificación conceptual

### 3. **CONTEXTO (Context)**
Proporciona información de fondo relevante.
- Situación específica del análisis
- Factores que deben considerarse
- Exclusiones claras (qué NO incluir)

### 4. **RAZONAMIENTO (Reasoning)**
Establece cómo debe pensar y verificar el agente.
- Prioridades de razonamiento
- Requisitos de verificación
- Criterios de calidad

### 5. **FORMATO DE SALIDA (Output Format)**
Define cómo debe estructurarse la respuesta.
- Estructura del informe
- Formato específico requerido
- Elementos que debe contener

### 6. **CONDICIONES DE FINALIZACIÓN (Completion Conditions)**
Especifica cuándo está completa la tarea.
- Criterios de éxito
- Elementos que deben estar presentes
- Validación requerida

## Uso del Sistema

### Anatomías Predefinidas

El sistema incluye anatomías predefinidas para todos los tipos de analistas:

```python
from tennisAgents.agents.utils.prompt_anatomy import TennisAnalystAnatomies

# Obtener anatomía para analista de jugadores
anatomy = TennisAnalystAnatomies.player_analyst()

# Obtener anatomía para analista de noticias
anatomy = TennisAnalystAnatomies.news_analyst()

# Obtener anatomía para analista de cuotas
anatomy = TennisAnalystAnatomies.odds_analyst()

# Obtener anatomía para analista de torneos
anatomy = TennisAnalystAnatomies.tournament_analyst()

# Obtener anatomía para analista del clima
anatomy = TennisAnalystAnatomies.weather_analyst()

# Obtener anatomía para analista de redes sociales
anatomy = TennisAnalystAnatomies.social_media_analyst()
```

### Constructor de Prompts

```python
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder

# Crear prompt estructurado
prompt = PromptBuilder.create_structured_prompt(
    anatomy=anatomy,
    tools_info="Descripción de herramientas disponibles",
    additional_context="Contexto adicional específico"
)
```

### Ejemplo Completo

```python
def create_analyst_prompt():
    # 1. Obtener anatomía
    anatomy = TennisAnalystAnatomies.player_analyst()
    
    # 2. Definir herramientas
    tools_info = """
    • get_atp_rankings() - Obtiene ranking ATP actual
    • get_recent_matches() - Obtiene partidos recientes
    """
    
    # 3. Definir contexto adicional
    additional_context = """
    PROCESO RECOMENDADO:
    1. Obtener ranking ATP
    2. Analizar partidos recientes
    3. Evaluar rendimiento en superficie
    """
    
    # 4. Crear prompt
    prompt = PromptBuilder.create_structured_prompt(
        anatomy=anatomy,
        tools_info=tools_info,
        additional_context=additional_context
    )
    
    return prompt
```

## Ventajas de la Nueva Anatomía

### 1. **Estructura Clara**
- Cada prompt sigue la misma estructura lógica
- Fácil de entender y mantener
- Consistencia entre diferentes analistas

### 2. **Mejor Rendimiento**
- Prompts más claros y específicos
- Menor ambigüedad para el modelo
- Resultados más consistentes y precisos

### 3. **Mantenibilidad**
- Fácil modificación de prompts individuales
- Reutilización de anatomías comunes
- Separación clara de responsabilidades

### 4. **Escalabilidad**
- Fácil agregar nuevos tipos de analistas
- Anatomías personalizables
- Sistema modular y extensible

## Crear Anatomías Personalizadas

Para crear una nueva anatomía personalizada:

```python
from tennisAgents.agents.utils.prompt_anatomy import PromptAnatomy

custom_anatomy = PromptAnatomy(
    role="Descripción del rol",
    task="Descripción de la tarea",
    task_steps=["Paso 1", "Paso 2", "Paso 3"],
    context="Contexto del análisis",
    exclusions=["Qué no incluir"],
    reasoning_priorities=["Prioridad 1", "Prioridad 2"],
    verification_requirements=["Requisito 1", "Requisito 2"],
    output_format="Formato de salida requerido",
    output_structure="1. Sección 1\n2. Sección 2",
    completion_criteria=["Criterio 1", "Criterio 2"]
)
```

## Migración de Prompts Existentes

Los prompts existentes han sido refactorizados para usar la nueva anatomía sin cambiar su funcionalidad:

- **players.py** - ✅ Refactorizado
- **news.py** - ✅ Refactorizado
- **odds.py** - ✅ Refactorizado
- **tournament.py** - ✅ Refactorizado
- **weather.py** - ✅ Refactorizado
- **social_media.py** - ✅ Refactorizado

**🎉 ¡TODOS LOS ANALISTAS HAN SIDO REFACTORIZADOS EXITOSAMENTE!**

## Archivos del Sistema

- `prompt_anatomy.py` - Clases principales y anatomías predefinidas
- `prompt_examples.py` - Ejemplos de uso y demostraciones
- `README_PROMPT_ANATOMY.md` - Esta documentación

## Beneficios para el Usuario Final

1. **Análisis más preciso** - Prompts más claros producen mejores resultados
2. **Consistencia** - Todos los analistas siguen la misma metodología
3. **Transparencia** - Es fácil entender qué hace cada analista
4. **Mantenimiento** - Sistema más fácil de mantener y mejorar
5. **Escalabilidad** - Fácil agregar nuevos tipos de análisis

## Próximos Pasos

1. Refactorizar los analistas restantes
2. Crear anatomías para otros tipos de agentes
3. Implementar validación automática de prompts
4. Agregar métricas de rendimiento de prompts
5. Crear interfaz visual para edición de anatomías

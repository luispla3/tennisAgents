"""
Prompt Anatomy Utilities - Implementación de la anatomía de prompts recomendada por OpenAI
Basado en las mejores prácticas para GPT-5 y modelos avanzados de IA
"""

from dataclasses import dataclass
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


@dataclass
class PromptAnatomy:
    """Estructura de la anatomía de un prompt siguiendo las mejores prácticas de OpenAI"""
    
    # 1. ROL (Role)
    role: str
    
    # 2. TAREA (Task)
    task: str
    task_steps: List[str]
    
    # 3. CONTEXTO (Context)
    context: str
    
    # 4. RAZONAMIENTO (Reasoning)
    reasoning_priorities: List[str]
    verification_requirements: List[str]
    
    # 5. FORMATO DE SALIDA (Output Format)
    output_format: str
    
    # 6. CONDICIONES DE FINALIZACIÓN (Completion Conditions)
    completion_criteria: List[str]
    
    # Argumentos opcionales con valores por defecto
    exclusions: Optional[List[str]] = None
    output_structure: Optional[str] = None


class PromptBuilder:
    """Constructor de prompts siguiendo la anatomía recomendada"""
    
    @staticmethod
    def build_system_message(anatomy: PromptAnatomy, **kwargs) -> str:
        """Construye el mensaje del sistema siguiendo la anatomía del prompt"""
        
        # 1. ROL
        system_parts = [f"ROL: {anatomy.role}\n"]
        
        # 2. TAREA
        system_parts.append("TAREA:")
        system_parts.append(anatomy.task)
        system_parts.append("PASOS A SEGUIR:")
        for i, step in enumerate(anatomy.task_steps, 1):
            system_parts.append(f"{i}. {step}")
        system_parts.append("")
        
        # 3. CONTEXTO
        system_parts.append("CONTEXTO:")
        system_parts.append(anatomy.context)
        if anatomy.exclusions:
            system_parts.append("EXCLUSIONES:")
            for exclusion in anatomy.exclusions:
                system_parts.append(f"• {exclusion}")
        system_parts.append("")
        
        # 4. RAZONAMIENTO
        system_parts.append("RAZONAMIENTO:")
        system_parts.append("PRIORIDADES:")
        for priority in anatomy.reasoning_priorities:
            system_parts.append(f"• {priority}")
        system_parts.append("REQUISITOS DE VERIFICACIÓN:")
        for requirement in anatomy.verification_requirements:
            system_parts.append(f"• {requirement}")
        system_parts.append("")
        
        # 5. FORMATO DE SALIDA
        system_parts.append("FORMATO DE SALIDA:")
        system_parts.append(anatomy.output_format)
        if anatomy.output_structure:
            system_parts.append(anatomy.output_structure)
        system_parts.append("")
        
        # 6. CONDICIONES DE FINALIZACIÓN
        system_parts.append("CONDICIONES DE FINALIZACIÓN:")
        for criterion in anatomy.completion_criteria:
            system_parts.append(f"• {criterion}")
        
        return "\n".join(system_parts)
    
    @staticmethod
    def create_structured_prompt(
        anatomy: PromptAnatomy,
        tools_info: str = "",
        additional_context: str = "",
        **kwargs
    ) -> ChatPromptTemplate:
        """Crea un prompt estructurado completo con la anatomía recomendada"""
        
        system_message = PromptBuilder.build_system_message(anatomy, **kwargs)
        
        # Agregar información de herramientas si está disponible
        if tools_info:
            system_message += f"\n\nHERRAMIENTAS DISPONIBLES:\n{tools_info}"
        
        # Agregar contexto adicional si se proporciona
        if additional_context:
            system_message += f"\n\nCONTEXTO ADICIONAL:\n{additional_context}"
        
        # Crear la plantilla del prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "{user_message}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        return prompt



# Anatomías predefinidas para diferentes tipos de analistas
class TennisAnalystAnatomies:
    """Anatomías de prompts específicas para analistas de tenis"""
    
    @staticmethod
    def player_analyst() -> PromptAnatomy:
        """Anatomía para el analista de jugadores"""
        return PromptAnatomy(
            role="Analista deportivo experto en tenis especializado en análisis profundo de rendimiento de jugadores",
            
            task="Analizar en profundidad el rendimiento de un jugador específico contra su oponente en el contexto de un partido de tenis",
            
            task_steps=[
                "Obtener ranking ATP actual para contextualizar posiciones de ambos jugadores",
                "Consultar reportes de lesiones para evaluar estado físico actual",
                "Analizar partidos recientes de ambos jugadores (últimos 20-30 partidos)",
                "Evaluar rendimiento específico en la superficie del torneo",
                "Revisar historial head-to-head para patrones históricos",
                "Sintetizar hallazgos en un informe estructurado"
            ],
            
            context="Análisis de rendimiento para un partido específico de tenis, considerando múltiples factores que pueden influir en el resultado",
            
            exclusions=[
                "Análisis genérico sin datos específicos",
                "Información desactualizada o no verificada",
                "Opiniones subjetivas sin respaldo de datos"
            ],
            
            reasoning_priorities=[
                "Priorizar precisión: usar solo datos verificados y actualizados",
                "Enfocarse en análisis cuantitativo y estadístico",
                "Considerar contexto específico del torneo y superficie",
                "Identificar patrones y tendencias relevantes"
            ],
            
            verification_requirements=[
                "Verificar que todas las estadísticas provengan de fuentes oficiales",
                "Confirmar fechas y resultados de partidos recientes",
                "Validar rankings y posiciones actuales",
                "Contrastar información con múltiples fuentes cuando sea posible"
            ],
            
            output_format="Informe en prosa con conclusiones verificadas por jugador, comparación directa, servicio en superficie, H2H y limitaciones de datos (sin tablas markdown)",
            
            output_structure="1. Resumen ejecutivo\n2. Conclusiones por jugador\n3. Comparación directa\n4. Servicio en superficie\n5. Head-to-head\n6. Lectura del partido\n7. Limitaciones de datos",
            
            completion_criteria=[
                "Conclusiones basadas solo en datos devueltos por las herramientas",
                "Comparación directa de fortalezas y debilidades verificables",
                "Lectura cualitativa del partido sin probabilidades numéricas inventadas",
                "Sección explícita de limitaciones cuando falten datos"
            ]
        )
    
    @staticmethod
    def news_analyst() -> PromptAnatomy:
        """Anatomía para el analista de noticias"""
        return PromptAnatomy(
            role="Analista de noticias especializado en tenis profesional con enfoque en información crítica para predicciones",
            
            task="Investigar y generar informe detallado sobre noticias relevantes relacionadas con jugadores y torneos específicos",
            
            task_steps=[
                "Identificar noticias críticas de los últimos días sobre los jugadores",
                "Analizar impacto potencial en rendimiento deportivo",
                "Evaluar contexto del torneo y su relevancia",
                "Sintetizar implicaciones para el partido específico",
                "Organizar información en categorías relevantes"
            ],
            
            context="Análisis de noticias deportivas para evaluar factores que pueden influir en el rendimiento de jugadores en partidos específicos",
            
            exclusions=[
                "Noticias no relacionadas con tenis o los jugadores específicos",
                "Información de entretenimiento sin relevancia deportiva",
                "Rumores no verificados o especulaciones sin fundamento"
            ],
            
            reasoning_priorities=[
                "Priorizar noticias con impacto directo en rendimiento",
                "Enfocarse en información verificada y reciente",
                "Evaluar relevancia para el contexto específico del partido",
                "Identificar patrones o tendencias en las noticias"
            ],
            
            verification_requirements=[
                "Verificar fechas y fuentes de las noticias",
                "Confirmar relevancia para los jugadores específicos",
                "Validar impacto potencial en rendimiento deportivo",
                "Contrastar información con contexto del torneo"
            ],
            
            output_format="Informe estructurado con resumen ejecutivo, análisis por jugador, contexto del torneo e implicaciones para el partido",
            
            output_structure="1. Resumen ejecutivo\n2. Análisis por jugador\n3. Contexto del torneo\n4. Implicaciones para el partido\n5. Tabla de puntos clave",
            
            completion_criteria=[
                "Identificación de noticias críticas relevantes",
                "Análisis del impacto en rendimiento deportivo",
                "Contextualización para el partido específico",
                "Informe estructurado con información verificada"
            ]
        )
    
    @staticmethod
    def tournament_analyst() -> PromptAnatomy:
        """Anatomía para el analista de torneos"""
        return PromptAnatomy(
            role="Analista especializado en torneos de tenis con enfoque en contexto histórico y condiciones específicas",
            
            task="Analizar contexto histórico y condiciones específicas de un torneo de tenis para evaluar su impacto en los jugadores",
            
            task_steps=[
                "Investigar historia y tradición del torneo",
                "Analizar condiciones específicas (superficie, clima, altitud)",
                "Evaluar impacto en diferentes tipos de jugadores",
                "Revisar resultados históricos y patrones",
                "Sintetizar implicaciones para el partido específico"
            ],
            
            context="Análisis de contexto de torneos de tenis para entender factores que pueden influir en el rendimiento de jugadores específicos",
            
            exclusions=[
                "Información genérica sobre tenis sin contexto específico del torneo",
                "Datos históricos no verificados o desactualizados",
                "Análisis que no considere las condiciones específicas del torneo"
            ],
            
            reasoning_priorities=[
                "Priorizar información específica del torneo",
                "Enfocarse en condiciones que afectan el juego",
                "Considerar contexto histórico relevante",
                "Identificar patrones específicos del torneo"
            ],
            
            verification_requirements=[
                "Verificar información histórica del torneo",
                "Confirmar condiciones específicas actuales",
                "Validar datos de resultados históricos",
                "Contrastar información con fuentes oficiales"
            ],
            
            output_format="Informe estructurado con contexto histórico del torneo, condiciones específicas y su impacto en los jugadores",
            
            output_structure="1. Contexto histórico\n2. Condiciones específicas\n3. Impacto en jugadores\n4. Patrones históricos\n5. Implicaciones para el partido",
            
            completion_criteria=[
                "Análisis completo del contexto del torneo",
                "Identificación de condiciones específicas relevantes",
                "Evaluación del impacto en los jugadores",
                "Informe estructurado con información verificada"
            ]
        )
    
    @staticmethod
    def weather_analyst() -> PromptAnatomy:
        """Anatomía para el analista del clima"""
        return PromptAnatomy(
            role="Analista especializado en condiciones climáticas y su impacto en partidos de tenis al aire libre",
            
            task="Analizar condiciones climáticas actuales y pronósticos para evaluar su impacto en el rendimiento de los jugadores",
            
            task_steps=[
                "Obtener condiciones climáticas actuales del lugar del partido",
                "Analizar pronósticos meteorológicos para el horario del partido",
                "Evaluar impacto de condiciones climáticas en el juego",
                "Considerar adaptabilidad de cada jugador a diferentes condiciones",
                "Sintetizar implicaciones para el desarrollo del partido"
            ],
            
            context="Análisis de condiciones climáticas para partidos de tenis al aire libre, considerando su impacto en el rendimiento y estrategia",
            
            exclusions=[
                "Información climática no relacionada con el lugar del partido",
                "Pronósticos meteorológicos desactualizados",
                "Análisis que no considere el impacto específico en el tenis"
            ],
            
            reasoning_priorities=[
                "Priorizar información climática actual y precisa",
                "Enfocarse en impacto específico en el tenis",
                "Considerar adaptabilidad de los jugadores",
                "Evaluar cambios en condiciones durante el partido"
            ],
            
            verification_requirements=[
                "Verificar fuentes meteorológicas confiables",
                "Confirmar ubicación exacta del partido",
                "Validar timestamps de la información climática",
                "Contrastar pronósticos de múltiples fuentes"
            ],
            
            output_format="Informe estructurado con condiciones climáticas actuales, pronósticos y su impacto en el desarrollo del partido",
            
            output_structure="1. Condiciones actuales\n2. Pronósticos\n3. Impacto en el juego\n4. Adaptabilidad de jugadores\n5. Implicaciones para el partido",
            
            completion_criteria=[
                "Análisis completo de condiciones climáticas",
                "Pronósticos precisos para el horario del partido",
                "Evaluación del impacto en el rendimiento",
                "Informe estructurado con información verificada"
            ]
        )

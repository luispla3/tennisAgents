from datetime import datetime
from betfair_scraper.scraper import BetfairScraper
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import re


# ============================================================================
# SCRAPER DE BETFAIR - FUNCIONES PRINCIPALES
# ============================================================================

def extraer_apellido(nombre_completo):
    """
    Extrae el apellido (última palabra) del nombre completo.
    
    Ejemplos:
        "Maxim Mrva" -> "Mrva"
        "Carlos Alcaraz Garfia" -> "Garfia"
        "Medvedev" -> "Medvedev"
    
    Args:
        nombre_completo (str): Nombre completo del jugador
    
    Returns:
        str: El apellido (última palabra del nombre)
    """
    partes = nombre_completo.strip().split()
    # Si solo hay una palabra, es el apellido
    if len(partes) == 1:
        return partes[0]
    # Si hay varias palabras, tomar la última (apellido)
    return partes[-1]


def buscar_jugador(nombre_jugador):
    """
    Busca un jugador y devuelve información de su partido.
    
    Betfair suele listar los partidos solo con el apellido de los jugadores,
    por lo que esta función intenta buscar primero con el apellido y luego
    con el nombre completo como fallback.
    
    Args:
        nombre_jugador (str): Nombre completo del jugador o apellido
    
    Returns:
        dict: Información del partido encontrado, o None si no se encuentra
    """
    
    print(f"\n🔍 Buscando partidos de '{nombre_jugador}' en tenis...")
    
    scraper = BetfairScraper()
    
    # Buscar en partidos en juego
    markets = list(scraper.get_inplay_markets(sport='tennis', market_type='match_odds', live_stats=False))
    
    print(f"   📊 Total de partidos en juego: {len(markets)}")
    
    # Extraer el apellido para la búsqueda principal
    apellido = extraer_apellido(nombre_jugador)
    apellido_lower = apellido.lower()
    nombre_completo_lower = nombre_jugador.lower()
    
    print(f"   🔎 Buscando con apellido: '{apellido}'")
    if apellido != nombre_jugador:
        print(f"   🔎 También intentaré con nombre completo: '{nombre_jugador}'")
    
    # Buscar el jugador (primero por apellido, luego por nombre completo)
    for market in markets:
        event = market.get('event', '').lower()
        
        # Intentar primero con el apellido (más probable en Betfair)
        if apellido_lower in event:
            print(f"\n✅ PARTIDO ENCONTRADO! (búsqueda por apellido)")
            print(f"   Partido: {market.get('event')}")
            print(f"   Competición: {market.get('competition', 'N/A')}")
            print(f"   Event ID: {market.get('event_id')}")
            
            return {
                'event_name': market.get('event'),
                'event_id': market.get('event_id'),
                'competition': market.get('competition', 'N/A'),
                'market_id': market.get('market_id')
            }
        
        # Fallback: intentar con nombre completo
        elif nombre_completo_lower in event:
            print(f"\n✅ PARTIDO ENCONTRADO! (búsqueda por nombre completo)")
            print(f"   Partido: {market.get('event')}")
            print(f"   Competición: {market.get('competition', 'N/A')}")
            print(f"   Event ID: {market.get('event_id')}")
            
            return {
                'event_name': market.get('event'),
                'event_id': market.get('event_id'),
                'competition': market.get('competition', 'N/A'),
                'market_id': market.get('market_id')
            }
    
    print(f"\n❌ No se encontró ningún partido de '{nombre_jugador}' (ni con '{apellido}') en juego")
    return None


def setup_driver():
    """Configura Selenium WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def scrapear_partido(event_id, event_name):
    """Scrapea la página del partido y extrae todo el texto visible"""
    
    print(f"\n🌐 Accediendo a la página del partido...")
    
    # Construir URL
    url = f'https://www.betfair.es/sport/tennis?eventId={event_id}'
    
    # Inicializar driver
    driver = setup_driver()
    
    try:
        # Primero ir a la página de tenis
        driver.get('https://www.betfair.es/sport/tennis')
        time.sleep(3)
        
        # Buscar el enlace del partido
        print("   Buscando enlace del partido...")
        
        try:
            # Buscar elementos que contengan el nombre del evento
            elements = driver.find_elements(By.TAG_NAME, 'a')
            
            for elem in elements:
                try:
                    href = elem.get_attribute('href')
                    if href and str(event_id) in href and '/sport/tennis/' in href:
                        url = href
                        print(f"   ✅ URL encontrada: {url}")
                        break
                except:
                    pass
        except Exception as e:
            print(f"   ⚠️  No se pudo encontrar URL específica, usando genérica")
        
        # Navegar a la página del partido
        print(f"\n📄 Cargando página: {url}")
        driver.get(url)
        
        print("⏳ Esperando 10 segundos para carga completa...")
        time.sleep(10)
        
        # Scroll completo
        print("\n📜 Haciendo scroll por toda la página...")
        total_height = driver.execute_script("return document.body.scrollHeight")
        
        for scroll_pos in range(0, total_height, 800):
            driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
            time.sleep(0.5)
        
        print("   ✅ Scroll completado")
        
        # Volver arriba
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # Expandir elementos
        print("\n🔽 Expandiendo mercados...")
        try:
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            expanded = 0
            for btn in buttons[:200]:
                try:
                    if btn.is_displayed():
                        text = btn.text.lower()
                        if any(word in text for word in ['más', 'more', 'ver', 'mostrar', 'all', 'todo']):
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.3)
                            expanded += 1
                except:
                    pass
            print(f"   ✅ {expanded} elementos expandidos")
        except Exception as e:
            print(f"   ⚠️  Error expandiendo: {e}")
        
        time.sleep(3)
        
        # Extraer TODO el texto visible
        print("\n📝 Extrayendo texto visible...")
        
        script = """
        function getAllVisibleText() {
            let text = [];
            let walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode: function(node) {
                        let parent = node.parentElement;
                        if (!parent) return NodeFilter.FILTER_REJECT;
                        
                        let style = window.getComputedStyle(parent);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                            return NodeFilter.FILTER_REJECT;
                        }
                        
                        let nodeText = node.textContent.trim();
                        if (nodeText.length > 0) {
                            return NodeFilter.FILTER_ACCEPT;
                        }
                        return NodeFilter.FILTER_REJECT;
                    }
                }
            );
            
            let node;
            while(node = walker.nextNode()) {
                let nodeText = node.textContent.trim();
                if (nodeText) {
                    text.push(nodeText);
                }
            }
            return text;
        }
        return getAllVisibleText();
        """
        
        visible_text = driver.execute_script(script)
        
        print(f"   ✅ Extraídos {len(visible_text)} elementos de texto")
        
        return visible_text
        
    finally:
        driver.quit()


def parsear_mercados(text_elements):
    """Parsea los mercados del texto extraído"""
    
    print("\n🔍 Parseando mercados...")
    
    # Palabras clave que indican inicio de mercado
    market_keywords = [
        'cuotas de partido', 'apuestas a sets', 'tie-breaks', 'total', 'set', 
        'resultado correcto', 'hándicap', 'juego', 'ganador', 'gana', 
        'puntos', 'carrera', 'break', 'deuces', 'más/menos'
    ]
    
    # Patrón para detectar cuotas
    odds_pattern = re.compile(r'^\d+\.?\d*$')
    
    def is_market_name(text):
        """Detecta si una línea es nombre de mercado"""
        text_lower = text.lower().strip()
        has_keyword = any(keyword in text_lower for keyword in market_keywords)
        not_number = not odds_pattern.match(text.strip())
        reasonable_length = 10 < len(text) < 150
        return has_keyword and not_number and reasonable_length
    
    def is_odds(text):
        """Detecta si una línea es una cuota"""
        text = text.strip()
        return bool(odds_pattern.match(text))
    
    markets = []
    current_market = None
    i = 0
    
    while i < len(text_elements):
        line = text_elements[i].strip()
        
        if not line or len(line) < 2:
            i += 1
            continue
        
        # ¿Es nombre de mercado?
        if is_market_name(line):
            # Guardar mercado anterior
            if current_market and current_market.get('runners'):
                markets.append(current_market)
            
            # Nuevo mercado
            current_market = {
                'market_name': line,
                'runners': []
            }
            i += 1
            continue
        
        # Si tenemos un mercado activo, buscar pares (nombre_opción, cuota)
        if current_market:
            option_name = line
            
            # Mirar las siguientes líneas buscando la cuota
            for j in range(i + 1, min(i + 5, len(text_elements))):
                next_line = text_elements[j].strip()
                
                if is_odds(next_line):
                    # Encontramos la cuota
                    current_market['runners'].append({
                        'name': option_name,
                        'odds': float(next_line)
                    })
                    i = j
                    break
                elif is_market_name(next_line):
                    break
                elif next_line and not is_odds(next_line):
                    option_name = next_line
        
        i += 1
    
    # Guardar último mercado
    if current_market and current_market.get('runners'):
        markets.append(current_market)
    
    # Filtrar mercados que no son de apuestas (ruido)
    markets = [m for m in markets if len(m['runners']) > 0 and len(m['runners']) < 50]
    
    print(f"   ✅ {len(markets)} mercados parseados")
    
    return markets


def fetch_betfair_odds(nombre_jugador):
    """
    Función principal que ejecuta el scraper completo de Betfair.
    
    Args:
        nombre_jugador (str): Nombre del jugador a buscar
    
    Returns:
        dict: Diccionario con información del partido y mercados, o None si hay error
    """
    print("\n" + "=" * 100)
    print(f"🎾 SCRAPER DE BETFAIR - EXTRACTOR DE CUOTAS 🎾".center(100))
    print("=" * 100)
    
    # PASO 1: Buscar jugador
    print("\n" + "─" * 100)
    print("PASO 1: Buscar partido del jugador")
    print("─" * 100)
    
    event_info = buscar_jugador(nombre_jugador)
    
    if not event_info:
        print("\n❌ No se pudo encontrar el partido. Verifica que:")
        print("   • El jugador esté jugando ahora mismo (En Juego)")
        print("   • El nombre esté escrito correctamente")
        return None
    
    # PASO 2: Scrapear página
    print("\n" + "─" * 100)
    print("PASO 2: Scrapear página del partido")
    print("─" * 100)
    
    try:
        text_elements = scrapear_partido(event_info['event_id'], event_info['event_name'])
    except Exception as e:
        print(f"\n❌ Error al scrapear la página: {e}")
        return None
    
    # PASO 3: Parsear mercados
    print("\n" + "─" * 100)
    print("PASO 3: Extraer mercados y cuotas")
    print("─" * 100)
    
    markets = parsear_mercados(text_elements)
    
    if not markets:
        print("\n❌ No se pudieron extraer mercados de la página")
        return None
    
    # Retornar información estructurada
    result = {
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'player_searched': nombre_jugador,
        'event_name': event_info['event_name'],
        'event_id': event_info['event_id'],
        'competition': event_info['competition'],
        'total_markets': len(markets),
        'total_selections': sum(len(m['runners']) for m in markets),
        'markets': markets
    }
    
    print("\n" + "=" * 100)
    print("✅ PROCESO COMPLETADO EXITOSAMENTE".center(100))
    print("=" * 100)
    
    return result
# TennisAgents Web Application

Aplicación web para TennisAgents construida con FastAPI.

## Estructura

```
web/
├── app.py              # Servidor FastAPI principal
├── run.py              # Script para ejecutar el servidor
├── templates/          # Plantillas HTML (Jinja2)
│   └── index.html     # Página inicial
├── static/            # Archivos estáticos
│   ├── css/
│   │   └── style.css  # Estilos principales
│   └── js/
│       └── main.js    # JavaScript para interactividad
└── README.md          # Este archivo
```

## Instalación

1. Asegúrate de tener instaladas las dependencias del proyecto:
```bash
pip install -r requirements.txt
```

2. Las dependencias necesarias para la web son:
   - `fastapi`
   - `uvicorn[standard]`
   - `jinja2`
   - `python-multipart`

## Ejecución

**Opción 1: Desde el directorio raíz del proyecto:**
```bash
python -m web.run
```

**Opción 2: Desde la carpeta `web/`:**
```bash
cd web
python run.py
```

**Opción 3: Directamente con uvicorn (desde `web/`):**
```bash
cd web
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Luego abre tu navegador en: `http://localhost:8000`

## Tecnologías

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Templates**: Jinja2
- **Servidor**: Uvicorn

## Características

- Navbar moderno con dropdown para secciones de Tennis
- Diseño oscuro elegante inspirado en invertase.io
- Responsive design (mobile-friendly)
- Animaciones suaves y transiciones
- Listo para integrar con el sistema de análisis existente


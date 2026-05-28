# API Agente Financiero

Backend en Python con FastAPI, LangChain y Yahoo Finance para exponer un agente conversacional con memoria independiente por `conversation_id`.

## Arquitectura

```text
app/
├── main.py
├── api/
│   └── rutas_chat.py
├── agentes/
│   └── agente_conversacional.py
├── core/
│   ├── configuracion.py
│   ├── dependencias.py
│   └── logs.py
├── herramientas/
│   └── herramienta_financiera.py
├── modelos/
│   ├── esquemas_chat.py
│   └── mensaje.py
├── repositorios/
│   └── repositorio_memoria.py
└── servicios/
    └── servicio_chat.py
```

La API delega la lógica de negocio en `ServicioConversacional`. La memoria vive en `RepositorioMemoria`, abstraída detrás de una clase thread-safe para poder migrarla después a Redis o PostgreSQL. La consulta financiera está encapsulada en `HerramientaFinanciera`, reutilizable como tool de LangChain.

## Decisiones técnicas

- FastAPI expone endpoints tipados con modelos Pydantic y documentación automática en `/docs`.
- La memoria se mantiene en RAM con un diccionario protegido por `RLock`.
- `agent_loop` muestra explícitamente el flujo del agente: recibe el mensaje, lee historial, evalúa contexto, decide si usa tool, ejecuta Yahoo Finance, suma el resultado y genera la respuesta.
- Si `OPENAI_API_KEY` está configurada, la respuesta final se redacta con `ChatOpenAI` mediante LangChain.
- Si no hay API key, la API sigue funcionando con respuesta determinística, útil para correr el challenge sin servicios externos pagos.

## Endpoints

### `POST /chat`

Envía un mensaje a una conversación.

```json
{
  "conversation_id": "abc123",
  "mensaje": "¿Cómo está Apple hoy?"
}
```

Respuesta:

```json
{
  "conversation_id": "abc123",
  "respuesta": "..."
}
```

### `GET /chat/{id}`

Devuelve el historial completo de una conversación.

## Correr localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La API queda disponible en:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

Opcionalmente podés configurar un LLM:

```bash
export OPENAI_API_KEY="tu_api_key"
export MODELO_LLM="gpt-4o-mini"
```

## Correr con Docker

```bash
docker build -t api-agente-financiero .
docker run --rm -p 8000:8000 api-agente-financiero
```

Con API key:

```bash
docker run --rm -p 8000:8000 -e OPENAI_API_KEY="tu_api_key" api-agente-financiero
```

## Ejemplos curl

Crear o continuar conversación:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"abc123","mensaje":"¿Cómo está Apple hoy?"}'
```

Consultar seguimiento usando el historial:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"abc123","mensaje":"¿Y su variación?"}'
```

Obtener historial:

```bash
curl http://127.0.0.1:8000/chat/abc123
```

## Flujo del agente

La función `agent_loop` representa el recorrido principal:

1. Recibe `conversation_id`, mensaje e historial.
2. Normaliza y valida el mensaje.
3. Lee el historial conversacional recibido desde el repositorio.
4. Evalúa si el contexto requiere información financiera.
5. Decide si debe usar la tool financiera y qué símbolo consultar.
6. Ejecuta `HerramientaFinanciera` con Yahoo Finance cuando corresponde.
7. Incorpora el resultado de la tool al contexto.
8. Genera la respuesta final con LangChain y LLM opcional, o con una salida determinística si no hay API key.
9. El servicio guarda el mensaje del usuario y la respuesta del asistente en la memoria de esa conversación.

## Notas

No se implementan autenticación, base de datos real, frontend, websocket, Redis, docker compose ni streaming. El foco es dejar una base simple, clara y lista para evolucionar.

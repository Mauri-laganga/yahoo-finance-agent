# API Agente Financiero

Backend en Python con FastAPI, LangChain opcional y Yahoo Finance. Expone un agente conversacional con memoria independiente por `conversation_id`, fallback determinístico sin LLM y una UI mínima para probar desde navegador.

## Arquitectura

```text
app/
├── api/                 # Entradas HTTP
├── casos_uso/           # Orquestación de casos de uso
├── agentes/             # agent_loop y grafo de estados
├── dominio/             # Conceptos del dominio del agente
├── puertos/             # Contratos internos
├── adaptadores/         # Implementaciones concretas
├── repositorios/        # Nombres compatibles históricos
├── herramientas/        # Yahoo Finance como tool
├── modelos/             # Modelos Pydantic
└── core/                # Configuración, dependencias y logs
```

Flujo conceptual:

```text
API / Entradas
  -> Casos de Uso
  -> Agente Conversacional
  -> Puertos
  -> Adaptadores
```

La reorganización es hexagonal ligera: `PuertoMemoria` define el contrato, `ImplementacionMemoriaRAM` lo implementa, y `RepositorioMemoria` queda como alias compatible para no romper imports existentes.

## Grafo Del Agente

`agent_loop` mantiene su firma pública, pero internamente recorre estados explícitos:

```text
INICIO
  -> LEER_HISTORIAL
  -> ANALIZAR_INTENCION
  -> DECIDIR_HERRAMIENTA
  -> EJECUTAR_HERRAMIENTA
  -> GENERAR_RESPUESTA
  -> FINALIZAR
```

Cada estado registra logs con `conversation_id`, decisión, símbolo financiero, uso de herramienta y errores. El grafo vive en `app/dominio/estados_agente.py`, lo que permite extender el agente sin convertir el flujo en lógica implícita.

## Memoria

La memoria sigue funcionando por `conversation_id`.

- Adaptador actual: RAM thread-safe con `RLock`.
- Puerto: `PuertoMemoria`.
- Compatibilidad: `RepositorioMemoria`.
- Límite configurable: `max_mensajes_historial`, por defecto `30`.
- Truncamiento: conserva los mensajes más recientes y evita iniciar el historial visible con una respuesta huérfana cuando es posible.

La estructura queda preparada para futuros adaptadores Redis o PostgreSQL sin cambiar los endpoints.

## Yahoo Finance

`HerramientaFinanciera` consulta Yahoo Finance con `yfinance` y expone una tool compatible con LangChain. Intenta primero `fast_info` y usa `history(period="1d")` como fallback. Devuelve precio, variación, market cap, moneda, mercado, empresa y fuente cuando están disponibles.

## LLM Opcional

Si `OPENAI_API_KEY` está configurada, el agente usa `ChatOpenAI` para redactar la respuesta final. Si no existe API key o falta `langchain-openai`, la API sigue funcionando con respuesta determinística.

## Endpoints

### `GET /`

```json
{
  "nombre": "API Agente Financiero",
  "version": "1.0.0",
  "docs": "/docs"
}
```

### `GET /health`

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### `POST /chat`

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

Devuelve el historial de una conversación.

### `GET /chat-ui`

Página HTML simple servida por FastAPI. Permite ingresar `conversation_id`, enviar mensajes y visualizar historial sin React ni frontend complejo.

## Correr Localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

URLs:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/chat-ui`

Variables opcionales:

```bash
export OPENAI_API_KEY="tu_api_key"
export MODELO_LLM="gpt-4o-mini"
export MAX_MENSAJES_HISTORIAL=30
```

## Correr Con Docker

```bash
docker build -t api-agente-financiero .
docker run --rm -p 8000:8000 api-agente-financiero
```

Con API key:

```bash
docker run --rm -p 8000:8000 -e OPENAI_API_KEY="tu_api_key" api-agente-financiero
```

## Tests

```bash
pytest -q
```

La suite cubre:

- memoria y truncamiento configurable
- conversaciones independientes
- contrato del endpoint chat
- integración financiera mockeada

## Ejemplos Curl

Healthcheck:

```bash
curl http://127.0.0.1:8000/health
```

Crear o continuar conversación:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"abc123","mensaje":"¿Cómo está AAPL hoy?"}'
```

Consultar seguimiento usando historial:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"abc123","mensaje":"¿Y su variación?"}'
```

Consultar otras acciones:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"msft-demo","mensaje":"MSFT"}'

curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"tsla-demo","mensaje":"TSLA"}'
```

Obtener historial:

```bash
curl http://127.0.0.1:8000/chat/abc123
```

## Estado Actual

No se implementan autenticación, base de datos real, Redis, docker compose, websocket ni streaming. La base queda simple, compatible con los contratos existentes y preparada para evolucionar hacia producción.

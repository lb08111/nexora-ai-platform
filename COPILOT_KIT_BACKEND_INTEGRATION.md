# Backend Integration Guide for Copilot Kit

Este documento descreve como integrar o frontend de chat e plugins com o backend Python (QwenPaw).

## 🔌 Endpoints Necessários

### 1. Chat Endpoint

**POST** `/api/chat`

Processa mensagens do usuário e retorna respostas do assistente.

#### Request
```json
{
  "message": "Pergunta do usuário",
  "history": [
    {
      "id": "msg-123-user",
      "role": "user",
      "content": "Mensagem anterior",
      "timestamp": "2026-06-12T20:00:00Z",
      "metadata": {}
    }
  ]
}
```

#### Response
```json
{
  "reply": "Resposta do assistente",
  "message": "Resposta do assistente (fallback)",
  "metadata": {
    "source": "qwenpaw",
    "model": "gpt-4",
    "tokens": 150
  }
}
```

### 2. Plugin Endpoints

#### GET `/api/plugins`
Lista todos os plugins disponíveis.

**Response:**
```json
{
  "plugins": [
    {
      "id": "weather",
      "name": "Weather",
      "version": "1.0.0",
      "description": "Check weather information",
      "enabled": true
    }
  ]
}
```

#### GET `/api/plugins/:id`
Obtém detalhes de um plugin específico.

#### POST `/api/plugins/:id/execute`
Executa uma ação dentro de um plugin.

**Request:**
```json
{
  "action": "search",
  "payload": {
    "city": "São Paulo"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "temperature": 25,
    "humidity": 60
  }
}
```

## 🏗️ Implementação no Backend

### Exemplo com FastAPI

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

app = FastAPI()

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str
    metadata: Optional[dict] = None

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

class ChatResponse(BaseModel):
    reply: str
    metadata: dict = {}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Processar mensagem com QwenPaw
        agent = get_agent()  # Obter instância do agente
        
        # Construir histórico para o agente
        history_text = "\n".join([
            f"{msg.role.upper()}: {msg.content}" 
            for msg in request.history
        ])
        
        # Enviar para o agente
        response = await agent.process_message(
            message=request.message,
            history=history_text
        )
        
        return ChatResponse(
            reply=response,
            metadata={
                "source": "qwenpaw",
                "model": agent.model_name
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/plugins")
async def list_plugins():
    plugins = get_available_plugins()
    return {"plugins": plugins}

@app.post("/api/plugins/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, payload: dict):
    try:
        plugin = get_plugin(plugin_id)
        result = await plugin.execute(payload)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Exemplo com Flask

```python
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    history = data.get('history', [])
    
    try:
        agent = get_agent()
        response = agent.process_message(message, history)
        
        return jsonify({
            'reply': response,
            'metadata': {'source': 'qwenpaw'}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plugins', methods=['GET'])
def list_plugins():
    plugins = get_available_plugins()
    return jsonify({'plugins': plugins})

@app.route('/api/plugins/<plugin_id>/execute', methods=['POST'])
def execute_plugin(plugin_id):
    try:
        plugin = get_plugin(plugin_id)
        result = plugin.execute(request.json)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## 🔐 CORS Configuration

Adicione CORS ao seu servidor backend para permitir requisições do frontend:

```python
# FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📝 Configuração do Cliente

### Variáveis de Ambiente

Crie um arquivo `.env.local` na pasta `website`:

```env
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
```

### Usar no Frontend

```tsx
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const chatService = {
  async sendMessage(message: string, history: ChatMessage[]) {
    const response = await fetch(`${apiUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    });
    return response.json();
  }
};
```

## 🚀 Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./src:/app/src

  frontend:
    build:
      context: ./website
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
```

## 🧪 Testando a Integração

```bash
# 1. Iniciar o backend
python -m uvicorn main:app --reload

# 2. Em outro terminal, iniciar o frontend
cd website
npm run dev

# 3. Acessar http://localhost:5173/copilot-kit-demo
```

## 📊 Monitoramento

Adicione logging para monitorar as interações:

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    logger.info(f"Chat request: {request.message}")
    logger.info(f"History length: {len(request.history)}")
    
    # Processamento...
    
    logger.info(f"Chat response: {response}")
    return ChatResponse(reply=response)
```

## 🤝 Plugin System Integration

### Registrar um Plugin no Backend

```python
class PluginManager:
    def __init__(self):
        self.plugins = {}
    
    def register(self, plugin_id: str, plugin: Plugin):
        self.plugins[plugin_id] = plugin
    
    def get(self, plugin_id: str):
        return self.plugins.get(plugin_id)
    
    def list_all(self):
        return [
            {
                'id': pid,
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description
            }
            for pid, plugin in self.plugins.items()
        ]

# Uso
plugin_manager = PluginManager()
plugin_manager.register('weather', WeatherPlugin())
plugin_manager.register('calculator', CalculatorPlugin())
```

Consulte a documentação principal em `website/src/components/README.md` para mais informações sobre o frontend.

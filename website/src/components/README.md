# Copilot Kit - Chat & Plugins System

Este é um sistema modular de chat e plugins para a Nexora AI Platform, desenvolvido em React com TypeScript.

## 📋 Estrutura

### Componentes de Chat (`/components/Chat`)

- **ChatContext** - Gerencia o estado global do chat, histórico de mensagens e comunicação com a API
- **CopilotChat** - Container principal que renderiza o chat completo
- **ChatMessage** - Renderiza mensagens individuais com avatares
- **ChatInput** - Input com suporte a multilinhas e teclado

### Componentes de Plugins (`/components/Plugins`)

- **PluginContext** - Gerencia registro e carregamento dinâmico de plugins
- **PluginGrid** - Exibe plugins em grid ou lista
- **PluginWrapper** - Wrapper para renderizar plugins com controles

### Plugins de Exemplo (`/components/Plugins/examples`)

- **WeatherPlugin** - Busca informações de clima
- **CalculatorPlugin** - Realiza cálculos matemáticos
- **NotesPlugin** - Tomar notas rápidas

## 🚀 Uso

### Integração Básica

```tsx
import { ChatProvider, CopilotChat } from '@/components/Chat';
import { PluginProvider, PluginGrid } from '@/components/Plugins';
import { examplePlugins } from '@/components/Plugins/examples';

export function MyApp() {
  return (
    <ChatProvider>
      <PluginProvider>
        <div className="flex gap-4">
          <CopilotChat title="Assistant" />
          <PluginGrid />
        </div>
      </PluginProvider>
    </ChatProvider>
  );
}
```

### Criar um Plugin Customizado

```tsx
import React from 'react';
import { PluginProps } from '@/components/Chat/types';

export const MyPlugin: React.FC<PluginProps> = ({ data, onClose, onAction }) => {
  return (
    <div>
      <p>Meu Plugin</p>
      <button onClick={() => onAction?.('myAction', { value: 123 })}>
        Execute Ação
      </button>
      <button onClick={onClose}>Fechar</button>
    </div>
  );
};

// Registrar o plugin
const myPluginDef: PluginDefinition = {
  id: 'my-plugin',
  name: 'My Plugin',
  version: '1.0.0',
  description: 'Descrição do meu plugin',
  component: MyPlugin,
};

// Usar
const { registerPlugin } = usePlugins();
registerPlugin(myPluginDef);
```

## 🎨 Personalização

### Temas

O sistema suporta temas claro e escuro através de classes CSS:
- `dark:` - Aplica estilos para modo escuro

### Estilos Globais

Os estilos são feitos com Tailwind CSS e podem ser customizados no `index.css`.

## 🔌 API Backend

O chat espera um endpoint em `/api/chat` que recebe:

```json
{
  "message": "Pergunta do usuário",
  "history": [{ "role": "user", "content": "...", "timestamp": "..." }]
}
```

E retorna:

```json
{
  "reply": "Resposta do assistente",
  "metadata": { "source": "..." }
}
```

## 📝 Tipos

```typescript
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

interface PluginDefinition {
  id: string;
  name: string;
  version: string;
  description: string;
  component: React.ComponentType<PluginProps>;
  hooks?: Record<string, (...args: unknown[]) => unknown>;
  config?: Record<string, unknown>;
}
```

## 🧪 Testando

Acesse a página de demo em `/copilot-kit-demo` para ver o sistema em ação.

## 📦 Dependências

- React 18.3+
- React Router 7+
- Tailwind CSS 4+
- TypeScript 5.6+

## 📄 Licença

Apache 2.0

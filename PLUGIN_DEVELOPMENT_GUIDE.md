# Guia: Criar um Plugin Personalizado

Este guia mostra como criar plugins customizados para o Copilot Kit.

## 📝 Estrutura Básica

```tsx
import React from 'react';
import { PluginProps } from '@/components/Chat/types';

export const MeuPlugin: React.FC<PluginProps> = ({ 
  data, 
  onClose, 
  onAction 
}) => {
  return (
    <div className="space-y-4">
      <h3 className="font-bold">Meu Plugin</h3>
      
      <button onClick={onClose}>Fechar</button>
    </div>
  );
};
```

## 🎯 Exemplo: Plugin de Tradutor

```tsx
import React, { useState } from 'react';
import { PluginProps } from '@/components/Chat/types';

interface TranslationResult {
  original: string;
  translated: string;
  language: string;
}

export const TranslatorPlugin: React.FC<PluginProps> = ({ onClose, onAction }) => {
  const [text, setText] = useState('');
  const [language, setLanguage] = useState('es');
  const [result, setResult] = useState<TranslationResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTranslate = async () => {
    if (!text.trim()) return;

    setLoading(true);
    try {
      const response = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language }),
      });

      const data = await response.json();
      setResult(data);
      
      // Notificar ação ao chat
      onAction?.('translate_complete', data);
    } catch (error) {
      console.error('Translation error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2">Texto a traduzir:</label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Digite o texto aqui..."
          className="w-full h-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Idioma:</label>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="es">Espanhol</option>
          <option value="fr">Francês</option>
          <option value="de">Alemão</option>
          <option value="pt">Português</option>
          <option value="ja">Japonês</option>
        </select>
      </div>

      {result && (
        <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Tradução para {result.language}:
          </p>
          <p className="text-lg text-green-600 dark:text-green-400 mt-2">
            {result.translated}
          </p>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleTranslate}
          disabled={loading || !text.trim()}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Traduzindo...' : 'Traduzir'}
        </button>
        <button
          onClick={onClose}
          className="px-4 py-2 bg-gray-400 text-white rounded hover:bg-gray-500"
        >
          Fechar
        </button>
      </div>
    </div>
  );
};
```

## 🔧 Registrando o Plugin

```tsx
// plugins/examples/index.ts
import { TranslatorPlugin } from './TranslatorPlugin';
import { PluginDefinition } from '../../Chat/types';

export const examplePlugins: PluginDefinition[] = [
  // ... plugins existentes
  {
    id: 'translator',
    name: 'Tradutor',
    version: '1.0.0',
    description: 'Traduza textos para diferentes idiomas',
    component: TranslatorPlugin,
    config: { 
      apiKey: '', 
      supportedLanguages: ['es', 'fr', 'de', 'pt', 'ja']
    },
  },
];
```

## 💬 Comunicação com o Chat

```tsx
// Dentro do plugin
const handleAction = () => {
  onAction?.('myAction', {
    type: 'notification',
    message: 'Ação concluída!',
    data: { /* dados relevantes */ }
  });
};
```

## 🎨 Estilos Recomendados

```tsx
// Usar classes Tailwind para consistência
const baseStyles = {
  container: 'space-y-4 p-4',
  label: 'block text-sm font-medium mb-2 text-gray-900 dark:text-white',
  input: 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white',
  button: 'px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50',
  success: 'bg-green-50 dark:bg-green-900/20 p-4 rounded text-green-600 dark:text-green-400',
  error: 'bg-red-50 dark:bg-red-900/20 p-4 rounded text-red-600 dark:text-red-400',
};
```

## 🧪 Testar Localmente

1. Adicione seu plugin ao arquivo `examples/index.ts`
2. Execute `npm run dev` na pasta website
3. Acesse `/copilot-kit-demo`
4. Procure pelo seu plugin na seção "Plugins"

## 📦 Ciclo de Vida do Plugin

```
1. Registro (registerPlugin)
   ↓
2. Carregamento (loadPlugin)
   ↓
3. Renderização (PluginWrapper)
   ↓
4. Interação (usuario interage)
   ↓
5. Ações (onAction callbacks)
   ↓
6. Descarregamento (unloadPlugin)
```

## 🔌 API Backend para Plugins

```python
# Backend (FastAPI)
from fastapi import FastAPI

app = FastAPI()

@app.post("/api/plugins/translator/translate")
async def translate(request: TranslateRequest):
    # Lógica de tradução
    result = await translate_text(request.text, request.language)
    return {
        "original": request.text,
        "translated": result,
        "language": request.language
    }
```

## 📚 Referência Completa de Props

```typescript
interface PluginProps {
  // Dados de configuração do plugin
  data?: Record<string, unknown>;
  
  // Callback para fechar o plugin
  onClose?: () => void;
  
  // Callback para executar ações
  onAction?: (action: string, payload: unknown) => void;
}
```

## 🚀 Dicas de Performance

1. **Memoize componentes frequentemente atualizados:**
```tsx
const MyComponent = React.memo(({ data }) => {
  // Componente
});
```

2. **Use callbacks com useCallback:**
```tsx
const handleClick = useCallback(() => {
  // Ação
}, []);
```

3. **Lazy load dados pesados:**
```tsx
const [data, setData] = useState(null);

useEffect(() => {
  const loadData = async () => {
    const result = await fetch('/api/heavy-data');
    setData(await result.json());
  };
  loadData();
}, []);
```

Pronto! Seu plugin personalizado está funcionando! 🎉

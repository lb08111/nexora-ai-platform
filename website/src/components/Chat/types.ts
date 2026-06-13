export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

export interface ChatContextType {
  messages: ChatMessage[];
  isLoading: boolean;
  error?: string;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  updateMessage: (id: string, content: string) => void;
}

export interface PluginDefinition {
  id: string;
  name: string;
  version: string;
  description: string;
  component: React.ComponentType<PluginProps>;
  hooks?: Record<string, (...args: unknown[]) => unknown>;
  config?: Record<string, unknown>;
}

export interface PluginProps {
  data?: Record<string, unknown>;
  onClose?: () => void;
  onAction?: (action: string, payload: unknown) => void;
}

export interface PluginManager {
  loadPlugin: (id: string) => Promise<PluginDefinition>;
  unloadPlugin: (id: string) => Promise<void>;
  getPlugin: (id: string) => PluginDefinition | undefined;
  listPlugins: () => PluginDefinition[];
  registerPlugin: (plugin: PluginDefinition) => void;
}

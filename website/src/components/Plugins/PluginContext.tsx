import React, { createContext, useContext, useState, useCallback } from 'react';
import { PluginDefinition, PluginManager } from '../Chat/types';

const PluginContext = createContext<PluginManager | undefined>(undefined);

export const PluginProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [plugins, setPlugins] = useState<Map<string, PluginDefinition>>(new Map());
  const [loadedPlugins, setLoadedPlugins] = useState<Set<string>>(new Set());

  const registerPlugin = useCallback((plugin: PluginDefinition) => {
    setPlugins(prev => new Map(prev).set(plugin.id, plugin));
  }, []);

  const loadPlugin = useCallback(async (id: string): Promise<PluginDefinition> => {
    const plugin = plugins.get(id);
    if (!plugin) throw new Error(`Plugin ${id} not found`);

    if (!loadedPlugins.has(id)) {
      // Simulate async plugin loading
      await new Promise(resolve => setTimeout(resolve, 100));
      setLoadedPlugins(prev => new Set(prev).add(id));
    }

    return plugin;
  }, [plugins, loadedPlugins]);

  const unloadPlugin = useCallback(async (id: string) => {
    setLoadedPlugins(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const getPlugin = useCallback(
    (id: string) => plugins.get(id),
    [plugins]
  );

  const listPlugins = useCallback(() => Array.from(plugins.values()), [plugins]);

  const value: PluginManager = {
    loadPlugin,
    unloadPlugin,
    getPlugin,
    listPlugins,
    registerPlugin,
  };

  return (
    <PluginContext.Provider value={value}>{children}</PluginContext.Provider>
  );
};

export const usePlugins = (): PluginManager => {
  const context = useContext(PluginContext);
  if (!context) throw new Error('usePlugins must be used within PluginProvider');
  return context;
};

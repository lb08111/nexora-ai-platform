import React, { useState } from 'react';
import { usePlugins } from './PluginContext';
import { PluginWrapper } from './PluginWrapper';

interface PluginGridProps {
  displayMode?: 'grid' | 'list';
  maxColumns?: number;
}

export const PluginGrid: React.FC<PluginGridProps> = ({
  displayMode = 'grid',
  maxColumns = 2,
}) => {
  const { listPlugins } = usePlugins();
  const [activePlugins, setActivePlugins] = useState<Set<string>>(new Set());

  const plugins = listPlugins();

  const handleTogglePlugin = (id: string) => {
    setActivePlugins(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (plugins.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No plugins available</p>
      </div>
    );
  }

  return (
    <div
      className={
        displayMode === 'grid'
          ? `grid gap-4 grid-cols-1 md:grid-cols-${maxColumns}`
          : 'flex flex-col gap-4'
      }
    >
      {plugins.map(plugin => (
        <PluginWrapper
          key={plugin.id}
          plugin={plugin}
          isActive={activePlugins.has(plugin.id)}
          onToggle={handleTogglePlugin}
        />
      ))}
    </div>
  );
};

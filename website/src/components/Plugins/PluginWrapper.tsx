import React, { useState } from 'react';
import { PluginDefinition } from '../Chat/types';
import clsx from 'clsx';

interface PluginWrapperProps {
  plugin: PluginDefinition;
  isActive: boolean;
  onToggle: (id: string) => void;
}

export const PluginWrapper: React.FC<PluginWrapperProps> = ({
  plugin,
  isActive,
  onToggle,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>();

  const handleToggle = async () => {
    if (!isActive) {
      setIsLoading(true);
      try {
        await new Promise(resolve => setTimeout(resolve, 300));
        onToggle(plugin.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load plugin');
      } finally {
        setIsLoading(false);
      }
    } else {
      onToggle(plugin.id);
    }
  };

  const PluginComponent = plugin.component;

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
      {/* Plugin Header */}
      <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {plugin.name}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {plugin.description}
          </p>
        </div>
        <button
          onClick={handleToggle}
          disabled={isLoading}
          className={clsx(
            'px-4 py-2 rounded font-medium transition-colors',
            isActive
              ? 'bg-red-600 text-white hover:bg-red-700'
              : 'bg-blue-600 text-white hover:bg-blue-700',
            isLoading && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isLoading ? 'Loading...' : isActive ? 'Close' : 'Open'}
        </button>
      </div>

      {/* Plugin Error */}
      {error && (
        <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-100 p-3 border-b border-red-300 dark:border-red-700">
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Plugin Content */}
      {isActive && (
        <div className="p-4">
          <PluginComponent
            data={plugin.config}
            onClose={() => onToggle(plugin.id)}
          />
        </div>
      )}
    </div>
  );
};

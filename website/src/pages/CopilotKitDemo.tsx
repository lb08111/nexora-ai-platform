import { useEffect } from 'react';
import { ChatProvider, CopilotChat } from '@/components/Chat';
import { PluginProvider, usePlugins, PluginGrid } from '@/components/Plugins';
import { examplePlugins } from '@/components/Plugins/examples';

function CopilotKitDemoContent() {
  const { registerPlugin } = usePlugins();

  useEffect(() => {
    examplePlugins.forEach(plugin => registerPlugin(plugin));
  }, [registerPlugin]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-screen overflow-hidden p-4">
      {/* Chat Section */}
      <div className="lg:col-span-2">
        <CopilotChat
          title="Copilot Assistant"
          subtitle="Chat and manage plugins"
        />
      </div>

      {/* Plugins Section */}
      <div className="overflow-y-auto">
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-4">
          <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
            Plugins
          </h2>
          <PluginGrid displayMode="list" />
        </div>
      </div>
    </div>
  );
}

export default function CopilotKitDemo() {
  return (
    <ChatProvider>
      <PluginProvider>
        <CopilotKitDemoContent />
      </PluginProvider>
    </ChatProvider>
  );
}

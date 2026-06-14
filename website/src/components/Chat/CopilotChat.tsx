import React, { useEffect, useRef } from 'react';
import { useChat } from './ChatContext';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import clsx from 'clsx';

interface CopilotChatProps {
  title?: string;
  subtitle?: string;
  disabled?: boolean;
}

export const CopilotChat: React.FC<CopilotChatProps> = ({
  title = 'Chat',
  subtitle,
  disabled = false,
}) => {
  const { messages, error, isLoading, clearMessages } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4">
        <h2 className="text-xl font-bold">{title}</h2>
        {subtitle && <p className="text-sm opacity-90">{subtitle}</p>}
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <p className="text-lg font-semibold mb-2">Start a conversation</p>
              <p className="text-sm">Send a message to begin chatting</p>
            </div>
          </div>
        )}

        {messages.map(message => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {error && (
          <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-100 p-3 rounded">
            <p className="text-sm font-semibold">Error</p>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {isLoading && (
          <div className="flex gap-2 justify-start items-end">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-xs font-bold">
              AI
            </div>
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Footer with controls */}
      {messages.length > 0 && (
        <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-3 flex justify-end">
          <button
            onClick={clearMessages}
            className={clsx(
              'text-sm px-3 py-1 rounded',
              'hover:bg-gray-100 dark:hover:bg-gray-800',
              'text-gray-600 dark:text-gray-400'
            )}
          >
            Clear
          </button>
        </div>
      )}

      {/* Input Area */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4">
        <ChatInput disabled={disabled} />
      </div>
    </div>
  );
};

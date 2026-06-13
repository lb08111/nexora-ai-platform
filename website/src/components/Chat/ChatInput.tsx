import React, { useState, useRef, useEffect } from 'react';
import { useChat } from './ChatContext';
import clsx from 'clsx';

interface ChatInputProps {
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  disabled = false,
  placeholder = 'Type your message...',
}) => {
  const [input, setInput] = useState('');
  const { sendMessage, isLoading } = useChat();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (input.trim() && !isLoading && !disabled) {
      await sendMessage(input);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-2 items-end bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || isLoading}
        rows={1}
        className={clsx(
          'flex-1 px-4 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white',
          'rounded border border-gray-300 dark:border-gray-600',
          'focus:outline-none focus:ring-2 focus:ring-blue-500',
          'resize-none max-h-[120px]',
          (disabled || isLoading) && 'opacity-50 cursor-not-allowed'
        )}
      />

      <button
        onClick={handleSend}
        disabled={!input.trim() || isLoading || disabled}
        className={clsx(
          'px-6 py-2 rounded font-medium transition-colors',
          'bg-blue-600 text-white hover:bg-blue-700',
          'disabled:bg-gray-400 disabled:cursor-not-allowed'
        )}
      >
        {isLoading ? '...' : 'Send'}
      </button>
    </div>
  );
};

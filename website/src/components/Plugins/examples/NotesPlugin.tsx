import React from 'react';
import { PluginProps } from '../../Chat/types';

export const NotesPlugin: React.FC<PluginProps> = ({ onClose }) => {
  const [notes, setNotes] = React.useState('');

  return (
    <div className="space-y-4">
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Write your notes here..."
        className="w-full h-48 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      <div className="flex gap-2 justify-end">
        <button
          onClick={() => setNotes('')}
          className="px-4 py-2 bg-gray-400 text-white rounded hover:bg-gray-500"
        >
          Clear
        </button>
        <button
          onClick={() => {
            navigator.clipboard.writeText(notes);
            alert('Notes copied to clipboard!');
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Copy
        </button>
      </div>

      <button
        onClick={onClose}
        className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
      >
        Close
      </button>
    </div>
  );
};

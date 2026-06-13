import React from 'react';
import { PluginProps } from '../../Chat/types';

export const CalculatorPlugin: React.FC<PluginProps> = ({ onClose }) => {
  const [input, setInput] = React.useState('');
  const [result, setResult] = React.useState<number | string>('');

  const calculate = () => {
    try {
      // eslint-disable-next-line no-new-func
      const calculated = Function('"use strict"; return (' + input + ')')();
      setResult(calculated);
    } catch (error) {
      setResult('Invalid expression');
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g., 2 + 2 * 3"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={calculate}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          Calculate
        </button>
        <button
          onClick={() => setInput('')}
          className="px-4 py-2 bg-gray-400 text-white rounded hover:bg-gray-500"
        >
          Clear
        </button>
      </div>

      {result && (
        <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded">
          <p className="text-sm text-gray-600 dark:text-gray-400">Result:</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{result}</p>
        </div>
      )}

      <button
        onClick={onClose}
        className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
      >
        Close
      </button>
    </div>
  );
};

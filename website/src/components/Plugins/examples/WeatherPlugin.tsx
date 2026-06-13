import React from 'react';
import { PluginProps } from '../../Chat/types';

export const WeatherPlugin: React.FC<PluginProps> = ({ onClose }) => {
  const [city, setCity] = React.useState('');
  const [weather, setWeather] = React.useState<Record<string, unknown> | null>(null);

  const handleSearch = async () => {
    if (!city.trim()) return;
    try {
      const response = await fetch(`/api/weather?city=${city}`);
      const data = await response.json();
      setWeather(data);
    } catch (error) {
      console.error('Weather fetch error:', error);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          type="text"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="Enter city name..."
          className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        />
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Search
        </button>
      </div>

      {weather && (
        <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {JSON.stringify(weather)}
          </p>
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

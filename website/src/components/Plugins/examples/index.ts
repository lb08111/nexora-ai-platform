import { WeatherPlugin } from './WeatherPlugin';
import { CalculatorPlugin } from './CalculatorPlugin';
import { NotesPlugin } from './NotesPlugin';
import { PluginDefinition } from '../../Chat/types';

export const examplePlugins: PluginDefinition[] = [
  {
    id: 'weather',
    name: 'Weather',
    version: '1.0.0',
    description: 'Check weather for any city',
    component: WeatherPlugin,
    config: { apiKey: '' },
  },
  {
    id: 'calculator',
    name: 'Calculator',
    version: '1.0.0',
    description: 'Perform mathematical calculations',
    component: CalculatorPlugin,
  },
  {
    id: 'notes',
    name: 'Notes',
    version: '1.0.0',
    description: 'Take and manage notes',
    component: NotesPlugin,
  },
];

/**
 * A2UI Core - 核心模块导出
 */

// Provider
export {
  A2UIProvider,
  useA2UI,
  useA2UIState,
  useA2UIRenderer
} from './A2UIProvider';

export type {
  A2UIProviderProps,
  A2UIContextValue,
  A2UIComponentSpec
} from './A2UIProvider';

// State Manager
export { A2UIStateManager } from './A2UIStateManager';

// Renderer
export {
  A2UIRenderer,
  DefaultA2UIErrorComponent,
  renderA2UI,
  renderA2UIBatch
} from './A2UIRenderer';

export type { RenderConfig } from './A2UIRenderer';

// Component Registry
export {
  A2UIComponentRegistry,
  a2uiRegistry,
  A2UIComponentType
} from './A2UIComponentRegistry';

export type {
  ComponentMetadata,
  PropSchema
} from './A2UIComponentRegistry';

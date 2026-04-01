/**
 * BroadcastChannel manager for cross-tab synchronization.
 *
 * Enables instant data sync between tabs of the same browser session.
 * When a mutation happens in Tab A, Tab B receives a message and can
 * refetch data immediately — zero network delay.
 *
 * Usage:
 *   // After a mutation (create, update, delete):
 *   syncChannel.publish('solicitacoes', { action: 'created' });
 *
 *   // In a component that displays data:
 *   const unsub = syncChannel.subscribe('solicitacoes', () => refetch());
 *   return () => unsub();
 *
 * Falls back silently if BroadcastChannel is not supported (~3% of browsers).
 *
 * @module services/syncChannel
 * @see Epic #1032
 */

export interface SyncEvent {
  channel: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

type Listener = (event: SyncEvent) => void;

const CHANNEL_NAME = 'aprender-sync';

let bc: BroadcastChannel | null = null;
const listeners = new Map<string, Set<Listener>>();

function getChannel(): BroadcastChannel | null {
  if (bc) return bc;
  if (typeof BroadcastChannel === 'undefined') return null;

  bc = new BroadcastChannel(CHANNEL_NAME);
  bc.onmessage = (event: MessageEvent<SyncEvent>) => {
    const { channel } = event.data;
    const channelListeners = listeners.get(channel);
    if (channelListeners) {
      channelListeners.forEach((fn) => fn(event.data));
    }
  };
  return bc;
}

/**
 * Publish a sync event to all other tabs.
 *
 * @param channel - Domain name (e.g. 'solicitacoes', 'availability')
 * @param payload - Event details (e.g. { action: 'created', id: 123 })
 */
function publish(channel: string, payload: Record<string, unknown> = {}): void {
  const ch = getChannel();
  if (!ch) return;

  const event: SyncEvent = {
    channel,
    payload,
    timestamp: Date.now(),
  };

  ch.postMessage(event);
}

/**
 * Subscribe to sync events from other tabs.
 *
 * @param channel - Domain name to listen for
 * @param callback - Called when another tab publishes to this channel
 * @returns Unsubscribe function (call in cleanup/unmount)
 */
function subscribe(channel: string, callback: Listener): () => void {
  getChannel(); // Ensure channel is initialized

  if (!listeners.has(channel)) {
    listeners.set(channel, new Set());
  }
  listeners.get(channel)!.add(callback);

  return () => {
    const set = listeners.get(channel);
    if (set) {
      set.delete(callback);
      if (set.size === 0) listeners.delete(channel);
    }
  };
}

export const syncChannel = { publish, subscribe } as const;

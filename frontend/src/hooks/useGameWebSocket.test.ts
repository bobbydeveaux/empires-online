import { renderHook, act } from '@testing-library/react';
import { useGameWebSocket } from './useGameWebSocket';
import { gamesAPI } from '../services/api';

// Mock the api module
jest.mock('../services/api', () => ({
  gamesAPI: {
    getGameState: jest.fn(),
  },
  getWebSocketUrl: jest.fn((gameId: number, token: string) => `ws://localhost/ws/${gameId}?token=${token}`),
}));

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: any) => void) | null = null;
  onclose: ((event: any) => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send = jest.fn();
  close = jest.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  // Test helpers
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.({} as Event);
  }

  simulateMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }

  simulateClose(code = 1000) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code } as CloseEvent);
  }

  static instances: MockWebSocket[] = [];
  static clear() {
    MockWebSocket.instances = [];
  }
  static latest(): MockWebSocket {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }
}

(global as any).WebSocket = MockWebSocket;

const mockGameState = {
  game: { id: 1, rounds: 5, rounds_remaining: 5, phase: 'waiting' as const, creator_id: 1, created_at: '2026-01-01' },
  players: [],
  leaderboard: [],
};

describe('useGameWebSocket', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    MockWebSocket.clear();
    (gamesAPI.getGameState as jest.Mock).mockResolvedValue(mockGameState);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should not connect when gameId is null', () => {
    renderHook(() =>
      useGameWebSocket({ gameId: null, token: 'test-token' })
    );
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it('should not connect when token is null', () => {
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: null })
    );
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it('should connect when gameId and token are provided', () => {
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it('should set status to connected on open', async () => {
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    expect(result.current.connectionStatus).toBe('connecting');

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    expect(result.current.connectionStatus).toBe('connected');
  });

  it('should fetch game state on connection open', async () => {
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    expect(gamesAPI.getGameState).toHaveBeenCalledWith(1);
  });

  it('should update game state from REST fetch', async () => {
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    // Wait for the async fetch to resolve
    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.gameState).toEqual(mockGameState);
  });

  it('should refetch state on player_joined message', async () => {
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    jest.clearAllMocks();
    (gamesAPI.getGameState as jest.Mock).mockResolvedValue(mockGameState);

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'player_joined',
        game_id: 1,
        player: { id: 2, username: 'player2' },
      });
    });

    expect(gamesAPI.getGameState).toHaveBeenCalledWith(1);
  });

  it('should refetch state on player_left message', async () => {
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    jest.clearAllMocks();
    (gamesAPI.getGameState as jest.Mock).mockResolvedValue(mockGameState);

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'player_left',
        game_id: 1,
        player: { id: 2, username: 'player2' },
      });
    });

    expect(gamesAPI.getGameState).toHaveBeenCalledWith(1);
  });

  it('should call onMessage callback', async () => {
    const onMessage = jest.fn();
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token', onMessage })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    const msg = { type: 'chat' as const, game_id: 1, player: { id: 1, username: 'p1' }, message: 'hello' };
    await act(async () => {
      MockWebSocket.latest().simulateMessage(msg);
    });

    expect(onMessage).toHaveBeenCalledWith(msg);
  });

  it('should set status to reconnecting on non-auth close', async () => {
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    await act(async () => {
      MockWebSocket.latest().simulateClose(1006); // Abnormal close
    });

    expect(result.current.connectionStatus).toBe('reconnecting');
  });

  it('should set status to disconnected on auth failure close (1008)', async () => {
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    await act(async () => {
      MockWebSocket.latest().simulateClose(1008);
    });

    expect(result.current.connectionStatus).toBe('disconnected');
  });

  it('should attempt reconnection with exponential backoff', async () => {
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
    });

    const initialCount = MockWebSocket.instances.length;

    // Simulate disconnect
    await act(async () => {
      MockWebSocket.latest().simulateClose(1006);
    });

    // After 1s, should reconnect
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(MockWebSocket.instances.length).toBe(initialCount + 1);
  });

  it('should close connection on unmount', async () => {
    const { unmount } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    const ws = MockWebSocket.latest();
    ws.readyState = MockWebSocket.OPEN;

    unmount();

    expect(ws.close).toHaveBeenCalled();
  });

  it('should use game_state from game_state_update message if provided', async () => {
    const updatedState = { ...mockGameState, game: { ...mockGameState.game, phase: 'development' as const } };

    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
      await Promise.resolve();
    });

    jest.clearAllMocks();

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'game_state_update',
        game_id: 1,
        game_state: updatedState,
      });
    });

    expect(result.current.gameState).toEqual(updatedState);
    // Should NOT have called REST since game_state was included
    expect(gamesAPI.getGameState).not.toHaveBeenCalled();
  });

  it('should fetch via REST if game_state_update has no game_state', async () => {
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
      await Promise.resolve();
    });

    jest.clearAllMocks();
    (gamesAPI.getGameState as jest.Mock).mockResolvedValue(mockGameState);

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'game_state_update',
        game_id: 1,
      });
    });

    expect(gamesAPI.getGameState).toHaveBeenCalledWith(1);
  });

  // --- Trade event tests ---

  const mockTrade = {
    id: 42,
    game_id: 1,
    proposer_country_id: 1,
    receiver_country_id: 2,
    offer_gold: 100,
    offer_people: 0,
    offer_territory: 0,
    request_gold: 0,
    request_people: 50,
    request_territory: 0,
    status: 'pending' as const,
    created_at: '2026-01-01T00:00:00Z',
  };

  it('should add trade to trades list on trade_proposed', async () => {
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
      await Promise.resolve();
    });

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'trade_proposed',
        game_id: 1,
        trade: mockTrade,
      });
    });

    expect(result.current.trades).toEqual([mockTrade]);
  });

  it('should call onTradeNotification on trade_proposed', async () => {
    const onTradeNotification = jest.fn();
    renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token', onTradeNotification })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
      await Promise.resolve();
    });

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'trade_proposed',
        game_id: 1,
        trade: mockTrade,
      });
    });

    expect(onTradeNotification).toHaveBeenCalledWith(
      'New trade proposal received (Trade #42)',
      'info',
    );
  });

  it('should remove trade and show success on trade_resolved accepted', async () => {
    const onTradeNotification = jest.fn();
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token', onTradeNotification })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
      await Promise.resolve();
    });

    // First add a trade
    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'trade_proposed',
        game_id: 1,
        trade: mockTrade,
      });
    });

    expect(result.current.trades).toHaveLength(1);

    jest.clearAllMocks();
    (gamesAPI.getGameState as jest.Mock).mockResolvedValue(mockGameState);

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'trade_resolved',
        game_id: 1,
        trade: { ...mockTrade, status: 'accepted' as const },
        resolution: 'accepted',
      });
    });

    expect(result.current.trades).toHaveLength(0);
    expect(onTradeNotification).toHaveBeenCalledWith(
      'Trade #42 was accepted',
      'success',
    );
    // Accepted trade should refetch game state (resources changed)
    expect(gamesAPI.getGameState).toHaveBeenCalledWith(1);
  });

  it('should remove trade and show error on trade_resolved rejected', async () => {
    const onTradeNotification = jest.fn();
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token', onTradeNotification })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
      await Promise.resolve();
    });

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'trade_proposed',
        game_id: 1,
        trade: mockTrade,
      });
    });

    jest.clearAllMocks();
    (gamesAPI.getGameState as jest.Mock).mockResolvedValue(mockGameState);

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'trade_resolved',
        game_id: 1,
        trade: { ...mockTrade, status: 'rejected' as const },
        resolution: 'rejected',
      });
    });

    expect(result.current.trades).toHaveLength(0);
    expect(onTradeNotification).toHaveBeenCalledWith(
      'Trade #42 was rejected',
      'error',
    );
    // Rejected trade should NOT refetch game state
    expect(gamesAPI.getGameState).not.toHaveBeenCalled();
  });

  it('should remove trade and show info on trade_resolved cancelled', async () => {
    const onTradeNotification = jest.fn();
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token', onTradeNotification })
    );

    await act(async () => {
      MockWebSocket.latest().simulateOpen();
      await Promise.resolve();
    });

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'trade_proposed',
        game_id: 1,
        trade: mockTrade,
      });
    });

    jest.clearAllMocks();
    (gamesAPI.getGameState as jest.Mock).mockResolvedValue(mockGameState);

    await act(async () => {
      MockWebSocket.latest().simulateMessage({
        type: 'trade_resolved',
        game_id: 1,
        trade: { ...mockTrade, status: 'cancelled' as const },
        resolution: 'cancelled',
      });
    });

    expect(result.current.trades).toHaveLength(0);
    expect(onTradeNotification).toHaveBeenCalledWith(
      'Trade #42 was cancelled',
      'info',
    );
    expect(gamesAPI.getGameState).not.toHaveBeenCalled();
  });

  it('should initialize with empty trades array', () => {
    const { result } = renderHook(() =>
      useGameWebSocket({ gameId: 1, token: 'test-token' })
    );

    expect(result.current.trades).toEqual([]);
  });
});

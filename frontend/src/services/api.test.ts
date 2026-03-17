// Mock axios before importing api module
jest.mock('axios', () => {
  const instance = {
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    get: jest.fn(),
    post: jest.fn(),
  };
  return {
    __esModule: true,
    default: { create: jest.fn(() => instance) },
  };
});

import { buildWebSocketUrl } from './api';

const originalLocation = window.location;

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  Object.defineProperty(window, 'location', {
    value: originalLocation,
    writable: true,
  });
});

function setLocation(protocol: string, host: string) {
  Object.defineProperty(window, 'location', {
    value: { protocol, host },
    writable: true,
  });
}

describe('buildWebSocketUrl', () => {
  it('builds ws:// URL from relative API base with token', () => {
    setLocation('http:', 'localhost:3000');
    localStorage.setItem('authToken', 'test-jwt-token');

    const url = buildWebSocketUrl(42);
    expect(url).toBe('ws://localhost:3000/ws/42?token=test-jwt-token');
  });

  it('builds wss:// URL when page is served over https', () => {
    setLocation('https:', 'example.com');
    localStorage.setItem('authToken', 'my-token');

    const url = buildWebSocketUrl(1);
    expect(url).toBe('wss://example.com/ws/1?token=my-token');
  });

  it('omits token query param when no auth token stored', () => {
    setLocation('http:', 'localhost:3000');

    const url = buildWebSocketUrl(5);
    expect(url).toBe('ws://localhost:3000/ws/5');
  });

  it('encodes special characters in token', () => {
    setLocation('http:', 'localhost:3000');
    localStorage.setItem('authToken', 'token with spaces&special=chars');

    const url = buildWebSocketUrl(1);
    expect(url).toContain('?token=token%20with%20spaces%26special%3Dchars');
  });
});

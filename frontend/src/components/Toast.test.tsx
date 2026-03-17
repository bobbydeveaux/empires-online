import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToastProvider, useToast } from './Toast';

const TestConsumer: React.FC = () => {
  const { showToast } = useToast();
  return (
    <div>
      <button onClick={() => showToast('Success message', 'success')}>Show Success</button>
      <button onClick={() => showToast('Error message', 'error')}>Show Error</button>
      <button onClick={() => showToast('Info message')}>Show Info</button>
    </div>
  );
};

describe('Toast', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders success toast when triggered', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    await userEvent.setup({ advanceTimers: jest.advanceTimersByTime }).click(
      screen.getByText('Show Success')
    );

    expect(screen.getByText('Success message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveClass('toast-success');
  });

  it('renders error toast when triggered', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    await userEvent.setup({ advanceTimers: jest.advanceTimersByTime }).click(
      screen.getByText('Show Error')
    );

    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveClass('toast-error');
  });

  it('renders info toast by default', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    await userEvent.setup({ advanceTimers: jest.advanceTimersByTime }).click(
      screen.getByText('Show Info')
    );

    expect(screen.getByText('Info message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveClass('toast-info');
  });

  it('auto-dismisses after timeout', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    await userEvent.setup({ advanceTimers: jest.advanceTimersByTime }).click(
      screen.getByText('Show Success')
    );

    expect(screen.getByText('Success message')).toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(4000);
    });

    expect(screen.queryByText('Success message')).not.toBeInTheDocument();
  });

  it('dismisses toast on close button click', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await user.click(screen.getByText('Show Success'));

    expect(screen.getByText('Success message')).toBeInTheDocument();

    await user.click(screen.getByLabelText('Dismiss notification'));

    expect(screen.queryByText('Success message')).not.toBeInTheDocument();
  });

  it('can display multiple toasts simultaneously', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await user.click(screen.getByText('Show Success'));
    await user.click(screen.getByText('Show Error'));

    expect(screen.getByText('Success message')).toBeInTheDocument();
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.getAllByRole('alert')).toHaveLength(2);
  });

  it('throws error when useToast is used outside ToastProvider', () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow(
      'useToast must be used within a ToastProvider'
    );
    spy.mockRestore();
  });
});

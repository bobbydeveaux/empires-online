# Toast Notification System

The application uses a toast notification system for displaying action confirmations, errors, and informational messages.

## Architecture

- **`ToastProvider`** (`frontend/src/components/Toast.tsx`) — React context provider that manages toast state. Wraps the app in `App.tsx`.
- **`useToast`** hook — Exposes `showToast(message, variant?)` to any component within the provider tree.
- **Toast component** — Renders toast notifications in a fixed container at the top-right of the viewport.

## Usage

```tsx
import { useToast } from '../components/Toast';

const MyComponent: React.FC = () => {
  const { showToast } = useToast();

  const handleAction = async () => {
    try {
      await someApiCall();
      showToast('Action completed', 'success');
    } catch (err) {
      showToast('Something went wrong', 'error');
    }
  };

  return <button onClick={handleAction}>Do something</button>;
};
```

## Variants

| Variant   | Use case                          | Color  |
|-----------|-----------------------------------|--------|
| `success` | Action confirmations              | Green  |
| `error`   | API errors, validation failures   | Red    |
| `info`    | Informational messages (default)  | Blue   |

## Behavior

- Toasts auto-dismiss after **4 seconds**
- Users can manually dismiss via the close button
- Multiple toasts stack vertically
- Container uses `aria-live="polite"` and each toast has `role="alert"` for accessibility

## Mobile

On viewports ≤768px, toasts span the full width of the screen (with 10px margins on each side).

## Integration in Game.tsx

Game action errors (start game, execute development, perform action, advance round) and success confirmations are displayed as toasts instead of inline error divs.

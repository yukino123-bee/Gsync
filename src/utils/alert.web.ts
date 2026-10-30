import type { AlertButton } from 'react-native';

/** react-native-web's Alert is a no-op, so this maps the buttons-style API onto window.confirm / alert. */
export const Alert = {
  alert(title: string, message?: string, buttons?: AlertButton[]) {
    const text = message ? `${title}\n\n${message}` : title;
    const action = buttons?.find((b) => b.style !== 'cancel');
    if (!action || buttons!.length < 2) {
      window.alert(text);
      buttons?.[0]?.onPress?.();
      return;
    }
    if (window.confirm(text)) action.onPress?.();
  },
};

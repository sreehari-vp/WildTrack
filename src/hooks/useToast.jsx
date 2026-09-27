import { createContext, useContext, useMemo, useState } from "react";
const ToastContext = createContext(null);
const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  const value = useMemo(
    () => ({
      toasts,
      pushToast: (toast) => {
        const id = crypto.randomUUID();
        setToasts((current) => [...current, { ...toast, id }]);
        window.setTimeout(() => setToasts((current) => current.filter((item) => item.id !== id)), 4200);
      },
      removeToast: (id) => setToasts((current) => current.filter((item) => item.id !== id))
    }),
    [toasts]
  );
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
};
const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
};
export {
  ToastProvider,
  useToast
};

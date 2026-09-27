import { X } from "lucide-react";
import { useToast } from "../../hooks/useToast";
const ToastViewport = () => {
  const { toasts, removeToast } = useToast();
  return <div className="fixed bottom-4 right-4 z-[1000] flex w-80 flex-col gap-2">
      {toasts.map((toast) => <div key={toast.id} className="rounded-panel border border-line bg-paper p-3 shadow-md">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-medium text-ink-900">{toast.title}</p>
            <button aria-label="Dismiss notification" onClick={() => removeToast(toast.id)}>
              <X className="h-4 w-4 text-ink-400" strokeWidth={1.75} />
            </button>
          </div>
          {toast.actionLabel ? <button
    className="mt-2 text-sm font-medium text-forest-700"
    onClick={() => {
      toast.onAction?.();
      removeToast(toast.id);
    }}
  >
              {toast.actionLabel}
            </button> : null}
        </div>)}
    </div>;
};
export {
  ToastViewport
};

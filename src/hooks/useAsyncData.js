import { useCallback, useEffect, useRef, useState } from "react";
const useAsyncData = (load, deps = [], options = {}) => {
  const [data, setData] = useState();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState();
  const hasDataRef = useRef(false);
  const runLoad = useCallback((background = false) => {
    const shouldShowLoading = !background || !hasDataRef.current;
    if (shouldShowLoading) {
      setLoading(true);
    }
    if (!background) {
      setError(void 0);
    }
    load().then((nextData) => {
      hasDataRef.current = true;
      setData(nextData);
      setError(void 0);
    }).catch((caught) => {
      if (shouldShowLoading) {
        setError(caught);
      }
    }).finally(() => {
      if (shouldShowLoading) {
        setLoading(false);
      }
    });
  }, deps);
  const retry = useCallback(() => runLoad(false), [runLoad]);
  useEffect(() => {
    retry();
  }, [retry]);
  useEffect(() => {
    if (!options.intervalMs) return;
    const timer = window.setInterval(() => runLoad(true), options.intervalMs);
    return () => window.clearInterval(timer);
  }, [options.intervalMs, runLoad]);
  return { data, loading, error, retry };
};
export {
  useAsyncData
};

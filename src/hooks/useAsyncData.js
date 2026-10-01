import { useCallback, useEffect, useRef, useState } from "react";
const useAsyncData = (load, deps = [], options = {}) => {
  const [data, setData] = useState();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState();
  const hasDataRef = useRef(false);
  const requestIdRef = useRef(0);
  const runLoad = useCallback((background = false) => {
    if (background && !hasDataRef.current) return;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    const shouldShowLoading = !background || !hasDataRef.current;
    if (shouldShowLoading) {
      setLoading(true);
    }
    if (!background) {
      setError(void 0);
    }
    load().then((nextData) => {
      if (requestId !== requestIdRef.current) return;
      hasDataRef.current = true;
      setData(nextData);
      setError(void 0);
    }).catch((caught) => {
      if (requestId !== requestIdRef.current) return;
      if (shouldShowLoading) {
        setError(caught);
      }
    }).finally(() => {
      if (requestId !== requestIdRef.current) return;
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

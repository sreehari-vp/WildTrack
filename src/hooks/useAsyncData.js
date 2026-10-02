import { useCallback, useEffect, useRef, useState } from "react";

export const useAsyncData = (load, deps = [], options = {}) => {
  const [state, setState] = useState({ data: undefined, loading: true, error: undefined, updatedAt: null });
  const [revision, setRevision] = useState(0);
  const loader = useRef(load);
  loader.current = load;
  const retry = useCallback(() => setRevision((value) => value + 1), []);
  const refresh = useCallback(async () => {
    const data = await loader.current();
    setState({ data, loading: false, error: undefined, updatedAt: new Date() });
    return data;
  }, []);
  const intervalMs = Number.isFinite(options.intervalMs) && options.intervalMs >= 1000 ? options.intervalMs : 0;
  useEffect(() => {
    let active = true;
    let timer;
    const run = async (background = false) => {
      if (!background) setState({ data: undefined, loading: true, error: undefined, updatedAt: null });
      try {
        const data = await loader.current();
        if (active) setState({ data, loading: false, error: undefined, updatedAt: new Date() });
      } catch (error) {
        if (active) setState((current) => ({ ...current, loading: false, error }));
      } finally {
        // Wait for completion so slow requests cannot overlap or starve updates.
        if (active && intervalMs) timer = window.setTimeout(() => run(true), intervalMs);
      }
    };
    run();
    return () => { active = false; window.clearTimeout(timer); };
  }, [...deps, intervalMs, revision]);
  return { ...state, retry, refresh };
};

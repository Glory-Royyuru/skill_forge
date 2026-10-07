import { useCallback, useEffect, useState } from "react";

// Fetch on mount (and when deps change); exposes reload for retry buttons.
export function useLoad(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(fn, deps);
  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    load()
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => setState({ data: null, error, loading: false }));
  }, [load]);
  useEffect(reload, [reload]);
  return { ...state, reload };
}

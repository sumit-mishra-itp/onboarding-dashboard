import { useCallback, useEffect, useState } from "react";

/** Load data on mount (and when deps change). `reload` re-fetches; errors land in `error`. */
export function useResource<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const reload = useCallback(
    () => load().then((d) => { setData(d); setError(""); }, (e: Error) => setError(e.message)),
    deps, // eslint-disable-line react-hooks/exhaustive-deps
  );
  useEffect(() => void reload(), [reload]);
  return { data, error, reload, setData };
}

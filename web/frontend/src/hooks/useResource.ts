import { useEffect, useState } from "react";

import { api } from "../services/http";

export function useResource<T>(path: string | null, keepPrevious = false) {
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const refresh = () => setRevision((v) => v + 1);
    window.addEventListener("sigma:refresh", refresh);
    return () => window.removeEventListener("sigma:refresh", refresh);
  }, []);
  const [state, setState] = useState<{
    path: string | null;
    data?: T;
    loading: boolean;
    error?: Error;
  }>({ path, loading: !!path });
  useEffect(() => {
    const controller = new AbortController();
    if (!path) {
      setState({ path, loading: false });
      return () => controller.abort();
    }
    setState((previous) => ({
      path,
      data: keepPrevious ? previous.data : undefined,
      loading: true,
    }));
    api<T>(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted)
          setState({ path, data, loading: false });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({ path, loading: false, error });
      });
    return () => controller.abort();
  }, [path, revision]);
  return state.path === path || keepPrevious
    ? state
    : { loading: !!path, data: undefined, error: undefined };
}

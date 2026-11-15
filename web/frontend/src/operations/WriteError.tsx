/** Loading data again must never implicitly discard or resubmit a stock form. */
export function WriteError({ error }: { error?: Error }) {
  if (!error) return null;
  return <p className="notice error" role="alert">{error.message}</p>;
}

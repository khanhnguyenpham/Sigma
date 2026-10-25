import { Icon } from "./Icon";

export function Card({
  label,
  value,
  note,
  tone = "",
  icon,
}: {
  label: string;
  value: string;
  note?: string;
  tone?: string;
  icon?: string;
}) {
  return (
    <article className={"stat " + tone}>
      {icon && (
        <div className="stat-icon">
          <Icon name={icon} />
        </div>
      )}
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </article>
  );
}

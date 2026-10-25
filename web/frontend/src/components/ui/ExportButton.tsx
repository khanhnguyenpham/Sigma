import { Icon } from "./Icon";
import { API_PREFIX } from "../../config/http";

export function ExportButton({ url }: { url: string }) {
  return (
    <a className="button secondary" href={API_PREFIX + url} download>
      <Icon name="download" size={16} /> Xuất CSV
    </a>
  );
}

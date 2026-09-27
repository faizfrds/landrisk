import type { ProgressEvent } from "../api/types";

interface Props {
  events: ProgressEvent[];
}

export default function ProgressStream({ events }: Props) {
  if (events.length === 0) return null;

  return (
    <ul className="progress-stream">
      {events.map((event, i) => (
        <li key={i} className={i === events.length - 1 ? "current" : "done"}>
          {event.message}
        </li>
      ))}
    </ul>
  );
}

import { Fragment, type CSSProperties } from "react";

/** A page title that sharpens into focus word by word on load. Screen readers get the plain text once. */
export default function BlurTitle({ text, className }: { text: string; className?: string }) {
  return (
    <h1 className={className ? `blur-title ${className}` : "blur-title"} aria-label={text}>
      {text.split(" ").map((w, i) => (
        <Fragment key={i}>
          <span className="w" aria-hidden="true" style={{ "--i": i } as CSSProperties}>{w}</span>{" "}
        </Fragment>
      ))}
    </h1>
  );
}

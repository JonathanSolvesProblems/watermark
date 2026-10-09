// The signature device (charter 9): what happened above the line, the date below it,
// the way every high-water plaque in .design/refs is laid out.
export default function HighWaterLine({
  above,
  below,
  draw = true,
  className = "",
}: {
  above: React.ReactNode;
  below: React.ReactNode;
  draw?: boolean;
  className?: string;
}) {
  return (
    <div className={className}>
      <div>{above}</div>
      <div className="hwl-rule my-2" data-draw={draw} aria-hidden="true" />
      <div className="text-stencil text-[15px]">{below}</div>
    </div>
  );
}

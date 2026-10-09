// A vertical flood staff, the way it is bolted to a wall: enamel, E-ticks, metre
// numerals, and water (the stain, never a colour) climbing to a stage mark in detented
// steps on first paint, with the red line at its level. Decorative, so hidden from
// assistive technology.
//
// The enamel plate is the outer element itself: `.staff` sets position: relative and
// is declared after Tailwind's utilities, so it cannot also be an absolutely placed child.
export default function StaffColumn({ stage = 0.58, marks = ["3", "2", "1", "0"] }: { stage?: number; marks?: string[] }) {
  return (
    <div className="relative h-full min-h-[320px] w-14" aria-hidden="true">
      <div className="staff h-full overflow-hidden">
        <div className="staff-col-fill absolute inset-x-0 bottom-0" style={{ height: `${stage * 100}%` }} />
        <div className="staff-col-ticks absolute inset-0" />
      </div>
      <div className="staff-level absolute -inset-x-2 h-[3px]" style={{ bottom: `${stage * 100}%` }} />
      <div className="absolute inset-y-0 -left-7 flex flex-col justify-between py-1 font-display font-bold text-[13px] text-stencil">
        {marks.map((m) => (
          <span key={m}>{m}</span>
        ))}
      </div>
    </div>
  );
}

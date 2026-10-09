// One of the brand's illustrations (charter 11), straight on the ground. The alt text says
// what the scene is.
const ALT: Record<string, string> = {
  empty: "A dry basement floor with a water sensor sitting alone on it",
  setup: "A camera on a basement wall angled down at a water sensor on the floor",
  error: "A basement camera with its power cable unplugged",
};

// Intrinsic sizes of web/public/art, so the space is reserved before the image loads.
const SIZE: Record<string, [number, number]> = {
  empty: [340, 405], setup: [339, 725], error: [386, 651]
};

export type PrintName = keyof typeof ALT;

export default function Print({ name, width, className = "", decorative = false }: {
  name: PrintName;
  width: number;
  className?: string;
  decorative?: boolean;
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`/art/${name}.webp`}
      width={width}
      height={Math.round((width * SIZE[name][1]) / SIZE[name][0])}
      alt={decorative ? "" : ALT[name]}
      className={`print ${className}`}
      loading="lazy"
      decoding="async"
    />
  );
}

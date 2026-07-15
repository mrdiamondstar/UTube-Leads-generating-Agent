import { cx } from "@/components/ui";

export function UserAvatar({
  name,
  avatarUrl,
  size = 32,
  className,
}: {
  name: string;
  avatarUrl?: string | null;
  size?: number;
  className?: string;
}) {
  const initial = (name?.trim()?.[0] ?? "?").toUpperCase();
  const style = { width: size, height: size };

  if (avatarUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={avatarUrl}
        alt={name}
        style={style}
        className={cx("rounded-full object-cover ring-2 ring-white", className)}
      />
    );
  }

  return (
    <span
      style={style}
      className={cx(
        "flex items-center justify-center rounded-full bg-slate-900 font-semibold text-white ring-2 ring-white",
        className,
      )}
    >
      <span style={{ fontSize: size * 0.4 }}>{initial}</span>
    </span>
  );
}

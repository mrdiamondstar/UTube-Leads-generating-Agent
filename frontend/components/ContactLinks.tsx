import { GlobeIcon, MailIcon } from "@/components/icons";

const PLATFORM_LABEL: Record<string, string> = {
  instagram: "IG",
  x: "X",
  twitter: "X",
  tiktok: "TT",
  facebook: "FB",
  linkedin: "IN",
  discord: "DC",
  telegram: "TG",
  twitch: "TW",
  patreon: "PT",
};

export function ContactLinks({
  email,
  website,
  socials,
}: {
  email?: string | null;
  website?: string | null;
  socials?: Record<string, string> | null;
}) {
  const socialEntries = Object.entries(socials ?? {});
  const hasAny = email || website || socialEntries.length > 0;

  if (!hasAny) {
    return <span className="text-slate-300">—</span>;
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {email && (
        <a
          href={`mailto:${email}`}
          title={email}
          onClick={(e) => e.stopPropagation()}
          className="text-slate-400 transition hover:text-emerald-600"
        >
          <MailIcon className="h-4 w-4" />
        </a>
      )}
      {website && (
        <a
          href={website}
          target="_blank"
          rel="noreferrer"
          title={website}
          onClick={(e) => e.stopPropagation()}
          className="text-slate-400 transition hover:text-emerald-600"
        >
          <GlobeIcon className="h-4 w-4" />
        </a>
      )}
      {socialEntries.map(([platform, url]) => (
        <a
          key={platform}
          href={url}
          target="_blank"
          rel="noreferrer"
          title={`${platform}: ${url}`}
          onClick={(e) => e.stopPropagation()}
          className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500 transition hover:bg-emerald-50 hover:text-emerald-700"
        >
          {PLATFORM_LABEL[platform] ?? platform.slice(0, 2).toUpperCase()}
        </a>
      ))}
    </div>
  );
}

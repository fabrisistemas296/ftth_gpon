export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" stroke="#7CC4E8" strokeWidth={2.2} strokeLinecap="round" aria-hidden="true">
      <circle cx="8" cy="18" r="4" />
      <path d="M12 18h8" />
      <path d="M20 18l8-9M20 18h8M20 18l8 9" />
      <circle cx="30" cy="9" r="2" />
      <circle cx="30" cy="18" r="2" />
      <circle cx="30" cy="27" r="2" />
    </svg>
  );
}

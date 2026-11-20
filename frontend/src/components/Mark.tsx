/** Contour-line mark: three nested soundings, drawn for this product (not a company logo). */
export default function Mark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" className="mark">
      <path d="M3 22c4-6 9-9 13-9s9 3 13 9" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M7 24c3-4 6-6 9-6s6 2 9 6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity=".7" />
      <path d="M11 26c2-2 3.5-3 5-3s3 1 5 3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity=".45" />
      <circle cx="16" cy="7" r="2.4" fill="var(--buoy)" />
      <path d="M16 9.5v3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

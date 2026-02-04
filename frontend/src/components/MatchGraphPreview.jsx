export default function MatchGraphPreview() {
  return (
    <div className="graph-preview">
      <svg width="100%" height="64" viewBox="0 0 320 64" fill="none">
        <g transform="translate(160 32) scale(1.3) translate(-160 -32)">
          {/* Cluster 1 - left */}
          <line x1="32" y1="32" x2="56" y2="20" stroke="#e8a090" strokeWidth="1.5" opacity="0.75" />
          <line x1="32" y1="32" x2="52" y2="44" stroke="#e8a090" strokeWidth="1.5" opacity="0.75" />
          <line x1="56" y1="20" x2="52" y2="44" stroke="#e8a090" strokeWidth="1.5" opacity="0.65" />
          <circle cx="32" cy="32" r="4" fill="#a99d94" />
          <circle cx="56" cy="20" r="4" fill="#a99d94" />
          <circle cx="52" cy="44" r="4" fill="#a99d94" />

          {/* Cluster 2 - center */}
          <line x1="140" y1="28" x2="164" y2="36" stroke="#e8a090" strokeWidth="1.5" opacity="0.75" />
          <line x1="164" y1="36" x2="180" y2="24" stroke="#e8a090" strokeWidth="1.5" opacity="0.75" />
          <line x1="140" y1="28" x2="156" y2="48" stroke="#e8a090" strokeWidth="1.5" opacity="0.65" />
          <line x1="156" y1="48" x2="164" y2="36" stroke="#e8a090" strokeWidth="1.5" opacity="0.65" />
          <circle cx="140" cy="28" r="4" fill="#a99d94" />
          <circle cx="164" cy="36" r="4" fill="#a99d94" />
          <circle cx="180" cy="24" r="4" fill="#a99d94" />
          <circle cx="156" cy="48" r="4" fill="#a99d94" />

          {/* Cluster 3 - right */}
          <line x1="268" y1="36" x2="288" y2="28" stroke="#e8a090" strokeWidth="1.5" opacity="0.75" />
          <circle cx="268" cy="36" r="4" fill="#a99d94" />
          <circle cx="288" cy="28" r="4" fill="#a99d94" />
        </g>
      </svg>
    </div>
  );
}

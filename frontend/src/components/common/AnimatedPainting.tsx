import React, { useMemo } from 'react';
import { createNoise3D } from 'simplex-noise';

/**
 * AnimatedPainting renders an animated SVG painting effect using organic, noise-based mask shapes.
 * The image is revealed through animated organic blobs. Reusable anywhere in the app.
 *
 * @param logo - The image URL to use as the painting base (e.g., a logo or artwork)
 * @param animationDuration - Total duration (in seconds) for the full painting animation
 */
interface AnimatedPaintingProps {
  logo: string;
  animationDuration?: number; // in seconds
}

export const AnimatedPainting: React.FC<AnimatedPaintingProps> = ({ logo, animationDuration = 7 }) => {
  // Grid settings
  const gridCols = 20;
  const gridRows = 20;
  const width = 180;
  const height = 180;
  const cellW = width / gridCols;
  const cellH = height / gridRows;
  const noise3D = useMemo(() => createNoise3D(() => 0.5), []);

  // Animation timing
  const totalPieces = gridCols * gridRows;
  const fadeIn = 0.8; // seconds for each piece to fade in
  const maxDelay = Math.max(animationDuration - fadeIn, 0.01); // avoid negative or zero

  // Generate organic blob path for each cell
  function generateBlobPath(cx: number, cy: number, r: number, seed: number) {
    const points = 12;
    let d = '';
    for (let i = 0; i < points; i++) {
      const angle = (Math.PI * 2 * i) / points;
      // Use simplex noise to perturb the radius
      const noise = noise3D(
        Math.cos(angle) + cx / width,
        Math.sin(angle) + cy / height,
        seed
      );
      const localR = r * (0.85 + 0.25 * noise);
      const x = cx + Math.cos(angle) * localR;
      const y = cy + Math.sin(angle) * localR;
      d += i === 0 ? `M${x},${y}` : `L${x},${y}`;
    }
    d += 'Z';
    return d;
  }

  // Generate all mask pieces
  const maskPieces = useMemo(() => {
    let piecesData = [];
    let idx = 0;
    for (let row = 0; row < gridRows; row++) {
      for (let col = 0; col < gridCols; col++) {
        // Center of the cell, with jitter
        const cx = col * cellW + cellW / 2 + (Math.random() - 0.5) * cellW * 0.3;
        const cy = row * cellH + cellH / 2 + (Math.random() - 0.5) * cellH * 0.3;
        // Radius covers the cell, with overlap
        const r = Math.max(cellW, cellH) * (0.7 + Math.random() * 0.5);
        // Each piece gets a unique seed for noise
        const seed = idx * 0.13;
        const path = generateBlobPath(cx, cy, r, seed);
        piecesData.push({ idx, path });
        idx++;
      }
    }
    // Shuffle the fill order (Fisher-Yates)
    for (let i = piecesData.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [piecesData[i], piecesData[j]] = [piecesData[j], piecesData[i]];
    }
    // Assign delays based on shuffled order
    return piecesData.map((piece, orderIdx) => {
      const delay = (orderIdx / (totalPieces - 1)) * maxDelay;
      return (
        <path
          key={piece.idx}
          d={piece.path}
          fill="white"
          style={{
            opacity: 0,
            animation: `fade-in-stroke ${fadeIn}s ease forwards`,
            animationDelay: `${delay}s`,
          }}
        />
      );
    });
  }, [gridCols, gridRows, cellW, cellH, noise3D, maxDelay, totalPieces, fadeIn]);

  return (
    <svg
      className="h-[180px] w-[180px]"
      viewBox="0 0 180 180"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ display: 'block' }}
    >
      <defs>
        <mask id="noiseMask">
          {maskPieces}
        </mask>
        <style>{`
          @keyframes fade-in-stroke {
            to { opacity: 1; }
          }
        `}</style>
      </defs>
      <image
        href={logo}
        x="0"
        y="0"
        height="180"
        width="180"
        mask="url(#noiseMask)"
        style={{ opacity: 0.85 }}
      />
    </svg>
  );
}; 
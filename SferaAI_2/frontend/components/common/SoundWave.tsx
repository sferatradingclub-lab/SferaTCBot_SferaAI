import React, { useCallback, useEffect, useRef } from 'react';

interface SoundWaveProps {
  bars?: number[];
  isActive: boolean;
}

export const SoundWave: React.FC<SoundWaveProps> = ({ bars = [], isActive }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameIdRef = useRef<number | null>(null);
  const phaseRef = useRef(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Match drawing buffer to display size
    if (canvas.width !== canvas.clientWidth || canvas.height !== canvas.clientHeight) {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    }

    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    if (!isActive) {
      return;
    }

    // Calculate average volume from bars to drive amplitude
    const volume = bars && bars.length > 0
      ? bars.reduce((acc, val) => acc + val, 0) / bars.length
      : 0;

    // Don't render waves if there's no meaningful audio activity
    if (volume < 0.01) {
      return;
    }

    // Base amplitude scaling
    const baseAmplitude = Math.min(height / 2, volume * height * 2);

    // Update phase for animation
    phaseRef.current += 0.15;

    // Configuration for multiple waves - Intermediate thickness
    const waves = [
      { color: 'rgba(0, 255, 255, 0.3)', speed: 1.0, amplitude: 1.0, frequency: 1.0, width: 2 },
      { color: 'rgba(0, 255, 255, 0.5)', speed: 1.5, amplitude: 0.8, frequency: 1.5, width: 3 },
      { color: 'rgba(0, 255, 255, 1.0)', speed: 2.0, amplitude: 0.6, frequency: 2.0, width: 4 }, // Main wave
      { color: 'rgba(255, 255, 255, 0.6)', speed: 2.5, amplitude: 0.4, frequency: 2.5, width: 2 }, // Highlight
    ];

    const centerY = height / 2;

    // Global glow - Balanced intensity
    ctx.shadowBlur = 20;
    ctx.shadowColor = 'rgba(0, 255, 255, 0.7)';

    waves.forEach((wave) => {
      ctx.beginPath();
      ctx.strokeStyle = wave.color;
      ctx.lineWidth = wave.width; // Use individual width for each wave
      ctx.lineCap = 'round'; // Smooth ends
      ctx.lineJoin = 'round';

      for (let x = 0; x < width; x++) {
        // Normalized X from -1 to 1
        const normX = (x / width) * 2 - 1;

        // Window function (Hanning-like) to taper ends to 0
        const window = 0.5 * (1 + Math.cos(Math.PI * normX));

        // Wave calculation
        const y = centerY +
          Math.sin(x * 0.01 * wave.frequency + phaseRef.current * wave.speed) *
          baseAmplitude * wave.amplitude * window;

        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
    });

    // Reset shadow for next frame/other draws
    ctx.shadowBlur = 0;

  }, [isActive, bars]);

  useEffect(() => {
    const animate = () => {
      draw();
      animationFrameIdRef.current = requestAnimationFrame(animate);
    };

    if (isActive) {
      animationFrameIdRef.current = requestAnimationFrame(animate);
    } else {
      draw(); // Clear or draw idle state
    }

    return () => {
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
    };
  }, [isActive, draw]);

  useEffect(() => {
    const handleResize = () => draw();
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, [draw]);

  return (
    <div
      className={`mx-auto h-[150px] w-full max-w-xl px-4 transition-opacity duration-500 md:h-[300px] ${isActive ? 'opacity-100' : 'opacity-0'
        }`}
    >
      <canvas ref={canvasRef} className="h-full w-full" />
    </div>
  );
};

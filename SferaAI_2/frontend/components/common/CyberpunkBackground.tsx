import React, { useEffect, useRef } from 'react';

// A lightweight and performant "pulsing hexagonal grid" animation.
export const CyberpunkBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;

    const HEX_RADIUS = 25;
    const HEX_COLOR = 'rgba(0, 255, 255, 0.16)';
    const PULSE_COLOR = 'rgba(173, 254, 255, 1)';

    let hexGrid: { x: number; y: number; col: number; row: number }[] = [];
    let pulses: Pulse[] = [];

    class Pulse {
      x: number;
      y: number;
      radius: number;
      speed: number;
      maxRadius: number;
      constructor(x: number, y: number) {
        this.x = x;
        this.y = y;
        this.radius = 0;
        this.speed = Math.random() * 2 + 1;
        this.maxRadius = canvas ? Math.max(canvas.width, canvas.height) * 0.6 : 500;
      }

      update() {
        this.radius += this.speed;
      }

      isFinished() {
        return this.radius > this.maxRadius;
      }
    }

    const drawHexagon = (x: number, y: number, color: string, lineWidth: number) => {
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const angle = (Math.PI / 3) * i;
        const pointX = x + HEX_RADIUS * Math.cos(angle);
        const pointY = y + HEX_RADIUS * Math.sin(angle);
        if (i === 0) {
          ctx.moveTo(pointX, pointY);
        } else {
          ctx.lineTo(pointX, pointY);
        }
      }
      ctx.closePath();
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    };

    const initialize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;

      hexGrid = [];
      pulses = [new Pulse(canvas.width / 2, canvas.height / 2)];

      const hexHeight = HEX_RADIUS * Math.sqrt(3);
      const hexWidth = HEX_RADIUS * 2;

      const rows = Math.ceil(canvas.height / hexHeight) + 2;
      const cols = Math.ceil(canvas.width / (hexWidth * 0.75)) + 2;

      for (let row = -1; row < rows; row++) {
        for (let col = -1; col < cols; col++) {
          const xOffset = col * hexWidth * 0.75;
          const yOffset = row * hexHeight + (col % 2 === 0 ? 0 : hexHeight / 2);
          hexGrid.push({ x: xOffset, y: yOffset, col, row });
        }
      }
    };

    window.addEventListener('resize', initialize);
    initialize();

    const draw = () => {
      // Fading background
      ctx.fillStyle = 'rgba(10, 25, 47, 0.1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Add new pulses randomly
      if (Math.random() < 0.01 && pulses.length < 5) {
        pulses.push(new Pulse(Math.random() * canvas.width, Math.random() * canvas.height));
      }

      // Update pulses
      pulses.forEach((p) => p.update());
      pulses = pulses.filter((p) => !p.isFinished());

      // Draw hexagons
      hexGrid.forEach((hex) => {
        let maxIntensity = 0;
        pulses.forEach((pulse) => {
          const dx = hex.x - pulse.x;
          const dy = hex.y - pulse.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          const pulseWidth = 100;
          const intensity = Math.max(0, 1 - Math.abs(dist - pulse.radius) / pulseWidth);

          if (intensity > maxIntensity) {
            maxIntensity = intensity;
          }
        });

        if (maxIntensity > 0) {
          const color = `rgba(173, 254, 255, ${Math.min(maxIntensity * 0.64, 0.64)})`;
          drawHexagon(hex.x, hex.y, color, 1 + maxIntensity * 1.5);
        } else {
          drawHexagon(hex.x, hex.y, HEX_COLOR, 0.5);
        }
      });

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', initialize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 z-0 h-full w-full" />;
};

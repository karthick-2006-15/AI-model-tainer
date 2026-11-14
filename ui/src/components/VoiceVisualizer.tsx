import React, { useEffect, useRef } from 'react';

interface Props {
  isActive: boolean;
  color?: string;
  height?: number;
}

export const VoiceVisualizer: React.FC<Props> = ({ 
  isActive, 
  color = '#06b6d4',
  height = 40 
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const h = canvas.height;
      const centerY = h / 2;

      ctx.beginPath();
      ctx.lineWidth = 2;
      ctx.strokeStyle = color;
      ctx.shadowBlur = 8;
      ctx.shadowColor = color;

      const numPoints = 64;
      const amplitude = isActive ? h * 0.35 : 2;

      for (let i = 0; i <= numPoints; i++) {
        const x = (i / numPoints) * width;
        const normalizedX = (i / numPoints) * 2 - 1;
        // Envelope: dampen wave at borders
        const envelope = 1 - Math.pow(normalizedX, 2);
        const y = centerY + Math.sin(phase + i * 0.3) * amplitude * envelope;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();

      phase += isActive ? 0.12 : 0.03;
      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isActive, color]);

  return (
    <div className="w-full flex items-center justify-center">
      <canvas 
        ref={canvasRef} 
        width={320} 
        height={height} 
        className="w-full max-w-xs h-10"
      />
    </div>
  );
};

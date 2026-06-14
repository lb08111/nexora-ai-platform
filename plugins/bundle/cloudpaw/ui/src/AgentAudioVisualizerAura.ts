type AgentState =
  | "connecting"
  | "initializing"
  | "listening"
  | "thinking"
  | "speaking"
  | "idle"
  | "disconnected"
  | "failed";

type AuraSize = "icon" | "sm" | "md" | "lg" | "xl";

type AuraProps = {
  size?: AuraSize;
  state?: AgentState;
  color?: `#${string}`;
  colorShift?: number;
  className?: string;
  style?: Record<string, string | number | undefined>;
};

type HostReact = {
  createElement: (...args: any[]) => any;
  useEffect: (effect: () => void | (() => void), deps?: any[]) => void;
  useRef: <T>(initialValue: T) => { current: T };
};

const SIZE_PX: Record<AuraSize, number> = {
  icon: 28,
  sm: 64,
  md: 112,
  lg: 192,
  xl: 320,
};

const STATE_PROFILE: Record<
  AgentState,
  { speed: number; amplitude: number; rings: number; alpha: number }
> = {
  connecting: { speed: 0.92, amplitude: 0.34, rings: 3, alpha: 0.7 },
  initializing: { speed: 0.82, amplitude: 0.3, rings: 3, alpha: 0.65 },
  listening: { speed: 0.48, amplitude: 0.18, rings: 2, alpha: 0.56 },
  thinking: { speed: 0.74, amplitude: 0.24, rings: 3, alpha: 0.62 },
  speaking: { speed: 1.18, amplitude: 0.42, rings: 4, alpha: 0.78 },
  idle: { speed: 0.28, amplitude: 0.1, rings: 2, alpha: 0.44 },
  disconnected: { speed: 0.2, amplitude: 0.08, rings: 1, alpha: 0.32 },
  failed: { speed: 0.24, amplitude: 0.08, rings: 1, alpha: 0.32 },
};

function hexToRgb(color: `#${string}`): [number, number, number] {
  const match = color.match(/^#([0-9a-fA-F]{6})$/);
  if (!match) return [75, 143, 206];
  const value = match[1];
  return [
    Number.parseInt(value.slice(0, 2), 16),
    Number.parseInt(value.slice(2, 4), 16),
    Number.parseInt(value.slice(4, 6), 16),
  ];
}

function channel(value: number, shift: number) {
  return Math.max(0, Math.min(255, Math.round(value + shift)));
}

export function createAgentAudioVisualizerAura(React: HostReact) {
  const { useEffect, useRef } = React;

  function AgentAudioVisualizerAura({
    size = "sm",
    state = "thinking",
    color = "#4b8fce",
    colorShift = 0.28,
    className,
    style,
  }: AuraProps) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const frameRef = useRef<number | null>(null);
    const sizePx = SIZE_PX[size] ?? SIZE_PX.sm;

    useEffect(() => {
      const canvas = canvasRef.current;
      const context = canvas?.getContext("2d");
      if (!canvas || !context) return;

      const profile = STATE_PROFILE[state] ?? STATE_PROFILE.thinking;
      const [r, g, b] = hexToRgb(color);
      let start = performance.now();

      const draw = (now: number) => {
        const dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
        const rect = canvas.getBoundingClientRect();
        const width = Math.max(1, Math.floor(rect.width * dpr));
        const height = Math.max(1, Math.floor(rect.height * dpr));

        if (canvas.width !== width || canvas.height !== height) {
          canvas.width = width;
          canvas.height = height;
        }

        const elapsed = (now - start) / 1000;
        const cx = width / 2;
        const cy = height / 2;
        const radius = Math.min(width, height) * 0.28;

        context.clearRect(0, 0, width, height);
        context.globalCompositeOperation = "lighter";

        const core = context.createRadialGradient(cx, cy, 0, cx, cy, radius * 2.2);
        core.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${0.22 * profile.alpha})`);
        core.addColorStop(0.52, `rgba(${r}, ${g}, ${b}, ${0.1 * profile.alpha})`);
        core.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
        context.fillStyle = core;
        context.beginPath();
        context.arc(cx, cy, radius * 2.1, 0, Math.PI * 2);
        context.fill();

        for (let ring = 0; ring < profile.rings; ring += 1) {
          const ringTime = elapsed * profile.speed + ring * 0.72;
          const hueShift = Math.sin(ringTime * 1.4) * colorShift * 42;
          const rr = channel(r, hueShift);
          const gg = channel(g, -hueShift * 0.35);
          const bb = channel(b, hueShift * 0.2);
          const wobble = Math.sin(ringTime * 2.2) * profile.amplitude;
          const scaleX = 1 + wobble * 0.6;
          const scaleY = 0.72 + Math.cos(ringTime * 1.6) * profile.amplitude * 0.28;
          const alpha = (0.22 - ring * 0.035) * profile.alpha;

          context.save();
          context.translate(cx, cy);
          context.rotate(ringTime * 0.55);
          context.scale(scaleX, scaleY);
          context.strokeStyle = `rgba(${rr}, ${gg}, ${bb}, ${alpha})`;
          context.lineWidth = Math.max(1, sizePx * 0.035 - ring * 0.25) * dpr;
          context.shadowColor = `rgba(${rr}, ${gg}, ${bb}, ${0.45 * profile.alpha})`;
          context.shadowBlur = sizePx * 0.24 * dpr;
          context.beginPath();

          const points = 96;
          for (let i = 0; i <= points; i += 1) {
            const angle = (i / points) * Math.PI * 2;
            const pulse =
              Math.sin(angle * 3 + ringTime * 2.4) * radius * profile.amplitude * 0.16 +
              Math.cos(angle * 5 - ringTime) * radius * profile.amplitude * 0.08;
            const currentRadius = radius + ring * radius * 0.18 + pulse;
            const x = Math.cos(angle) * currentRadius;
            const y = Math.sin(angle) * currentRadius;
            if (i === 0) context.moveTo(x, y);
            else context.lineTo(x, y);
          }

          context.closePath();
          context.stroke();
          context.restore();
        }

        context.globalCompositeOperation = "source-over";
        const dot = context.createRadialGradient(cx, cy, 0, cx, cy, radius * 0.34);
        dot.addColorStop(0, `rgba(248, 251, 255, ${0.38 * profile.alpha})`);
        dot.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
        context.fillStyle = dot;
        context.beginPath();
        context.arc(cx, cy, radius * 0.38, 0, Math.PI * 2);
        context.fill();

        frameRef.current = requestAnimationFrame(draw);
      };

      frameRef.current = requestAnimationFrame((now) => {
        start = now;
        draw(now);
      });

      return () => {
        if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      };
    }, [color, colorShift, sizePx, state]);

    return React.createElement("canvas", {
      ref: canvasRef,
      className,
      "aria-hidden": true,
      style: {
        width: sizePx,
        height: sizePx,
        display: "block",
        ...style,
      },
    });
  }

  return AgentAudioVisualizerAura;
}

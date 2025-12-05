import React from 'react';

interface AgentAvatarProps {
  isSpeaking: boolean;
}

export const AgentAvatar: React.FC<AgentAvatarProps> = ({ isSpeaking }) => {
  const styles = `
        @keyframes pulse-outer {
          0% { r: 18; opacity: 0.4; }
          50% { r: 22; opacity: 0.2; }
          100% { r: 18; opacity: 0.4; }
        }
        @keyframes pulse-inner {
          0% { r: 8; opacity: 0.9; }
          50% { r: 7; opacity: 0.7; }
          100% { r: 8; opacity: 0.9; }
        }
        .pulse-outer-circle {
          animation: pulse-outer 4s ease-in-out infinite;
        }
        .pulse-inner-circle {
          animation: pulse-inner 2.5s ease-in-out infinite;
        }
    `;

  return (
    <div className="h-10 w-10 flex-shrink-0">
      <style>{styles}</style>
      <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient
            id="glow-gradient"
            cx="0"
            cy="0"
            r="1"
            gradientUnits="userSpaceOnUse"
            gradientTransform="translate(24 24) rotate(90) scale(24)"
          >
            <stop stopColor="#00FFFF" stopOpacity={isSpeaking ? '0.3' : '0.15'} />
            <stop offset="1" stopColor="#0A192F" stopOpacity="0" />
          </radialGradient>
        </defs>
        {/* Outer glow */}
        <circle cx="24" cy="24" r="24" fill="url(#glow-gradient)" />
        {/* Animated Circles */}
        <circle
          className="pulse-outer-circle"
          cx="24"
          cy="24"
          r="18"
          stroke="#00FFFF"
          strokeWidth="1.5"
          strokeOpacity="0.4"
        />
        <circle cx="24" cy="24" r="12" stroke="#00FFFF" strokeWidth="1" strokeOpacity="0.8" />
        <circle className="pulse-inner-circle" cx="24" cy="24" r="8" fill="#00FFFF" />
      </svg>
    </div>
  );
};

import React from 'react';

export const MicrophoneIcon = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
  >
    <path d="M12 14q.825 0 1.413-.587T14 12V6q0-.825-.587-1.413T12 4q-.825 0-1.413.587T10 6v6q0 .825.587 1.413T12 14Zm-1 7v-3.075q-2.6-.35-4.3-2.325T5 11H7q0 2.075 1.463 3.538T12 16q2.075 0 3.538-1.463T17 11h2q0 2.525-1.7 4.5T13 17.925V21h-2Z" />
  </svg>
);

export const MicrophoneOffIcon = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
  >
    <path d="M12 14q.825 0 1.413-.588T14 12v-1.15l-2-2V12q0 .825.588 1.412T12 14Zm-1-1.175L9.4 11.225q-.15-.325-.225-.688T9 10v2q0 .275.025.538t.075.512Zm-2-2.35V11h2q0-.8.2-1.525t.55-1.375L9 6.5V6q0-.825.588-1.413T11 4h.15l-2 2H9Zm6.15 6.175L12 15q-.275 0-.537-.025t-.513-.075L9.4 13.35q.725.4 1.525.6t1.625.2q2.075 0 3.538-1.463T17 11h-1.15l-1.7 1.7ZM3.25 2.8 2 4.05l4.7 4.7V11H8q.05 2.15 1.488 3.688T13 16.925V19h-2v2h6v-2h-2v-2.075q.6-.1 1.163-.337T17.3 15.6l1.65 1.65L20.2 16l-17-17Z" />
  </svg>
);

export const PowerIcon = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
  >
    <path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42A6.92 6.92 0 0 1 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z" />
  </svg>
);

export const CameraIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
  >
    <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM15 16H5V8h10v8z" />
  </svg>
);

export const CameraOffIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
  >
    <path d="M21 6.5l-4 4V7c0-.55-.45-1-1-1H9.82L21 17.18V6.5zM3.27 2L2 3.27 4.73 6H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.21 0 .39-.08.55-.18L19.73 21 21 19.73 3.27 2z" />
  </svg>
);

export const ScreenShareIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
  >
    <path d="M20 18c1.1 0 1.99-.9 1.99-2L22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 16V6h16v10H4z" />
  </svg>
);

export const ScreenShareOffIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
  >
    <path d="M2.81 2.81L1.39 4.22 4 6.83V16c0 1.1.9 2 2 2h10c.82 0 1.52-.5 1.83-1.17L19.78 21l1.41-1.41L2.81 2.81zM6 16V8.83l8 8H6zm16-10H8.83l2 2H20v8.17l2 2V6c0-1.1-.9-2-2-2z" />
  </svg>
);

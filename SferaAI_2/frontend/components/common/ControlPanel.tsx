import React from 'react';
import { cn } from '@/lib/utils';
import {
  CameraIcon,
  CameraOffIcon,
  PowerIcon,
  ScreenShareIcon,
  ScreenShareOffIcon,
} from './IconComponents';
import { Microphone, MicrophoneSlash } from '@phosphor-icons/react/dist/ssr';

interface ControlPanelProps {
  isSessionActive: boolean;
  isConnecting: boolean;
  isMuted: boolean;
  isCameraOn: boolean;
  isScreenShareOn: boolean;
  onStart: () => void;
  onStop: () => void;
  onToggleMute: () => void;
  onToggleCamera: () => void;
  onToggleScreenShare: () => void;
}

const ControlButton: React.FC<{
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
  children: React.ReactNode;
  'aria-label': string;
  isActive?: boolean;
}> = ({ onClick, disabled, className, children, 'aria-label': ariaLabel, isActive }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    aria-label={ariaLabel}
    className={`flex h-6 w-6 sm:h-10 sm:w-10 md:h-12 md:w-12 items-center justify-center rounded-full border border-white/10 text-white/90 backdrop-blur-sm transition-all duration-300 ease-in-out hover:bg-white/20 hover:text-white hover:shadow-[0_0_15px_rgba(255,255,255,0.3)] focus:ring-2 focus:ring-white/50 focus:ring-offset-2 focus:ring-offset-transparent focus:outline-none disabled:cursor-not-allowed disabled:opacity-40 ${isActive ? 'bg-blue-500/30 text-white shadow-[0_0_15px_rgba(0,128,255,0.5)]' : ''
      } ${className} `}
  >
    {children}
  </button>
);
const MemoizedControlButton = React.memo(ControlButton);

export const ControlPanel: React.FC<ControlPanelProps> = ({
  isSessionActive,
  isConnecting,
  onStart,
  onStop,
  isMuted,
  onToggleMute,
  isCameraOn,
  isScreenShareOn,
  onToggleCamera,
  onToggleScreenShare,
}) => {
  const handleMainButtonClick = () => {
    if (isSessionActive) {
      onStop();
    } else {
      onStart();
    }
  };

  return (
    <div className="relative z-10 transition-all duration-300 ease-in-out">
      <div
        className="flex items-center justify-center space-x-3 rounded-full px-5 py-3 shadow-[20px_20px_50px_rgba(0,0,0,0.5)] transition-all duration-500 ease-out hover:shadow-[0_0_15px_rgba(0,201,255,0.7),0_0_30px_rgba(0,201,255,0.5),inset_0_0_10px_rgba(0,201,255,0.3)] md:space-x-6 md:px-8 md:py-4"
        style={{
          background: 'rgba(255, 255, 255, 0.02)',
          backdropFilter: 'blur(10px)',
          WebkitBackdropFilter: 'blur(10px)',
          borderTop: '1px solid rgba(255, 255, 255, 0.5)',
          borderLeft: '1px solid rgba(255, 255, 255, 0.5)',
        }}
      >
        <MemoizedControlButton
          onClick={onToggleMute}
          disabled={isConnecting || !isSessionActive}
          aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}
          className={isMuted ? 'bg-red-600/80 hover:bg-red-500/80 shadow-[0_0_15px_rgba(255,0,0,0.4)]' : ''}
        >
          {isMuted ? (
            <MicrophoneSlash weight="fill" className="h-4 w-4 sm:h-6 sm:w-6 md:h-7 md:w-7" />
          ) : (
            <Microphone weight="fill" className="h-4 w-4 sm:h-6 sm:w-6 md:h-7 md:w-7" />
          )}
        </MemoizedControlButton>

        <MemoizedControlButton
          onClick={onToggleCamera}
          disabled={isConnecting}
          aria-label={isCameraOn ? 'Turn off camera' : 'Turn on camera'}
          isActive={isCameraOn}
        >
          {isCameraOn ? (
            <CameraOffIcon className="h-4 w-4 sm:h-6 sm:w-6 md:h-7 md:w-7" />
          ) : (
            <CameraIcon className="h-4 w-4 sm:h-6 sm:w-6 md:h-7 md:w-7" />
          )}
        </MemoizedControlButton>

        <button
          onClick={handleMainButtonClick}
          disabled={isConnecting}
          aria-label={isSessionActive ? 'End session' : 'Start session'}
          className={`flex h-10 w-10 sm:h-14 sm:w-14 md:h-16 md:w-16 transform items-center justify-center rounded-full border border-white/10 text-white shadow-xl backdrop-blur-sm transition-all duration-300 hover:scale-110 focus:ring-4 focus:ring-offset-2 focus:ring-offset-transparent focus:outline-none disabled:scale-100 disabled:cursor-not-allowed disabled:opacity-50 ${isConnecting ? 'animate-pulse' : ''} ${isSessionActive
            ? 'bg-red-600/40 hover:bg-red-500/50 focus:ring-red-500/50 shadow-[0_0_20px_rgba(255,0,0,0.4)] animate-[pulse_2s_ease-in-out_infinite]'
            : 'bg-green-600/40 hover:bg-green-500/50 focus:ring-green-500/50 shadow-[0_0_20px_rgba(0,255,0,0.3)]'
            } `}
        >
          <PowerIcon className="h-5 w-5 sm:h-7 sm:w-7 md:h-8 md:w-8" />
        </button>

        <MemoizedControlButton
          onClick={onToggleScreenShare}
          disabled={isConnecting}
          aria-label={isScreenShareOn ? 'Stop sharing screen' : 'Share screen'}
          isActive={isScreenShareOn}
        >
          {isScreenShareOn ? (
            <ScreenShareOffIcon className="h-4 w-4 sm:h-6 sm:w-6 md:h-7 md:w-7" />
          ) : (
            <ScreenShareIcon className="h-4 w-4 sm:h-6 sm:w-6 md:h-7 md:w-7" />
          )}
        </MemoizedControlButton>
      </div>
    </div>
  );
};

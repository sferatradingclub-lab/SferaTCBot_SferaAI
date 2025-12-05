// Force refresh
'use client';

import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import { type ReceivedChatMessage, useRoomContext, useVoiceAssistant, VideoTrack } from '@livekit/components-react';
import { Track } from 'livekit-client';
import { AnimatePresence, motion } from 'motion/react';
import type { AppConfig } from '@/app-config';
import { PreConnectMessage } from '@/components/app/preconnect-message';
import { isImageMessage, isLinkMessage, isYouTubeMessage, useChatMessages } from '@/hooks/useChatMessages';
import { useConnectionTimeout } from '@/hooks/useConnectionTimout';
import { useDebugMode } from '@/hooks/useDebug';
import { cn } from '@/lib/utils';
import type { TranscriptMessage } from '../common/types';
import { useInputControls } from '../livekit/agent-control-bar/hooks/use-input-controls';
import { useSession } from './session-provider';
import { useLocalTrackRef } from './tile-layout';

// Dynamically import heavy components
const CyberpunkBackground = dynamic(
  () => import('../common/CyberpunkBackground').then((mod) => mod.CyberpunkBackground),
  { ssr: false }
);
const SphereVisualizer = dynamic(() => import('../common/SphereVisualizer').then((mod) => mod.SphereVisualizer), {
  ssr: false,
});
const ChatPanel = dynamic(() => import('../common/ChatPanel').then((mod) => mod.ChatPanel), {
  ssr: false,
});
const ControlPanel = dynamic(
  () => import('../common/ControlPanel').then((mod) => mod.ControlPanel),
  { ssr: false }
);
const TileLayout = dynamic(() => import('./tile-layout').then((mod) => mod.TileLayout), {
  ssr: false,
});

interface SessionViewProps {
  appConfig: AppConfig;
}

export const SessionView = ({
  appConfig,
  ...props
}: React.ComponentProps<'section'> & SessionViewProps) => {
  useConnectionTimeout(200_000);
  useDebugMode({ enabled: process.env.NODE_ENV !== 'production' });

  const messages = useChatMessages();
  const [chatOpen, setChatOpen] = React.useState(true);
  const { state: agentState } = useVoiceAssistant();
  const isAgentSpeaking = agentState === 'speaking';
  const { startSession, endSession, isSessionActive } = useSession();

  const { microphoneToggle, cameraToggle, screenShareToggle } = useInputControls({
    saveUserChoices: true,
  });

  const cameraTrack = useLocalTrackRef(Track.Source.Camera);
  const isCameraEnabled = cameraTrack && !cameraTrack.publication.isMuted;

  const transcripts = useMemo<TranscriptMessage[]>(() => {
    return messages.map((msg, index) => {
      if (isImageMessage(msg)) {
        return {
          id: msg.id || `msg-${index}`,
          speaker: msg.from?.isLocal ? 'user' : 'agent',
          text: '',
          imageUrl: msg.url,
        };
      }

      if (isLinkMessage(msg)) {
        return {
          id: msg.id || `msg-${index}`,
          speaker: msg.from?.isLocal ? 'user' : 'agent',
          text: msg.url,
          linkUrl: msg.url,
        };
      }

      if (isYouTubeMessage(msg)) {
        return {
          id: msg.id || `msg-${index}`,
          speaker: msg.from?.isLocal ? 'user' : 'agent',
          text: '',
          youtubeVideo: msg.youtubeVideo,
        };
      }

      return {
        id: msg.id || `msg-${index}`,
        speaker: msg.from?.isLocal ? 'user' : 'agent',
        text: msg.message,
      };
    });
  }, [messages]);

  const isConversationActive = isAgentSpeaking || transcripts.length > 0;



  const handleStop = useCallback(() => {
    endSession();
  }, [endSession]);

  const handleToggleMute = useCallback(() => {
    microphoneToggle.toggle();
  }, [microphoneToggle]);

  const handleToggleCamera = useCallback(() => {
    cameraToggle.toggle();
  }, [cameraToggle]);

  const handleToggleScreenShare = useCallback(() => {
    screenShareToggle.toggle();
  }, [screenShareToggle]);

  const preConnectMessages = useMemo(() => {
    return messages.filter((msg) => !isImageMessage(msg)) as ReceivedChatMessage[];
  }, [messages]);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-gray-900">
      {/* Cyberpunk font and animations */}
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
        .blend-screen {
          mix-blend-mode: screen;
        }
        .cyberpunk-title {
          font-family: 'Orbitron', sans-serif;
          color: rgba(200, 255, 255, 0.3); /* Dim but visible */
          text-align: center;
          font-size: 2.5rem; /* Base size for mobile */
          font-weight: 700;
          letter-spacing: 0.15em;
          margin-bottom: 1rem; /* Reduced spacing between title and visualizer */
          position: relative;
          text-shadow: none; /* No glow by default */
          transition: all 0.5s ease-in-out;
          white-space: nowrap; /* Keep text in one line */
        }
        .cyberpunk-title.active {
          color: rgba(200, 255, 255, 0.9);
          text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
        }
        @media (min-width: 768px) {
          .cyberpunk-title {
            font-size: 4.5rem;
            margin-bottom: 1.4rem; /* Reduced spacing between title and visualizer */
          }
        }
        .pulsate {
          animation: pulsate 3s ease-in-out infinite;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(10, 25, 47, 0.5);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(0, 255, 255, 0.3);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(0, 255, 255, 0.6);
        }
        @keyframes pulsate {
          0% {
            transform: scale(1);
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
          }
          50% {
            transform: scale(1.02);
            text-shadow: 0 0 25px rgba(0, 255, 255, 0.8), 0 0 50px rgba(0, 255, 255, 0.4);
          }
          100% {
            transform: scale(1);
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
          }
        }
      `}</style>

      <div className="absolute inset-0 z-0">
        <CyberpunkBackground />
      </div>

      {/* Title Container */}
      <div
        className={cn(
          'pointer-events-none absolute top-[20%] sm:top-[28%] md:top-[30%] left-1/2 -translate-x-1/2 transform z-10 flex flex-col items-center justify-center',
          !isSessionActive && 'blend-screen'
        )}
      >
        <AnimatePresence>
          {isSessionActive && isCameraEnabled && cameraTrack && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8, height: 0, marginBottom: 0 }}
              animate={{ opacity: 1, scale: 1, height: 'auto', marginBottom: 32 }}
              exit={{ opacity: 0, scale: 0.8, height: 0, marginBottom: 0 }}
              transition={{ duration: 0.5 }}
              className="absolute bottom-full w-full flex justify-center overflow-hidden mb-8"
            >
              <div className="relative w-full aspect-video rounded-2xl overflow-hidden shadow-2xl border border-white/10 bg-black/50 backdrop-blur-sm">
                <VideoTrack
                  trackRef={cameraTrack}
                  className="w-full h-full object-cover"
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <h1 className={cn('cyberpunk-title', isSessionActive && 'active pulsate')}>
          Sfera AI
        </h1>
      </div>

      {/* Visualizer Container - positioned independently */}
      <div
        className={cn(
          'pointer-events-none absolute top-[42%] sm:top-[44%] md:top-[45%] left-1/2 -translate-x-1/2 -translate-y-1/2 transform z-10 flex items-center justify-center',
          !isSessionActive && 'blend-screen'
        )}
      >
        <SphereVisualizer isActive={isAgentSpeaking} />
      </div>

      <TileLayout chatOpen={chatOpen} />

      {/* Container for bottom controls, adapted for mobile */}
      <div className="fixed inset-x-0 bottom-0 z-50 px-2 md:inset-x-12 md:px-0">
        {appConfig.isPreConnectBufferEnabled && (
          <PreConnectMessage messages={preConnectMessages} className="z-50 pb-4" />
        )}

        {/* On mobile, this div stacks the chat and controls. On desktop, it's just a container. */}
        <div className="flex flex-col">
          <div className={cn('mb-4 flex w-full justify-center')}>
            <div className="mx-auto w-full max-w-2xl">
              <ChatPanel
                transcripts={transcripts}
                liveTranscript={null}
                isConnected={isSessionActive}
                isConnecting={false}
                isConversationActive={isConversationActive}
                chatOpen={chatOpen}
                onChatOpenChange={setChatOpen}
              />
            </div>
          </div>

          <div className="relative z-50 flex justify-center pb-3 md:pb-12">
            <ControlPanel
              isSessionActive={isSessionActive}
              isConnecting={false}
              isMuted={!microphoneToggle.enabled}
              isCameraOn={cameraToggle.enabled}
              isScreenShareOn={screenShareToggle.enabled}
              onStart={startSession}
              onStop={handleStop}
              onToggleMute={handleToggleMute}
              onToggleCamera={handleToggleCamera}
              onToggleScreenShare={handleToggleScreenShare}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

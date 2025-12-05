// Force refresh
import React, { useMemo } from 'react';
import { useRef } from 'react';
import { Track } from 'livekit-client';
import { AnimatePresence, motion } from 'motion/react';
import {
  type TrackReference,
  VideoTrack,
  useAudioWaveform,
  useLocalParticipant,
  useTracks,
  useVoiceAssistant,
} from '@livekit/components-react';
import { cn } from '@/lib/utils';


const MotionContainer = motion.create('div');

const ANIMATION_TRANSITION = {
  type: 'spring',
  stiffness: 675,
  damping: 75,
  mass: 1,
};

const classNames = {
  // GRID
  // 2 Columns x 2 Rows
  grid: [
    'h-full w-full',
    'grid gap-x-2 place-content-center',
    'grid-cols-[1fr_1fr] grid-rows-[1fr_90px]',
  ],
  // Second tile
  // chatOpen: true,
  // hasSecondTile: true
  // layout: Column 2 / Row 1
  // align: x-start y-center
  secondTileChatOpen: ['col-start-2 row-start-1', 'self-center justify-self-start'],
  // Second tile
  // chatOpen: false,
  // hasSecondTile: false
  // layout: Column 2 / Row 2
  // align: x-end y-end
  secondTileChatClosed: ['col-start-2 row-start-2', 'place-content-end'],
};

export function useLocalTrackRef(source: Track.Source) {
  const { localParticipant } = useLocalParticipant();
  const publication = localParticipant.getTrackPublication(source);
  const trackRef = useMemo<TrackReference | undefined>(
    () => (publication ? ({ source, participant: localParticipant, publication } as any) : undefined),
    [source, publication, localParticipant]
  );
  return trackRef;
}

interface TileLayoutProps {
  chatOpen: boolean;
}

export function TileLayout({ chatOpen }: TileLayoutProps) {
  const { state: agentState, audioTrack: agentAudioTrack } = useVoiceAssistant();
  const [screenShareTrack] = useTracks([Track.Source.ScreenShare]);
  const cameraTrack: TrackReference | undefined = useLocalTrackRef(Track.Source.Camera);

  const isCameraEnabled = cameraTrack && !cameraTrack.publication.isMuted;
  const isScreenShareEnabled = screenShareTrack && !screenShareTrack.publication.isMuted;

  const animationDelay = chatOpen ? 0 : 0.15;

  // Get waveform data from agent's audio track using LiveKit's built-in hook
  const { bars: waveformBars } = useAudioWaveform(agentAudioTrack, {
    barCount: 32,
    updateInterval: 50,
    volMultiplier: 1.5,
  });

  const isAgentSpeaking = agentState === 'speaking';

  return (
    <div className="pointer-events-none fixed inset-x-0 top-8 bottom-32 z-50 flex items-center justify-center md:top-12 md:bottom-40">
      <div className="relative flex h-full w-full items-center justify-center">


        {/* Camera & Screen Share - bottom right */}
        <div className="absolute right-0 bottom-0">
          <AnimatePresence>
            {screenShareTrack && isScreenShareEnabled && (
              <MotionContainer
                key="screenshare"
                layout="position"
                layoutId="screenshare"
                initial={{
                  opacity: 0,
                  scale: 0,
                }}
                animate={{
                  opacity: 1,
                  scale: 1,
                }}
                exit={{
                  opacity: 0,
                  scale: 0,
                }}
                transition={{
                  ...ANIMATION_TRANSITION,
                  delay: animationDelay,
                }}
                className="drop-shadow-lg/20"
              >
                <VideoTrack
                  trackRef={screenShareTrack}
                  width={screenShareTrack.publication.dimensions?.width ?? 0}
                  height={screenShareTrack.publication.dimensions?.height ?? 0}
                  className="bg-muted aspect-square w-[90px] rounded-md object-cover"
                />
              </MotionContainer>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

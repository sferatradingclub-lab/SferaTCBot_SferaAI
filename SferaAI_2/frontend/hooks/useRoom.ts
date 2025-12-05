import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Room, RoomEvent, TokenSource, VideoPresets, RoomOptions } from 'livekit-client';
import { AppConfig } from '@/app-config';
import { toastAlert } from '@/components/livekit/alert-toast';

export function useRoom(appConfig: AppConfig) {
  const aborted = useRef(false);

  // Configure room with optimized screen share settings
  const room = useMemo(() => {
    const roomOptions: RoomOptions = {
      // Screen share specific settings
      videoCaptureDefaults: {
        resolution: VideoPresets.h1080,
        frameRate: 30,
      },
      // Optimizations for screen content
      dynacast: true,
      adaptiveStream: true,
      // Ensure high quality for text and UI
      publishDefaults: {
        videoEncoding: {
          maxBitrate: 3_000_000, // 3 Mbps for screen share
          maxFramerate: 30,
        },
        screenShareEncoding: {
          maxBitrate: 5_000_000, // 5 Mbps specifically for screen share
          maxFramerate: 30,
        },
        dtx: false, // Don't use discontinuous transmission for better quality
        videoCodec: 'vp9', // VP9 is better for screen content than VP8
        degradationPreference: 'maintain-resolution', // Prioritize resolution over framerate for text clarity
      },
    };
    return new Room(roomOptions);
  }, []);
  const [isSessionActive, setIsSessionActive] = useState(false);

  useEffect(() => {
    function onDisconnected() {
      setIsSessionActive(false);
    }

    function onMediaDevicesError(error: Error) {
      toastAlert({
        title: 'Encountered an error with your media devices',
        description: `${error.name}: ${error.message}`,
      });
    }

    room.on(RoomEvent.Disconnected, onDisconnected);
    room.on(RoomEvent.MediaDevicesError, onMediaDevicesError);

    return () => {
      room.off(RoomEvent.Disconnected, onDisconnected);
      room.off(RoomEvent.MediaDevicesError, onMediaDevicesError);
    };
  }, [room]);

  useEffect(() => {
    return () => {
      aborted.current = true;
      room.disconnect();
    };
  }, [room]);

  const tokenSource = useMemo(
    () =>
      TokenSource.custom(async () => {
        const url = new URL(
          process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT ?? '/api/connection-details',
          window.location.origin
        );

        const initData = typeof window !== 'undefined' && window.Telegram?.WebApp?.initData || undefined;

        // Get userId from URL params (set by page.tsx)
        const searchParams = new URLSearchParams(window.location.search);
        const userId = searchParams.get('userId') || undefined;

        try {
          const res = await fetch(url.toString(), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Sandbox-Id': appConfig.sandboxId ?? '',
            },
            body: JSON.stringify({
              room_config: appConfig.agentName
                ? {
                  agents: [{ agent_name: appConfig.agentName }],
                }
                : undefined,
              userId,
              initData,
            }),
          });
          return await res.json();
        } catch (error) {
          console.error('Error fetching connection details:', error);
          throw new Error('Error fetching connection details!');
        }
      }),
    [appConfig]
  );

  const startSession = useCallback(() => {
    setIsSessionActive(true);

    if (room.state === 'disconnected') {
      const { isPreConnectBufferEnabled } = appConfig;

      // Retry logic with exponential backoff
      const connectWithRetry = async (maxRetries = 3) => {
        for (let attempt = 0; attempt < maxRetries; attempt++) {
          try {
            await Promise.all([
              room.localParticipant.setMicrophoneEnabled(true, undefined, {
                preConnectBuffer: isPreConnectBufferEnabled,
              }),
              tokenSource
                .fetch({ agentName: appConfig.agentName })
                .then((connectionDetails) =>
                  room.connect(connectionDetails.serverUrl, connectionDetails.participantToken)
                ),
            ]);

            // Success! Exit retry loop
            return;

          } catch (error) {
            console.error(`Connection attempt ${attempt + 1} failed:`, error);

            // Last attempt failed
            if (attempt === maxRetries - 1) {
              if (aborted.current) {
                return;
              }

              toastAlert({
                title: 'Unable to connect to agent',
                description: 'Please check your internet connection. Click the Start button to try again.',
              });
              setIsSessionActive(false);
              throw error;
            }

            // Wait before retry with exponential backoff
            const delay = Math.min(1000 * Math.pow(2, attempt), 5000); // Max 5s
            console.log(`Retrying in ${delay}ms...`);
            await new Promise(resolve => setTimeout(resolve, delay));
          }
        }
      };

      connectWithRetry().catch((error) => {
        console.error('All connection attempts failed:', error);
      });
    }
  }, [room, appConfig, tokenSource, aborted]);

  const endSession = useCallback(() => {
    if (room.state !== 'disconnected') {
      room.disconnect();
    }
    setIsSessionActive(false);
  }, [room]);

  return { room, isSessionActive, startSession, endSession };
}

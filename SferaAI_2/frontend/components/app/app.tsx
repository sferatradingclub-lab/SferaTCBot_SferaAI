'use client';

import { RoomAudioRenderer, StartAudio } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { SessionProvider } from '@/components/app/session-provider';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/livekit/toaster';

const defaultAppConfig: AppConfig = {
  title: 'Sfera AI',
  description: 'AI Voice Assistant',
  sandboxId: '',
  isPreConnectBufferEnabled: false,
  agentName: '',
};

interface AppProps {
  appConfig?: AppConfig;
}

export function App({ appConfig = defaultAppConfig }: AppProps) {
  return (
    <SessionProvider appConfig={appConfig}>
      <main className="grid h-svh grid-cols-1 place-content-center relative overflow-hidden bg-gradient-to-br from-[#0a0a0a] via-[#1a1a2e] to-[#16213e]">
        <div className="fixed inset-0 -z-10 pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] h-[700px] w-[700px] rounded-full bg-[#ff0f7b]/30 blur-[140px] animate-pulse" style={{ animationDuration: '10s' }} />
          <div className="absolute bottom-[-10%] right-[-10%] h-[700px] w-[700px] rounded-full bg-[#f89b29]/30 blur-[140px] animate-pulse" style={{ animationDuration: '12s', animationDelay: '2s' }} />
          <div className="absolute top-[20%] right-[20%] h-[500px] w-[500px] rounded-full bg-[#00c9ff]/30 blur-[120px] animate-pulse" style={{ animationDuration: '15s', animationDelay: '1s' }} />
        </div>
        <ViewController />
      </main>
      <StartAudio label="Start Audio" />
      <RoomAudioRenderer />
      <Toaster />
    </SessionProvider>
  );
}

'use client';

import { Button } from '@/components/livekit/button';
import { AgentAvatar } from '../common/AgentAvatar';
import { CyberpunkBackground } from '../common/CyberpunkBackground';
import { ClientOnly } from './client-only-wrapper';

interface AnimatedWelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const AnimatedWelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & AnimatedWelcomeViewProps) => {
  return (
    <div ref={ref} className="relative h-screen w-screen overflow-hidden bg-gray-900">
      <ClientOnly>
        <CyberpunkBackground />
      </ClientOnly>
      <div className="relative z-10 flex h-full flex-col items-center justify-center text-center">
        <div className="mb-4 h-16 w-16 flex-shrink-0">
          <ClientOnly>
            <AgentAvatar isSpeaking={false} />
          </ClientOnly>
        </div>
        <p className="text-foreground max-w-prose pt-1 text-xl leading-6 font-medium text-white">
          Chat live with your voice AI agent
        </p>
        <Button
          variant="primary"
          size="lg"
          onClick={onStartCall}
          className="hover:bg-cyan-60 mt-6 w-64 bg-cyan-500 font-mono text-gray-900"
        >
          {startButtonText}
        </Button>
      </div>
      <div className="fixed bottom-5 left-0 z-20 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty text-white md:text-sm">
          Need help getting set up? Check out the{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://docs.livekit.io/agents/start/voice-ai/"
            className="underline"
          >
            Voice AI quickstart
          </a>
          .
        </p>
      </div>
    </div>
  );
};

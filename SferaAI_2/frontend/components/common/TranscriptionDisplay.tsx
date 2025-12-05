import React, { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { AgentAvatar } from './AgentAvatar';
import type { TranscriptMessage } from './types';

interface TranscriptionDisplayProps {
  transcripts: TranscriptMessage[];
  liveTranscript: TranscriptMessage | null;
  isConnected: boolean;
  isConnecting: boolean;
}

const MessageEntry: React.FC<{ entry: TranscriptMessage; isLive?: boolean }> = ({
  entry,
  isLive = false,
}) => {
  const textShadow = '1px 1px 3px rgba(0,0,0,0.7)';

  return (
    <div
      className={`flex items-start gap-3 ${
        entry.speaker === 'user' ? 'flex-row-reverse' : 'flex-row'
      }`}
    >
      {entry.speaker === 'agent' && <AgentAvatar isSpeaking={!!isLive} />}
      <div className={`flex flex-col ${entry.speaker === 'user' ? 'items-end' : 'items-start'}`}>
        <span className="mb-1 px-2 text-xs text-gray-400" style={{ textShadow }}>
          {entry.speaker === 'user' ? 'You' : 'Sfera AI'}
        </span>
        <div
          className={`max-w-md rounded-2xl p-3 shadow-lg ${
            entry.speaker === 'user'
              ? 'rounded-br-none bg-blue-600/[.35]'
              : 'rounded-bl-none bg-black/[.25]'
          }`}
        >
          <p
            className={`text-base leading-relaxed ${isLive ? 'text-gray-200' : 'text-white'}`}
            style={{ textShadow }}
          >
            {entry.text}
            {isLive && (
              <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-gray-300 align-middle"></span>
            )}
          </p>
        </div>
      </div>
    </div>
  );
};

export const TranscriptionDisplay: React.FC<TranscriptionDisplayProps> = ({
  transcripts,
  liveTranscript,
  isConnected,
  isConnecting,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const hasActiveSession = isConnecting || isConnected;
  const hasMeaningfulContent = transcripts.length > 0 || !!liveTranscript?.text;

  useEffect(() => {
    // Всегда прокручиваем к последнему сообщению при получении новых сообщений
    if (scrollContainerRef.current) {
      // Прокручиваем к последнему сообщению с плавной анимацией
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [transcripts, liveTranscript]);

  return (
    // This outer container is always in the DOM, providing a stable element for the flex layout.
    <div className="chat-panel mx-auto min-h-0 w-full max-w-2xl">
      {/* This is the actual chat box. Its visibility and size are transitioned via CSS for stability. */}
      <div
        ref={scrollContainerRef}
        className="custom-scrollbar relative flex h-full w-full flex-col overflow-y-auto rounded-2xl border border-white/5 bg-white/0 shadow-[0_8px_32px_rgba(0,0,0,0.05),0_0_5px_rgba(255,255,255,0.05)] backdrop-blur-3xl transition-all duration-300 ease-in-out hover:shadow-[0_8px_32px_rgba(0,0,0,0.05),0_0_35px_rgba(0,255,255,1.0)]"
        style={{
          maxHeight: hasActiveSession ? '30vh' : '0', // Reduced to approximately half the previous height
          minHeight: hasActiveSession && !hasMeaningfulContent ? '6rem' : '0',
          opacity: hasActiveSession ? 1 : 0,
          pointerEvents: hasActiveSession ? 'auto' : 'none',
        }}
      >
        {/* Message list container */}
        <div
          className={`w-full space-y-4 p-4 transition-opacity duration-500 ease-in-out ${hasMeaningfulContent ? 'opacity-100' : 'opacity-0'}`}
        >
          {transcripts.map((entry) => (
            <MessageEntry key={entry.id} entry={entry} />
          ))}
          {liveTranscript && liveTranscript.text && <MessageEntry entry={liveTranscript} isLive />}
        </div>

        {/* Placeholder text for connecting/listening states */}
        <div
          className={`pointer-events-none absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${!hasMeaningfulContent && hasActiveSession ? 'opacity-100' : 'opacity-0'}`}
        >
          {isConnecting ? (
            <p className="animate-pulse text-gray-300">Подключение...</p>
          ) : (
            <p className="animate-pulse text-gray-300">Sfera AI слушает...</p>
          )}
        </div>
      </div>
    </div>
  );
};

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useChat, useRemoteParticipants } from '@livekit/components-react';
import Linkify from 'react-linkify';
import {
  CaretDown,
  CaretUp,
  PaperPlaneRightIcon,
  SpinnerIcon,
} from '@phosphor-icons/react/dist/ssr';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { TranscriptMessage } from './types';

interface ChatPanelProps {
  transcripts: TranscriptMessage[];
  liveTranscript: TranscriptMessage | null;
  isConnected: boolean;
  isConnecting: boolean;
  isConversationActive?: boolean;
  chatOpen?: boolean;
  onChatOpenChange?: (open: boolean) => void;
}

const MessageEntry: React.FC<{ entry: TranscriptMessage; isLive?: boolean; onImageClick?: (url: string) => void }> = ({
  entry,
  isLive = false,
  onImageClick,
}) => {
  return (
    <div
      className={`flex items-start gap-3 ${entry.speaker === 'user' ? 'flex-row-reverse' : 'flex-row'
        }`}
    >
      {/* AgentAvatar removed */}
      <div className={`flex flex-col ${entry.speaker === 'user' ? 'items-end' : 'items-start'}`}>
        <span className="mb-1 px-2 text-xs font-medium text-white/40">
          {entry.speaker === 'user' ? 'You' : 'Sfera AI'}
        </span>

        {/* YouTube Card */}
        {entry.youtubeVideo ? (
          <a
            href={entry.youtubeVideo.videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="group relative block w-full max-w-sm overflow-hidden rounded-xl bg-black/40 border border-white/10 hover:border-[#0A84FF]/50 transition-all duration-300 hover:shadow-[0_0_20px_rgba(10,132,255,0.3)]"
          >
            <div className="relative aspect-video w-full overflow-hidden">
              <img
                src={entry.youtubeVideo.thumbnailUrl}
                alt={entry.youtubeVideo.title}
                className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
              <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/10 transition-colors">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/20 backdrop-blur-md border border-white/30 shadow-lg transition-transform duration-300 group-hover:scale-110">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white" viewBox="0 0 256 256">
                    <path d="M240,128a15.74,15.74,0,0,1-7.6,13.51L88.32,229.65a16,16,0,0,1-16.2.3A15.86,15.86,0,0,1,64,216.13V39.87a15.86,15.86,0,0,1,8.12-13.82,16,16,0,0,1,16.2.3L232.4,114.49A15.74,15.74,0,0,1,240,128Z"></path>
                  </svg>
                </div>
              </div>
            </div>
            <div className="p-3">
              <h3 className="line-clamp-2 text-sm font-medium text-white group-hover:text-[#0A84FF] transition-colors">
                {entry.youtubeVideo.title}
              </h3>
            </div>
          </a>
        ) : (
          /* Standard Text Message */
          <div
            className={`max-w-md rounded-2xl p-4 transition-all duration-300 ${entry.speaker === 'user'
              ? 'rounded-br-sm bg-[#0A84FF]/60 border border-[#0A84FF]/30 text-white shadow-[0_4px_20px_rgba(10,132,255,0.2)] backdrop-blur-xl'
              : 'rounded-bl-sm bg-white/10 border border-white/10 text-white/90 shadow-[0_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-xl'
              }`}
          >
            <p className="text-base leading-relaxed">
              <Linkify
                componentDecorator={(decoratedHref, decoratedText, key) => (
                  <a
                    target="_blank"
                    rel="noopener noreferrer"
                    href={decoratedHref}
                    key={key}
                    className="text-[#0A84FF] hover:text-[#409CFF] hover:underline underline-offset-2 transition-colors font-medium"
                  >
                    {decoratedText}
                  </a>
                )}
              >
                {entry.text}
              </Linkify>
              {isLive && (
                <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-white/50 align-middle"></span>
              )}
            </p>
            {entry.imageUrl && (
              (() => {
                console.log('[SferaAI Debug] Rendering image with src:', entry.imageUrl);
                return (
                  <img
                    src={entry.imageUrl}
                    alt="Agent response image"
                    className="mt-3 w-full max-w-xs rounded-lg border border-white/10 shadow-lg cursor-pointer"
                    onClick={() => onImageClick?.(entry.imageUrl!)}
                    onError={(e) => console.error('[SferaAI Debug] Image failed to load:', entry.imageUrl, e)}
                  />
                );
              })()
            )}
          </div>
        )}
      </div>
    </div>
  );
};
const MemoizedMessageEntry = React.memo(MessageEntry);

const ChatInput: React.FC<{
  isAgentAvailable?: boolean;
  onSend?: (message: string) => void;
  chatOpen?: boolean;
  onChatOpenChange?: (open: boolean) => void;
}> = ({ isAgentAvailable = false, onSend = async () => { }, chatOpen = true, onChatOpenChange }) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isSending, setIsSending] = useState(false);
  const [message, setMessage] = useState<string>('');

  const handleSendMessage = async () => {
    if (!message.trim()) return;

    try {
      setIsSending(true);
      await onSend(message);
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    handleSendMessage();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const isDisabled = isSending || !isAgentAvailable;

  return (
    <div
      className="border-t border-white/10 bg-black/20 p-3 backdrop-blur-xl flex w-full items-end gap-2"
    >
      <Button
        variant="ghost"
        size="icon"
        onClick={() => onChatOpenChange && onChatOpenChange(!chatOpen)}
        className="h-12 w-12 shrink-0 rounded-full text-white/50 hover:bg-white/10 hover:text-white md:h-10 md:w-10 transition-colors"
      >
        {chatOpen ? <CaretDown /> : <CaretUp />}
      </Button>
      <form onSubmit={handleSubmit} className="flex w-full grow items-end gap-2">
        <div className="relative flex-1">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="max-h-32 min-h-12 w-full resize-none rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white placeholder:text-white/30 focus:border-white/20 focus:bg-white/10 focus:outline-none focus:ring-0 disabled:cursor-not-allowed disabled:opacity-50 md:min-h-10 md:py-2 md:text-sm transition-all duration-200"
            disabled={isDisabled}
          />
        </div>
        <Button
          size="icon"
          type="submit"
          disabled={isDisabled || message.trim().length === 0}
          title={isSending ? 'Sending...' : 'Send'}
          className="h-12 w-12 shrink-0 self-end rounded-full bg-[#0A84FF] hover:bg-[#0077ED] text-white shadow-lg disabled:bg-white/10 disabled:text-white/20 md:h-10 md:w-10 transition-all duration-200"
        >
          {isSending ? (
            <SpinnerIcon className="animate-spin" weight="bold" />
          ) : (
            <PaperPlaneRightIcon weight="fill" />
          )}
        </Button>
      </form>
    </div>
  );
};
const MemoizedChatInput = React.memo(ChatInput);

export const ChatPanel: React.FC<ChatPanelProps> = ({
  transcripts,
  liveTranscript,
  isConnected,
  isConnecting,
  isConversationActive = false,
  chatOpen = true,
  onChatOpenChange,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const { send } = useChat();
  const participants = useRemoteParticipants();
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const handleImageClick = useCallback((url: string) => {
    setSelectedImage(url);
  }, []);

  const isAgentAvailable = participants.some((p) => p.isAgent);

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (send) {
        await send(message);
      }
    },
    [send]
  );

  useEffect(() => {
    if (scrollContainerRef.current && chatOpen) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [transcripts, liveTranscript, chatOpen]);

  const hasActiveSession = isConnecting || isConnected;
  const hasMeaningfulContent = transcripts.length > 0 || !!liveTranscript?.text;

  if (!hasActiveSession) {
    return null;
  }

  return (
    <div className="chat-panel relative mx-auto w-full max-w-2xl">
      <div
        className="custom-scrollbar flex h-full w-full flex-col overflow-hidden rounded-[20px] shadow-[20px_20px_50px_rgba(0,0,0,0.5)] transition-all duration-500 ease-out hover:shadow-[0_0_15px_rgba(0,201,255,0.7),0_0_30px_rgba(0,201,255,0.5),inset_0_0_10px_rgba(0,201,255,0.3)]"
        style={{
          background: 'rgba(255, 255, 255, 0.02)',
          backdropFilter: 'blur(10px)',
          WebkitBackdropFilter: 'blur(10px)',
          borderTop: '1px solid rgba(255, 255, 255, 0.5)',
          borderLeft: '1px solid rgba(255, 255, 255, 0.5)',
          opacity: hasActiveSession ? 1 : 0,
          pointerEvents: hasActiveSession ? 'auto' : 'none',
        }}
      >
        {/* Message list container */}
        <div
          ref={scrollContainerRef}
          className={cn(
            'relative flex-1 transition-[max-height] duration-300 ease-in-out',
            chatOpen
              ? 'max-h-[75dvh] overflow-y-auto md:max-h-[40vh] lg:max-h-[30vh]'
              : 'max-h-4 overflow-hidden'
          )}
        >
          <div
            className={`w-full space-y-6 p-5 transition-opacity duration-500 ease-in-out ${hasMeaningfulContent ? 'opacity-100' : 'opacity-0'
              }`}
          >
            {transcripts.map((entry) => (
              <MemoizedMessageEntry
                key={entry.id}
                entry={entry}
                onImageClick={handleImageClick}
              />
            ))}
            {liveTranscript && liveTranscript.text && (
              <MemoizedMessageEntry
                entry={liveTranscript}
                isLive
                onImageClick={handleImageClick}
              />
            )}
          </div>

          <div
            className={`pointer-events-none absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${!hasMeaningfulContent && hasActiveSession && chatOpen ? 'opacity-100' : 'opacity-0'
              }`}
          >
            {isConnecting ? (
              <p className="animate-pulse text-white/50 font-medium tracking-wide text-sm">INITIALIZING...</p>
            ) : (
              <p className="animate-pulse text-white/50 font-medium tracking-wide text-sm">LISTENING...</p>
            )}
          </div>
        </div>

        {isConversationActive && (
          <MemoizedChatInput
            isAgentAvailable={isAgentAvailable}
            onSend={handleSendMessage}
            chatOpen={chatOpen}
            onChatOpenChange={onChatOpenChange}
          />
        )}
      </div>

      {/* Image Lightbox Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 transition-all duration-300"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-h-[90vh] max-w-[90vw] overflow-hidden rounded-2xl shadow-2xl border border-white/10">
            <img
              src={selectedImage}
              alt="Full size view"
              className="max-h-[90vh] max-w-[90vw] object-contain"
            />
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute top-4 right-4 rounded-full bg-black/50 p-2 text-white hover:bg-white/20 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 256 256">
                <path d="M205.66,194.34a8,8,0,0,1-11.32,11.32L128,139.31,61.66,205.66a8,8,0,0,1-11.32-11.32L116.69,128,50.34,61.66A8,8,0,0,1,61.66,50.34L128,116.69l66.34-66.35a8,8,0,0,1,11.32,11.32L139.31,128Z"></path>
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
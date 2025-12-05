'use client';

import Image from 'next/image';
import { AnimatePresence, type HTMLMotionProps, motion } from 'motion/react';
import { type ReceivedChatMessage } from '@livekit/components-react';
import { ChatEntry as ChatEntryView } from '@/components/livekit/chat-entry';
import { type ChatEntry, isImageMessage } from '@/hooks/useChatMessages';

const MotionContainer = motion.create('div');
const MotionChatEntry = motion.create(ChatEntryView);

const CONTAINER_MOTION_PROPS = {
  variants: {
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeOut',
        duration: 0.3,
        staggerChildren: 0.1,
        staggerDirection: -1,
      },
    },
    visible: {
      opacity: 1,
      transition: {
        delay: 0.2,
        ease: 'easeOut',
        duration: 0.3,
        stagerDelay: 0.2,
        staggerChildren: 0.1,
        staggerDirection: 1,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const MESSAGE_MOTION_PROPS = {
  variants: {
    hidden: {
      opacity: 0,
      translateY: 10,
    },
    visible: {
      opacity: 1,
      translateY: 0,
    },
  },
};

interface ChatTranscriptProps {
  hidden?: boolean;
  messages?: ChatEntry[];
}

export function ChatTranscript({
  hidden = false,
  messages = [],
  ...props
}: ChatTranscriptProps & Omit<HTMLMotionProps<'div'>, 'ref'>) {
  return (
    <AnimatePresence>
      {!hidden && (
        <MotionContainer {...CONTAINER_MOTION_PROPS} {...props}>
          {messages.map((entry) => {
            if (isImageMessage(entry)) {
              return (
                <MotionContainer
                  key={entry.id}
                  {...MESSAGE_MOTION_PROPS}
                  className="mx-auto my-2 w-full max-w-md overflow-hidden rounded-xl"
                >
                  <Image
                    src={entry.url}
                    alt="Image from agent"
                    width={400}
                    height={300}
                    layout="responsive"
                  />
                </MotionContainer>
              );
            }

            // It's a ReceivedChatMessage
            const { id, timestamp, from, message, editTimestamp } = entry;
            const locale = navigator?.language ?? 'en-US';
            const messageOrigin = from?.isLocal ? 'local' : 'remote';
            const hasBeenEdited = !!editTimestamp;

            return (
              <MotionChatEntry
                key={id}
                locale={locale}
                timestamp={timestamp}
                message={message}
                messageOrigin={messageOrigin}
                hasBeenEdited={hasBeenEdited}
                {...MESSAGE_MOTION_PROPS}
              />
            );
          })}
        </MotionContainer>
      )}
    </AnimatePresence>
  );
}

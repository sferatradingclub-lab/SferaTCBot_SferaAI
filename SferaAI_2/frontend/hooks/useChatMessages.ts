import { useEffect, useMemo, useState } from 'react';
import { Room } from 'livekit-client';
import {
  type ReceivedChatMessage,
  type TextStreamData,
  useChat,
  useDataChannel,
  useRoomContext,
  useTranscriptions,
} from '@livekit/components-react';

export type ImageMessage = {
  type: 'image';
  id: string;
  timestamp: number;
  url: string;
  from?: ReceivedChatMessage['from'];
};

export type LinkMessage = {
  type: 'link';
  id: string;
  timestamp: number;
  url: string;
  from?: ReceivedChatMessage['from'];
};

export type YouTubeMessage = {
  type: 'youtube';
  id: string;
  timestamp: number;
  youtubeVideo: {
    title: string;
    thumbnailUrl: string;
    videoUrl: string;
  };
  from?: ReceivedChatMessage['from'];
};

export type ChatEntry = ReceivedChatMessage | ImageMessage | LinkMessage | YouTubeMessage;

export function isImageMessage(msg: ChatEntry): msg is ImageMessage {
  return (msg as ImageMessage).type === 'image';
}

export function isLinkMessage(msg: ChatEntry): msg is LinkMessage {
  return (msg as LinkMessage).type === 'link';
}

export function isYouTubeMessage(msg: ChatEntry): msg is YouTubeMessage {
  return (msg as YouTubeMessage).type === 'youtube';
}

function transcriptionToChatMessage(textStream: TextStreamData, room: Room): ReceivedChatMessage {
  return {
    id: textStream.streamInfo.id,
    timestamp: textStream.streamInfo.timestamp,
    message: textStream.text,
    from:
      textStream.participantInfo.identity === room.localParticipant.identity
        ? room.localParticipant
        : Array.from(room.remoteParticipants.values()).find(
          (p) => p.identity === textStream.participantInfo.identity
        ),
  };
}

export function useChatMessages() {
  const chat = useChat();
  const room = useRoomContext();
  const transcriptions: TextStreamData[] = useTranscriptions();
  const [imageMessages, setImageMessages] = useState<ImageMessage[]>([]);
  const [linkMessages, setLinkMessages] = useState<LinkMessage[]>([]);
  const [youtubeMessages, setYoutubeMessages] = useState<YouTubeMessage[]>([]);

  // Clear messages when room disconnects
  useEffect(() => {
    const handleDisconnected = () => {
      console.log('[SferaAI] Clearing chat messages on disconnect');
      setImageMessages([]);
      setLinkMessages([]);
      setYoutubeMessages([]);
    };

    room.on('disconnected', handleDisconnected);
    return () => {
      room.off('disconnected', handleDisconnected);
    };
  }, [room]);

  useDataChannel('sfera-image', (msg) => {
    const { imageUrl } = JSON.parse(new TextDecoder().decode(msg.payload));
    console.log('[SferaAI Debug] Received image payload:', imageUrl);
    if (imageUrl) {
      const imageMessage: ImageMessage = {
        type: 'image',
        id: `img-${Date.now()}`,
        timestamp: Date.now(),
        url: imageUrl,
        from: msg.from,
      };
      setImageMessages((prev) => [...prev, imageMessage]);
    }
  });

  useDataChannel('sfera-link', (msg) => {
    const { url } = JSON.parse(new TextDecoder().decode(msg.payload));
    if (url) {
      const linkMessage: LinkMessage = {
        type: 'link',
        id: `link-${Date.now()}`,
        timestamp: Date.now(),
        url: url,
        from: msg.from,
      };
      setLinkMessages((prev) => [...prev, linkMessage]);
    }
  });

  useDataChannel('sfera-youtube', (msg) => {
    const data = JSON.parse(new TextDecoder().decode(msg.payload));
    if (data.title && data.thumbnailUrl && data.videoUrl) {
      const youtubeMessage: YouTubeMessage = {
        type: 'youtube',
        id: `yt-${Date.now()}-${Math.random()}`,
        timestamp: Date.now(),
        youtubeVideo: {
          title: data.title,
          thumbnailUrl: data.thumbnailUrl,
          videoUrl: data.videoUrl,
        },
        from: msg.from,
      };
      setYoutubeMessages((prev) => [...prev, youtubeMessage]);
    }
  });

  const mergedMessages = useMemo(() => {
    const merged: Array<ChatEntry> = [
      ...transcriptions.map((transcription) => transcriptionToChatMessage(transcription, room)),
      ...chat.chatMessages,
      ...imageMessages,
      ...linkMessages,
      ...youtubeMessages,
    ];
    return merged.sort((a, b) => a.timestamp - b.timestamp);
  }, [transcriptions, chat.chatMessages, imageMessages, linkMessages, youtubeMessages, room]);

  return mergedMessages;
}

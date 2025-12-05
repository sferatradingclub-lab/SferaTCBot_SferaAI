export interface TranscriptMessage {
  id: string;
  speaker: 'user' | 'agent';
  text: string;
  imageUrl?: string;
  linkUrl?: string;
  youtubeVideo?: {
    title: string;
    thumbnailUrl: string;
    videoUrl: string;
  };
}

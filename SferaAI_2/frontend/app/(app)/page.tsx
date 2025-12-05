'use client';

import { App } from '@/components/app/app';
import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function Page() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Check if userId is in URL
    const userId = searchParams.get('userId');
    if (!userId) {
      // Generate or retrieve from localStorage
      let storedUserId = localStorage.getItem('sfera_user_id');
      if (!storedUserId) {
        storedUserId = `voice_assistant_user_${Math.floor(Math.random() * 10000)}`;
        localStorage.setItem('sfera_user_id', storedUserId);
      }
      // Add userId to URL
      const newUrl = `/?userId=${storedUserId}`;
      router.replace(newUrl);
    }
  }, [searchParams, router]);

  return <App />;
}

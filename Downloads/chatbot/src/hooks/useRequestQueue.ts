import { useState, useRef, useCallback } from 'react';

type Task<T> = () => Promise<T>;

interface QueueItem<T> {
  task: Task<T>;
  resolve: (value: T | PromiseLike<T>) => void;
  reject: (reason?: any) => void;
}

export function useRequestQueue() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [queueLength, setQueueLength] = useState(0);
  
  const queueRef = useRef<QueueItem<any>[]>([]);
  const isProcessingRef = useRef<boolean>(false);

  const processQueue = useCallback(async () => {
    if (isProcessingRef.current || queueRef.current.length === 0) return;

    isProcessingRef.current = true;
    setIsProcessing(true);

    while (queueRef.current.length > 0) {
      const currentItem = queueRef.current.shift();
      if (currentItem) {
        setQueueLength(queueRef.current.length);
        
        try {
          const result = await currentItem.task();
          currentItem.resolve(result);
        } catch (error) {
          currentItem.reject(error);
        }
      }
    }

    isProcessingRef.current = false;
    setIsProcessing(false);
    setQueueLength(0);
  }, []);

  const enqueue = useCallback(<T,>(task: Task<T>): Promise<T> => {
    return new Promise((resolve, reject) => {
      queueRef.current.push({ task, resolve, reject });
      setQueueLength(queueRef.current.length);
      processQueue();
    });
  }, [processQueue]);

  return {
    enqueue,
    isProcessing,
    queueLength,
  };
}

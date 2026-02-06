# Real-Time Connections - Kamiwaza Extensions

## Server-Sent Events (SSE) Pattern

### Vercel AI SDK Streaming (ai-chatbot)

#### Server-Side Streaming
```typescript
// app/(chat)/api/chat/route.ts
import {
  createDataStream,
  streamText,
  smoothStream,
} from 'ai';

export const maxDuration = 60;

export async function POST(request: Request) {
  const { id, message, selectedChatModel } = await request.json();

  const stream = createDataStream({
    execute: async (dataStream) => {
      const result = streamText({
        model: kamiwazaModel(port, selectedChatModel),
        system: systemPrompt({ selectedChatModel: modelName }),
        messages: filteredMessages,
        maxSteps: 5,
        experimental_transform: smoothStream({ chunking: 'word' }),
        experimental_generateMessageId: generateUUID,
        tools: {
          getWeather,
          createDocument: createDocument({ session, dataStream }),
          updateDocument: updateDocument({ session, dataStream }),
        },
        onFinish: async ({ response }) => {
          // Save messages to database
          await saveMessages({
            messages: [
              {
                id: assistantId,
                chatId: id,
                role: 'assistant',
                parts: processedParts,
                createdAt: new Date(),
              },
            ],
          });

          // Send custom data stream events
          dataStream.writeData({
            type: 'title-updated',
            content: title,
          });
        },
      });

      // Consume the stream
      result.consumeStream();

      // Merge into data stream
      result.mergeIntoDataStream(dataStream, {
        sendReasoning: true,
      });
    },
    onError: (error) => {
      console.error('Stream error:', error);
      return 'Oops, an error occurred!';
    },
  });

  return new Response(stream);
}
```

#### Client-Side Stream Handling
```typescript
// components/data-stream-handler.tsx
'use client';

import { useChat } from '@ai-sdk/react';
import { useEffect, useRef } from 'react';

export type DataStreamDelta = {
  type:
    | 'text-delta'
    | 'code-delta'
    | 'title'
    | 'id'
    | 'suggestion'
    | 'clear'
    | 'finish'
    | 'title-updated';
  content: string | object;
};

export function DataStreamHandler({ id }: { id: string }) {
  const { data: dataStream } = useChat({ id });
  const { artifact, setArtifact } = useArtifact();
  const lastProcessedIndex = useRef(-1);

  useEffect(() => {
    if (!dataStream?.length) return;

    const newDeltas = dataStream.slice(lastProcessedIndex.current + 1);
    lastProcessedIndex.current = dataStream.length - 1;

    (newDeltas as DataStreamDelta[]).forEach((delta: DataStreamDelta) => {
      setArtifact((draftArtifact) => {
        switch (delta.type) {
          case 'id':
            return {
              ...draftArtifact,
              documentId: delta.content as string,
              status: 'streaming',
            };

          case 'title':
            return {
              ...draftArtifact,
              title: delta.content as string,
              status: 'streaming',
            };

          case 'finish':
            return {
              ...draftArtifact,
              status: 'idle',
            };

          case 'title-updated':
            // Trigger SWR mutation
            mutate('/api/history');
            return draftArtifact;

          default:
            return draftArtifact;
        }
      });
    });
  }, [dataStream, setArtifact, artifact]);

  return null;
}
```

## Resumable Streams with Redis

### Server Context Setup
```typescript
import { createResumableStreamContext } from 'resumable-stream';
import { after } from 'next/server';

let globalStreamContext: ResumableStreamContext | null = null;

function getStreamContext() {
  if (!globalStreamContext) {
    try {
      globalStreamContext = createResumableStreamContext({
        waitUntil: after,
      });
    } catch (error: any) {
      if (error.message.includes('REDIS_URL')) {
        console.log('Resumable streams disabled - missing REDIS_URL');
      } else {
        console.error(error);
      }
    }
  }
  return globalStreamContext;
}
```

### Stream Resumption
```typescript
export async function POST(request: Request) {
  const streamId = generateUUID();
  await createStreamId({ streamId, chatId: id });

  const stream = createDataStream({ /* ... */ });
  const streamContext = getStreamContext();

  if (streamContext) {
    // Resumable stream (with Redis)
    return new Response(
      await streamContext.resumableStream(streamId, () => stream),
    );
  } else {
    // Simple stream (no Redis)
    return new Response(stream);
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const chatId = searchParams.get('chatId');
  const streamContext = getStreamContext();

  if (!streamContext) {
    return new Response(null, { status: 204 });
  }

  const streamIds = await getStreamIdsByChatId({ chatId });
  const recentStreamId = streamIds.at(-1);

  // Resume the stream
  const stream = await streamContext.resumableStream(
    recentStreamId,
    () => emptyDataStream,
  );

  // If stream concluded, restore from database
  if (!stream) {
    const messages = await getMessagesByChatId({ id: chatId });
    const mostRecentMessage = messages.at(-1);

    const restoredStream = createDataStream({
      execute: (buffer) => {
        buffer.writeData({
          type: 'append-message',
          message: JSON.stringify(mostRecentMessage),
        });
      },
    });

    return new Response(restoredStream, { status: 200 });
  }

  return new Response(stream, { status: 200 });
}
```

## Stream Transformation

### Smooth Streaming
```typescript
import { smoothStream } from 'ai';

const result = streamText({
  model: kamiwazaModel(port, modelId),
  messages: [...],
  experimental_transform: smoothStream({ chunking: 'word' }),
});
```

### Custom Transformations
```typescript
export function applyThinkTagProcessing(parts: any[]) {
  return parts.map(part => {
    if (part.type === 'text') {
      const text = part.text || '';
      const thinkPattern = /<think>([\s\S]*?)<\/think>/g;
      const hasThinkTags = thinkPattern.test(text);

      if (hasThinkTags) {
        const processedParts = [];
        let lastIndex = 0;

        text.replace(thinkPattern, (match, thinking, offset) => {
          // Add text before think tag
          if (offset > lastIndex) {
            processedParts.push({
              type: 'text',
              text: text.slice(lastIndex, offset),
            });
          }

          // Add reasoning part
          processedParts.push({
            type: 'reasoning',
            reasoning: thinking.trim(),
          });

          lastIndex = offset + match.length;
          return match;
        });

        // Add remaining text
        if (lastIndex < text.length) {
          processedParts.push({
            type: 'text',
            text: text.slice(lastIndex),
          });
        }

        return processedParts;
      }
    }
    return part;
  }).flat();
}
```

## Data Stream Events

### Custom Event Types
```typescript
// Server-side: Send custom events
dataStream.writeData({
  type: 'title-updated',
  content: title,
});

dataStream.writeData({
  type: 'suggestion',
  content: {
    id: suggestionId,
    documentId: documentId,
    text: suggestionText,
  },
});

// Client-side: Handle custom events
useEffect(() => {
  newDeltas.forEach((delta: DataStreamDelta) => {
    switch (delta.type) {
      case 'title-updated':
        mutate('/api/history'); // Refresh UI
        break;

      case 'suggestion':
        setSuggestions(prev => [...prev, delta.content]);
        break;
    }
  });
}, [dataStream]);
```

## LLM Streaming Integration

### Kamiwaza Model Provider
```typescript
import { createOpenAI } from '@ai-sdk/openai';

export function kamiwazaModel(port: number, modelId: string) {
  const baseURL = `http://localhost:${port}/v1`;

  const provider = createOpenAI({
    apiKey: 'not-needed-kamiwaza',
    baseURL,
  });

  return provider(modelId);
}
```

### Stream with Tools
```typescript
const result = streamText({
  model: kamiwazaModel(port, selectedChatModel),
  system: systemPrompt({ selectedChatModel }),
  messages: filteredMessages,
  maxSteps: 5,
  experimental_activeTools: [
    'getWeather',
    'createDocument',
    'updateDocument',
  ],
  tools: {
    getWeather: {
      description: 'Get weather for location',
      parameters: z.object({
        city: z.string(),
      }),
      execute: async ({ city }) => {
        const data = await fetchWeather(city);
        return data;
      },
    },
    createDocument: {
      description: 'Create new document',
      parameters: z.object({
        title: z.string(),
      }),
      execute: async ({ title }) => {
        const doc = await saveDocument({ title });
        dataStream.writeData({
          type: 'id',
          content: doc.id,
        });
        return doc;
      },
    },
  },
  onFinish: async ({ response }) => {
    await saveMessages({ messages: response.messages });
  },
});
```

## Error Handling

### Stream Error Recovery
```typescript
const stream = createDataStream({
  execute: async (dataStream) => {
    try {
      const result = streamText({ /* ... */ });
      result.mergeIntoDataStream(dataStream);
    } catch (error) {
      dataStream.writeData({
        type: 'error',
        content: error.message,
      });
      throw error;
    }
  },
  onError: (error) => {
    console.error('Stream error:', error);
    return 'An error occurred during streaming';
  },
});
```

### Client Error Handling
```typescript
const { error, isLoading } = useChat({ id });

useEffect(() => {
  if (error) {
    console.error('Chat error:', error);
    toast.error('Failed to send message');
  }
}, [error]);
```

## Performance Optimization

### Word-Level Chunking
```typescript
experimental_transform: smoothStream({ chunking: 'word' })
```

### Debounced Updates
```typescript
const debouncedUpdate = useDebouncedCallback(
  (content: string) => {
    setArtifact(prev => ({ ...prev, content }));
  },
  100
);

useEffect(() => {
  if (delta.type === 'text-delta') {
    debouncedUpdate(currentContent + delta.content);
  }
}, [dataStream]);
```

## Key Principles

### 1. Use AI SDK for LLM Streaming
- `streamText` for text generation
- `createDataStream` for custom events
- `smoothStream` for better UX

### 2. Handle Stream State
- Track `lastProcessedIndex` to avoid duplicates
- Use `status: 'streaming' | 'idle'` for UI states
- Clean up on unmount

### 3. Resumable Streams (Optional)
- Requires Redis connection
- Gracefully degrade to simple streams
- Restore from database on resume failure

### 4. Custom Events
- Use `dataStream.writeData()` for metadata
- Define clear event types
- Handle all event types client-side

### 5. Error Recovery
- Implement `onError` handlers
- Restore partial state from database
- Show user-friendly error messages

## Anti-Patterns

### ❌ Missing Stream Cleanup
```typescript
// Wrong - memory leak
useEffect(() => {
  processStream();
}); // Missing dependency array
```

### ✅ Proper Cleanup
```typescript
// Correct
useEffect(() => {
  processStream();
  return () => cleanup();
}, [dataStream]);
```

### ❌ Blocking onFinish
```typescript
// Wrong - blocks stream
onFinish: async ({ response }) => {
  await slowDatabaseOperation(); // Blocks response
}
```

### ✅ Non-Blocking onFinish
```typescript
// Correct - use after() for background tasks
onFinish: async ({ response }) => {
  after(async () => {
    await slowDatabaseOperation();
  });
}
```

### ❌ No Error Boundaries
```typescript
// Wrong - crashes app
return <DataStreamHandler id={id} />;
```

### ✅ Error Boundaries
```typescript
// Correct
<ErrorBoundary fallback={<ErrorMessage />}>
  <DataStreamHandler id={id} />
</ErrorBoundary>
```

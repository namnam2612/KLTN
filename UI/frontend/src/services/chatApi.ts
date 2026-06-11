export interface AskSource {
  file: string;
  source_file: string;
  page: number;
  category: string;
  sub_category: string;
  id: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  sources: AskSource[];
}

export interface CreateMessageResponse {
  answer: string;
  conversation_id: string;
}

export async function askQuestion(
  baseUrl: string,
  question: string
): Promise<AskResponse> {
  const response = await fetch(`${baseUrl}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error ${response.status}: ${errorText}`);
  }

  return response.json();
}

export async function saveAskedMessage(
  baseUrl: string,
  userId: string,
  content: string,
  answer: string,
  conversationId?: string | number | null
): Promise<CreateMessageResponse> {
  const response = await fetch(`${baseUrl}/api/asked-messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId,
    },
    body: JSON.stringify({
      content,
      answer,
      conversation_id: conversationId || null,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error ${response.status}: ${errorText}`);
  }

  return response.json();
}

export async function createMessageAuto(
  baseUrl: string,
  userId: string,
  content: string
): Promise<CreateMessageResponse> {
  const response = await fetch(`${baseUrl}/api/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId,
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error ${response.status}: ${errorText}`);
  }

  return response.json();
}

export async function createMessageInConversation(
  baseUrl: string,
  userId: string,
  conversationId: string | number,
  content: string
): Promise<CreateMessageResponse> {
  const response = await fetch(`${baseUrl}/api/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId,
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error ${response.status}: ${errorText}`);
  }

  return response.json();
}

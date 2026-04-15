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

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await fetch("http://127.0.0.1:8010/ask", {
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
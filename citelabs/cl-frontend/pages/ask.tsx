import { useState, useEffect, useRef } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';
const USER_ID = process.env.NEXT_PUBLIC_USER_ID || 'user_1'; // For v1: simple user ID

type Message = {
  message_id?: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  tokens_in?: number;
  tokens_out?: number;
  model_used?: string;
  citations?: Array<{
    url: string;
    domain_type?: string;
    chunk_id?: number;
    relevance_score?: number;
  }>;
};

type Session = {
  session_id: string;
  title: string | null;
  scope: string;
  message_count: number;
  last_message_at: string;
  run_id: string | null;
};

type Scope = 'sandbox_only' | 'sandbox_competitors' | 'web_only';

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState<Scope>('sandbox_only');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [showSessions, setShowSessions] = useState(false);
  const [usage, setUsage] = useState<{ tokens_used: number; tokens_limit: number } | null>(null);
  const [runIdInput, setRunIdInput] = useState('');
  const [showRunIdInput, setShowRunIdInput] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadSessions();
    loadUsage();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
        headers: {
          'X-User-Id': USER_ID,
        },
      });
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const loadUsage = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/usage?period=today`, {
        headers: {
          'X-User-Id': USER_ID,
        },
      });
      const data = await response.json();
      setUsage(data);
    } catch (error) {
      console.error('Failed to load usage:', error);
    }
  };

  const createSession = async (runId?: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': USER_ID,
        },
        body: JSON.stringify({
          scope,
          run_id: runId,
        }),
      });
      const data = await response.json();
      setSessionId(data.session_id);
      setMessages([]);
      setShowSessions(false);
      loadSessions();
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create session');
    }
  };

  const loadSession = async (sid: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sid}`, {
        headers: {
          'X-User-Id': USER_ID,
        },
      });
      const data = await response.json();
      setSessionId(sid);
      setMessages(data.messages || []);
      setScope(data.scope as Scope);
      setShowSessions(false);
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || loading) return;

    const messageContent = input.trim();
    const userMessage: Message = {
      role: 'user',
      content: messageContent,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': USER_ID,
        },
        body: JSON.stringify({
          content: messageContent,
        }),
      });

      if (response.status === 402) {
        const errorData = await response.json();
        alert(`Quota exceeded: ${errorData.quota_used}/${errorData.quota_limit} tokens used`);
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const assistantMessage: Message = {
        message_id: data.message_id,
        role: 'assistant',
        content: data.content,
        tokens_in: data.tokens_in,
        tokens_out: data.tokens_out,
        model_used: data.model_used,
        citations: data.citations,
        created_at: data.created_at,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      loadUsage();
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const router = useRouter();

  return (
    <>
      <Head>
        <title>Chat - CiteLabs</title>
        <meta name="description" content="Ask questions about your sandbox content" />
      </Head>
      <main className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 text-white">
        {/* Animated Background */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-pink-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
        </div>

        <div className="relative z-10 flex h-screen">
          {/* Sidebar */}
          <div className={`w-64 bg-gray-800/50 backdrop-blur-lg border-r border-gray-700 ${showSessions ? '' : 'hidden md:block'}`}>
            <div className="p-4 border-b border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">Chat Sessions</h2>
                <button
                  onClick={() => router.push('/')}
                  className="text-gray-400 hover:text-white text-sm"
                >
                  ← Home
                </button>
              </div>
              {!showRunIdInput ? (
                <button
                  onClick={() => setShowRunIdInput(true)}
                  className="w-full px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold rounded-lg shadow-lg transform hover:scale-105 transition-all duration-200"
                >
                  New Chat
                </button>
              ) : (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={runIdInput}
                    onChange={(e) => setRunIdInput(e.target.value)}
                    placeholder="Enter run_id (e.g., run_123...)"
                    className="w-full px-3 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        if (runIdInput.trim()) {
                          createSession(runIdInput.trim());
                          setRunIdInput('');
                          setShowRunIdInput(false);
                        }
                      }}
                      className="flex-1 px-3 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold rounded-lg text-sm"
                    >
                      Create
                    </button>
                    <button
                      onClick={() => {
                        setShowRunIdInput(false);
                        setRunIdInput('');
                      }}
                      className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
            <div className="overflow-y-auto h-[calc(100vh-120px)]">
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  onClick={() => loadSession(session.session_id)}
                  className={`p-3 border-b border-gray-700 cursor-pointer hover:bg-gray-700/50 transition-colors ${
                    sessionId === session.session_id ? 'bg-blue-600/20 border-blue-500' : ''
                  }`}
                >
                  <div className="font-medium text-sm truncate text-white">
                    {session.title || 'Untitled Chat'}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {session.message_count} messages • {session.scope}
                  </div>
                </div>
              ))}
            </div>
          </div>

      {/* Main Chat Area */}
          <div className="flex-1 flex flex-col bg-gray-900/30 backdrop-blur-sm">
        {/* Header */}
            <div className="bg-gray-800/50 backdrop-blur-lg border-b border-gray-700 p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowSessions(!showSessions)}
                  className="md:hidden px-3 py-2 border border-gray-600 rounded-lg bg-gray-700/50 hover:bg-gray-700 text-white"
            >
              Sessions
            </button>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 bg-clip-text text-transparent">Chat</h1>
          </div>
          <div className="flex items-center gap-4">
            {/* Scope Toggle */}
            <div className="flex gap-2">
              <button
                onClick={() => setScope('sandbox_only')}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                  scope === 'sandbox_only'
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                    : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700 border border-gray-600'
                }`}
              >
                🏠 Sandbox
              </button>
              <button
                onClick={() => setScope('sandbox_competitors')}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                  scope === 'sandbox_competitors'
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                    : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700 border border-gray-600'
                }`}
              >
                🏠+🏢 Both
              </button>
              <button
                disabled
                className="px-3 py-1 rounded-lg text-sm bg-gray-700/30 text-gray-500 cursor-not-allowed border border-gray-700"
                title="Coming soon"
              >
                🌐 Web
              </button>
            </div>
            {/* Usage Display */}
            {usage && (
              <div className="text-sm text-gray-300 bg-gray-800/50 px-3 py-1 rounded-lg border border-gray-700">
                <span className="text-purple-400">{usage.tokens_used.toLocaleString()}</span>
                <span className="text-gray-500"> / </span>
                <span className="text-blue-400">{usage.tokens_limit.toLocaleString()}</span>
                <span className="text-gray-500 ml-1">tokens</span>
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!sessionId ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-gray-400 mb-4 text-lg">No active chat session</p>
                <p className="text-gray-500 mb-4 text-sm">Create a session with a sandbox run_id to start chatting</p>
                <button
                  onClick={() => setShowRunIdInput(true)}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold rounded-lg shadow-lg transform hover:scale-105 transition-all duration-200"
                >
                  Start New Chat
                </button>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-400 text-lg">Start a conversation...</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-3xl rounded-lg p-4 ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                      : 'bg-gray-800/50 backdrop-blur-lg border border-gray-700 text-gray-100'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.role === 'assistant' && (
                    <div className="mt-2 text-xs text-gray-400">
                      {msg.tokens_in && msg.tokens_out && (
                        <span>
                          {msg.tokens_in + msg.tokens_out} tokens • {msg.model_used}
                        </span>
                      )}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-2">
                          <details className="cursor-pointer">
                            <summary className="text-purple-400 hover:text-purple-300 transition-colors">
                              {msg.citations.length} citation{msg.citations.length > 1 ? 's' : ''}
                            </summary>
                            <div className="mt-2 space-y-1">
                              {msg.citations.map((cit, i) => (
                                <a
                                  key={i}
                                  href={cit.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="block text-xs text-blue-400 hover:text-blue-300 transition-colors truncate"
                                >
                                  {cit.url} {cit.relevance_score && `(${(cit.relevance_score * 100).toFixed(0)}%)`}
                                </a>
                              ))}
                            </div>
                          </details>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800/50 backdrop-blur-lg border border-gray-700 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="bg-gray-800/50 backdrop-blur-lg border-t border-gray-700 p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Type your message..."
              className="flex-1 px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
              disabled={!sessionId || loading}
            />
            <button
              onClick={sendMessage}
              disabled={!sessionId || loading || !input.trim()}
              className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold rounded-lg shadow-lg transform hover:scale-105 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
      </main>
    </>
  );
}


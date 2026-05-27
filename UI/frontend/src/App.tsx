/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { 
  Plus, 
  History, 
  // Settings, 
  User, 
  Lightbulb, 
  Code2, 
  FileEdit, 
  Sparkles, 
  ThumbsUp, 
  ThumbsDown, 
  Copy, 
  RefreshCw, 
  PlusCircle, 
  Mic, 
  Send,
  Info,
  Share2,
  Bookmark,
  Loader2,
  Menu,
  X,
  LogOut,
  Shield
} from 'lucide-react';
import { createMessageAuto, createMessageInConversation } from './services/chatApi';
import { motion, AnimatePresence } from 'motion/react';
import { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import Admin from './Admin';
import { useAuth } from './context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Message {
  role: 'user' | 'model';
  content: string;
}

interface Conversation {
  id: number | string;
  title: string;
  updatedAt?: string;
}

export default function App() {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | string | null>(null);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);

  const [view, setView] = useState<'chat' | 'admin'>('chat');
  const [knowledgeBase, setKnowledgeBase] = useState<Array<{
    name: string;
    type: string;
    size: number;
    uploadedAt: string;
    content?: string;
  }>>([]);
  const [chatUserId] = useState(() => {
    const stored = localStorage.getItem('chatUserId');
    if (stored && /^\d+$/.test(stored)) {
      return stored;
    }
    const generated = String(Math.floor(Date.now() / 1000));
    localStorage.setItem('chatUserId', generated);
    return generated;
  });

  const apiHeaders = {
    'Content-Type': 'application/json',
    'X-User-Id': chatUserId,
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadConversations = async (preferActiveId?: number | string | null) => {
    setIsLoadingConversations(true);
    try {
      const response = await fetch(`${API_URL}/api/conversations`, {
        headers: apiHeaders,
      });
      const data = await response.json();
      const list = Array.isArray(data) ? data : (data?.conversations || []);

      setConversations(list);
      if (preferActiveId !== undefined && preferActiveId !== null) {
        setActiveConversationId(preferActiveId);
      } else if (list.length > 0) {
        setActiveConversationId(list[0].id);
      }
    } catch (error) {
      console.error('Load conversations error:', error);
    } finally {
      setIsLoadingConversations(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversation = async (conversationId: number | string) => {
    setActiveConversationId(conversationId);
    try {
      const response = await fetch(`${API_URL}/api/conversations/${conversationId}/messages`, {
        headers: apiHeaders,
      });
      const data = await response.json();
      const list = Array.isArray(data) ? data : (Array.isArray(data?.messages) ? data.messages : []);
      const normalized = list.map((item: any) => ({
        role: item.role === 'model' ? 'model' : 'user',
        content: item.content || ''
      }));
      setMessages(normalized);
    } catch (error) {
      console.error('Load conversation detail error:', error);
    }
  };

  const handleRenameConversation = (conversationId: number | string) => {
    const current = conversations.find(item => item.id === conversationId);
    const nextTitle = window.prompt('Rename conversation', current?.title || '');
    if (!nextTitle?.trim()) return;

    setConversations(prev => prev.map(item => item.id === conversationId ? { ...item, title: nextTitle.trim() } : item));
  };

  const handleDeleteConversation = (conversationId: number | string) => {
    setConversations(prev => prev.filter(item => item.id !== conversationId));
    if (activeConversationId === conversationId) {
      setActiveConversationId(null);
      setMessages([]);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isTyping) return;

    const currentInput = input;
    setInput('');

    const userMessage: Message = { role: 'user', content: currentInput };
    setMessages(prev => [...prev, userMessage]);

    setIsTyping(true);

    try {
      const data = activeConversationId
        ? await createMessageInConversation(API_URL, chatUserId, activeConversationId, currentInput)
        : await createMessageAuto(API_URL, chatUserId, currentInput);

      const answer = data.answer || 'Không có câu trả lời từ hệ thống.';
      const nextConversationId = data.conversation_id || activeConversationId;

      if (nextConversationId) {
        setActiveConversationId(nextConversationId);
      }

      let aiContent = '';
      setMessages(prev => [...prev, { role: 'model', content: '' }]);

      for (let i = 0; i < answer.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 15));
        aiContent += answer[i];

        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            role: 'model',
            content: aiContent
          };
          return newMessages;
        });
      }

      await loadConversations(nextConversationId ?? undefined);
    } catch (error) {
      console.error('API Error:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'model',
          content: 'Đã có lỗi khi gọi backend AI.'
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  
  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
  };

  return (
    <div className="flex min-h-screen bg-background text-on-surface font-body overflow-hidden">
      {/* Hamburger Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-4 left-4 z-50 p-2 text-on-surface hover:bg-surface-container rounded-lg transition-colors"
      >
        {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* SideNavBar (Drawer) */}
      <motion.aside
        animate={{ width: sidebarOpen ? 280 : 80 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="fixed left-0 top-0 h-full z-40 flex flex-col p-4 bg-surface-container rounded-r-2xl pt-20"
      >
        <div className="mb-8 px-2">
          <h2 className={`font-headline text-lg font-bold text-on-surface transition-all duration-300 ${sidebarOpen ? 'opacity-100' : 'opacity-0 hidden'}`}>Conversations</h2>
          <p className={`text-xs text-on-surface-variant opacity-50 transition-all duration-300 ${sidebarOpen ? '' : 'hidden'}`}>AI Assistant</p>
        </div>
        
        <motion.button 
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => { setMessages([]); setView('chat'); setActiveConversationId(null); }}
          className={`mb-6 flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-br from-primary to-primary-container text-on-primary-container font-headline font-bold rounded-xl shadow-lg shadow-primary/10 transition-all duration-300 ${sidebarOpen ? 'w-full' : 'w-12'}`}
        >
          <Plus className="w-4 h-4" />
          <span className={`transition-all duration-300 ${sidebarOpen ? 'opacity-100' : 'opacity-0 hidden'}`}>New Chat</span>
        </motion.button>

        <nav className="flex-1 space-y-2 overflow-y-auto pr-2 custom-scrollbar">
          <div className={`flex items-center gap-2 px-3 text-xs uppercase tracking-wide text-on-surface-variant/70 ${sidebarOpen ? '' : 'hidden'}`}>
            <History className="w-4 h-4" />
            Conversations
          </div>

          {isLoadingConversations && (
            <div className={`text-on-surface-variant p-3 text-sm ${sidebarOpen ? '' : 'hidden'}`}>
              Loading...
            </div>
          )}

          {!isLoadingConversations && conversations.length === 0 && (
            <div className={`text-on-surface-variant p-3 text-sm ${sidebarOpen ? '' : 'hidden'}`}>
              No conversations yet.
            </div>
          )}

          {conversations.map((item) => (
            <div
              key={item.id}
              onClick={() => loadConversation(item.id)}
              className={`group flex items-center gap-3 p-3 rounded-lg transition-all duration-300 cursor-pointer ${activeConversationId === item.id ? 'bg-surface-container-high text-primary' : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'}`}
            >
              <span className={`text-sm font-medium truncate transition-all duration-300 ${sidebarOpen ? 'opacity-100' : 'opacity-0 hidden'}`}>
                {item.title || 'Untitled'}
              </span>
              {sidebarOpen && (
                <div className="ml-auto flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleRenameConversation(item.id);
                    }}
                    className="text-on-surface-variant hover:text-on-surface"
                    aria-label="Rename"
                  >
                    ✏️
                  </button>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleDeleteConversation(item.id);
                    }}
                    className="text-on-surface-variant hover:text-red-400"
                    aria-label="Delete"
                  >
                    🗑️
                  </button>
                </div>
              )}
            </div>
          ))}

          {user?.role === 'admin' && (
            <div onClick={() => setView('admin')} className={`text-on-surface-variant hover:bg-surface-container-high ${view === 'admin' ? 'bg-surface-container-high text-primary' : ''} hover:text-on-surface p-3 flex items-center gap-3 rounded-lg transition-all duration-300 cursor-pointer`}>
              <Shield className="w-5 h-5 shrink-0" />
              <span className={`text-sm font-medium transition-all duration-300 ${sidebarOpen ? 'opacity-100' : 'opacity-0 hidden'}`}>Admin Panel</span>
            </div>
          )}
        </nav>

        <div className="mt-auto space-y-3 p-2">
          <div className={`flex items-center gap-3 p-2 rounded-xl bg-surface-container-high/50 transition-all duration-300 ${sidebarOpen ? '' : 'justify-center'}`}>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-primary-container flex items-center justify-center overflow-hidden shrink-0">
              <span className="text-on-primary-container font-bold text-sm">{user?.email?.charAt(0).toUpperCase() || 'U'}</span>
            </div>
            <div className={`overflow-hidden transition-all duration-300 ${sidebarOpen ? '' : 'hidden'}`}>
              <p className="text-sm font-bold text-on-surface truncate">{user?.email || 'User'}</p>
              <p className="text-[10px] text-on-surface-variant capitalize">{user?.role === 'admin' ? '🔐 Admin' : '👤 User'}</p>
            </div>
          </div>
          
          <motion.button
            whileHover={{ scale: sidebarOpen ? 1.02 : 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={logout}
            className={`w-full flex items-center justify-center gap-2 py-2 px-3 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30 rounded-lg transition-all duration-300 font-headline font-semibold text-sm`}
          >
            <LogOut className="w-4 h-4" />
            <span className={`transition-all duration-300 ${sidebarOpen ? 'opacity-100' : 'opacity-0 hidden'}`}>Logout</span>
          </motion.button>
        </div>
      </motion.aside>

      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 md:hidden"
        />
      )}

      {/* Main Content Canvas */}
      <main className={`flex-1 min-h-screen flex flex-col bg-surface-container-low relative transition-all duration-300 ${sidebarOpen ? 'ml-[280px]' : 'ml-20'}`}>
        {view === 'admin' ? (
          <Admin knowledgeBase={knowledgeBase} setKnowledgeBase={setKnowledgeBase} onBack={() => setView('chat')} />
        ) : (
          <div className="flex-1 flex flex-col min-h-screen w-full relative">
            {/* TopNavBar */}
            <header className={`fixed top-0 right-0 z-50 flex justify-between items-center px-8 py-4 bg-background/70 backdrop-blur-xl transition-all duration-300 ${sidebarOpen ? 'left-[280px]' : 'left-20'}`}>
          <div className="flex items-center gap-4">
            <span className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-br from-primary to-primary-container font-headline">
              Thăng Long Chatbot
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            <button className="text-on-surface-variant hover:text-on-surface transition-all">
              <User className="w-6 h-6" />
            </button>
          </div>
        </header>

        {/* Message Container */}
        <div className="flex-1 overflow-y-auto px-8 py-12 max-w-5xl mx-auto w-full flex flex-col gap-16 custom-scrollbar">
          <AnimatePresence>
            {messages.length === 0 && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                className="py-12 flex flex-col items-start max-w-2xl"
              >
                <h1 className="font-headline text-5xl font-extrabold tracking-tight mb-6 text-transparent bg-clip-text bg-gradient-to-r from-primary via-tertiary to-primary leading-tight">
                  Tôi là Chatbot hỗ trợ sinh viên
                </h1>
                <p className="text-on-surface-variant text-lg leading-relaxed font-medium mb-12">
                  Tôi có thể giúp bạn giải đáp thắc mắc về quy chế đào tạo thế nào?
                </p>

                {/* Bento Prompt Suggestions */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
                  {[
                    { icon: Lightbulb, color: 'text-primary', title: 'Quy đổi điểm', desc: 'Các quy đổi điểm IELTS.' },
                    { icon: Code2, color: 'text-tertiary', title: 'Thủ tục bảo lưu', desc: 'Hướng dẫn cách làm thủ tục bảo lưu học phần.' },
                    { icon: FileEdit, color: 'text-secondary', title: 'Cách đăng ký học phần', desc: 'Hướng dẫn cách đăng ký học phần.' }
                  ].map((item, i) => (
                    <motion.div 
                      key={i}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 * i, duration: 0.5 }}
                      whileHover={{ y: -4 }}
                      onClick={() => handleSuggestionClick(item.desc)}
                      className="p-6 rounded-2xl bg-surface-container-high hover:bg-surface-variant transition-all cursor-pointer group border border-white/5"
                    >
                      <item.icon className={`${item.color} mb-4 w-6 h-6`} />
                      <p className="text-sm font-headline font-bold text-on-surface mb-2">{item.title}</p>
                      <p className="text-xs text-on-surface-variant leading-relaxed">{item.desc}</p>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Thread */}
          <div className="space-y-12 pb-32">
            {messages.map((msg, idx) => (
              <motion.div 
                key={idx}
                initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex ${msg.role === 'user' ? 'flex-col items-end' : 'items-start gap-6'} w-full`}
              >
                {msg.role === 'model' && (
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary-container flex items-center justify-center shrink-0 shadow-lg shadow-primary/20">
                    <Sparkles className="text-on-primary-container w-5 h-5" />
                  </div>
                )}
                <div className={`flex-1 ${msg.role === 'user' ? 'max-w-[80%] bg-secondary-container text-on-secondary-container px-6 py-4 rounded-2xl rounded-br-sm shadow-sm' : 'max-w-[90%]'}`}>
                  {msg.role === 'model' && idx === messages.length - 1 && isTyping && msg.content === '' && (
                    <div className="loom-progress w-24 mb-6 rounded-full opacity-50"></div>
                  )}
                  <div className={`prose prose-invert max-w-none text-on-surface space-y-4 font-body leading-relaxed ${msg.role === 'model' ? 'text-lg' : 'text-base font-medium'}`}>
                    <Markdown>{msg.content}</Markdown>
                  </div>
                  {msg.role === 'model' && msg.content !== '' && (
                    <div className="flex gap-6 mt-8">
                      <button className="text-on-surface-variant hover:text-primary transition-colors"><ThumbsUp className="w-4 h-4" /></button>
                      <button className="text-on-surface-variant hover:text-primary transition-colors"><ThumbsDown className="w-4 h-4" /></button>
                      <button className="text-on-surface-variant hover:text-primary transition-colors"><Copy className="w-4 h-4" /></button>
                      <button className="text-on-surface-variant hover:text-primary transition-colors"><RefreshCw className="w-4 h-4" /></button>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Floating Message Input */}
        <div className={`fixed bottom-8 right-0 flex flex-col items-center px-8 pointer-events-none transition-all duration-300 ${sidebarOpen ? 'left-[280px]' : 'left-20'}`}>
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-4xl glass rounded-full p-2 flex items-center gap-3 pointer-events-auto"
          >
            <button className="p-3 text-on-surface-variant hover:text-primary transition-colors">
              <PlusCircle className="w-6 h-6" />
            </button>
              <input 
                className="flex-1 bg-transparent border-none focus:ring-0 text-on-surface font-body py-3 px-2 placeholder:text-on-surface-variant/40 text-lg disabled:opacity-50" 
                placeholder={isTyping ? "Vui lòng đợi..." : "Message Ethereal AI..."} 
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                disabled={isTyping}
              />
            <div className="flex items-center gap-2 pr-2">
              <button className="p-3 text-on-surface-variant hover:text-primary transition-colors">
                <Mic className="w-6 h-6" />
              </button>
              <motion.button 
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSendMessage}
                disabled={isTyping}
                className={`p-3 rounded-full transition-all ${isTyping ? 'bg-surface-variant text-on-surface-variant cursor-not-allowed' : 'bg-primary text-on-primary hover:shadow-[0_0_20px_rgba(173,198,255,0.4)]'}`}
              >
                {isTyping ? <Loader2 className="w-6 h-6 animate-spin" /> : <Send className="w-6 h-6" />}
              </motion.button>
            </div>
          </motion.div>
        </div>

        {/* Right Side Context Bar */}
        <div className="fixed right-8 top-1/2 -translate-y-1/2 flex flex-col gap-8 opacity-40 hover:opacity-100 transition-opacity duration-300">
          <button className="text-on-surface-variant hover:text-primary transition-colors"><Info className="w-5 h-5" /></button>
          <button className="text-on-surface-variant hover:text-primary transition-colors"><Share2 className="w-5 h-5" /></button>
          <button className="text-on-surface-variant hover:text-primary transition-colors"><Bookmark className="w-5 h-5" /></button>
        </div>
        </div>
        )}
      </main>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #343536;
          border-radius: 10px;
        }
        
        .prose strong {
          color: var(--color-primary);
        }
        .prose code {
          color: var(--color-tertiary);
          background: var(--color-surface-container-high);
          padding: 0.2em 0.4em;
          border-radius: 0.3em;
        }
      `}</style>
    </div>
  );
}
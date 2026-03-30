import { useState } from 'react';
import { motion } from 'motion/react';
import { Plus, Trash2, ArrowLeft, RefreshCw, Save } from 'lucide-react';

interface AdminProps {
  knowledgeBase: string[];
  setKnowledgeBase: React.Dispatch<React.SetStateAction<string[]>>;
  onBack: () => void;
}

export default function Admin({ knowledgeBase, setKnowledgeBase, onBack }: AdminProps) {
  const [newEntry, setNewEntry] = useState('');

  const handleAdd = () => {
    if (!newEntry.trim()) return;
    setKnowledgeBase(prev => [newEntry, ...prev]);
    setNewEntry('');
  };

  const handleDelete = (index: number) => {
    setKnowledgeBase(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="flex-1 min-h-screen bg-surface-container-low text-on-surface flex flex-col items-center pt-24 px-8 pb-12 overflow-y-auto">
      <div className="w-full max-w-4xl space-y-8">
        
        {/* Header */}
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="p-3 bg-surface-container-high hover:bg-surface-variant rounded-full transition-colors mb-2"
          >
            <ArrowLeft className="w-6 h-6 text-on-surface" />
          </button>
          <div>
            <h1 className="text-4xl font-headline font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-primary to-tertiary">
              Admin Control Panel
            </h1>
            <p className="text-on-surface-variant mt-2 text-lg">Quản lý kho dữ liệu câu trả lời cho Chatbot</p>
          </div>
        </div>

        {/* Add New Data Form */}
        <div className="bg-surface-container rounded-3xl p-8 border border-white/5 shadow-xl">
          <h2 className="text-xl font-headline font-bold mb-6 flex items-center gap-3">
            <Plus className="text-primary w-6 h-6" /> Thêm văn bản mới
          </h2>
          <textarea 
            className="w-full h-32 bg-background/50 border border-white/10 rounded-xl p-4 text-on-surface font-body outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none placeholder:text-on-surface-variant/50"
            placeholder="Nhập nội dung dữ liệu chatbot sẽ sử dụng để trả lời..."
            value={newEntry}
            onChange={(e) => setNewEntry(e.target.value)}
          />
          <div className="flex justify-end mt-4">
            <motion.button 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleAdd}
              className="flex items-center gap-2 px-6 py-3 bg-primary text-on-primary font-bold rounded-xl shadow-[0_0_20px_rgba(173,198,255,0.2)] hover:shadow-[0_0_20px_rgba(173,198,255,0.5)] transition-all"
            >
              <Save className="w-5 h-5" /> Thêm Dữ Liệu
            </motion.button>
          </div>
        </div>

        {/* Database List */}
        <div className="bg-surface-container rounded-3xl p-8 border border-white/5 shadow-xl">
          <h2 className="text-xl font-headline font-bold mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <RefreshCw className="text-secondary w-6 h-6" /> 
              Kho Dữ Liệu Hiện Tại 
              <span className="bg-surface-variant text-on-surface-variant text-sm px-3 py-1 rounded-full font-bold ml-2">
                {knowledgeBase.length}
              </span>
            </div>
          </h2>
          
          <div className="space-y-4">
            {knowledgeBase.length === 0 ? (
              <p className="text-on-surface-variant text-center py-8 italic bg-background/30 rounded-xl border border-dashed border-white/10">
                Chưa có dữ liệu nào trong hệ thống.
              </p>
            ) : (
              knowledgeBase.map((entry, index) => (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={index} 
                  className="group flex gap-4 p-5 bg-background border border-white/5 rounded-2xl hover:border-primary/30 transition-colors items-start"
                >
                  <div className="w-8 h-8 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center font-bold font-headline shrink-0 mt-1">
                    {knowledgeBase.length - index}
                  </div>
                  <p className="flex-1 text-on-surface leading-relaxed whitespace-pre-wrap">
                    {entry}
                  </p>
                  <button 
                    onClick={() => handleDelete(index)}
                    className="p-3 text-error/70 hover:text-error hover:bg-error/10 rounded-xl transition-colors shrink-0 opacity-0 group-hover:opacity-100"
                    title="Xóa dữ liệu này"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </motion.div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

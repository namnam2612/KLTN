import { useState, useRef } from 'react';
import { motion } from 'motion/react';
import { Plus, Trash2, ArrowLeft, RefreshCw, Save, Upload, File, FileText, AlertCircle } from 'lucide-react';

interface KnowledgeFile {
  name: string;
  type: string;
  size: number;
  uploadedAt: string;
  content?: string;
}

interface AdminProps {
  knowledgeBase: KnowledgeFile[];
  setKnowledgeBase: React.Dispatch<React.SetStateAction<KnowledgeFile[]>>;
  onBack: () => void;
}

function getFileExtension(fileName: string): string {
  return fileName.split('.').pop()?.toLowerCase() || '';
}

export default function Admin({ knowledgeBase, setKnowledgeBase, onBack }: AdminProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;

    setError('');
    setIsUploading(true);

    for (const file of Array.from(files)) {
      const extension = getFileExtension(file.name);
      const allowedExtensions = ['pdf', 'doc', 'docx'];
      if (!allowedExtensions.includes(extension)) {
        setError('Chỉ hỗ trợ file PDF hoặc Word (.docx, .doc)');
        continue;
      }

      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setError('Kích thước file không được vượt quá 10MB');
        continue;
      }

      const newFile: KnowledgeFile = {
        name: file.name,
        type: file.type || extension,
        size: file.size,
        uploadedAt: new Date().toLocaleString('vi-VN'),
      };

      setKnowledgeBase(prev => [newFile, ...prev]);
    }

    setIsUploading(false);
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDelete = (index: number) => {
    setKnowledgeBase(prev => prev.filter((_, i) => i !== index));
  };

  const getFileIcon = (fileType: string) => {
    if (fileType.includes('pdf')) {
      return <FileText className="w-5 h-5 text-red-400" />;
    }
    return <File className="w-5 h-5 text-blue-400" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
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
            <Plus className="text-primary w-6 h-6" /> Tải lên tài liệu
          </h2>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3"
            >
              <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
              <p className="text-sm text-red-300">{error}</p>
            </motion.div>
          )}

          <label className="block">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileSelect}
              className="hidden"
            />
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => !isUploading && fileInputRef.current?.click()}
              className="w-full p-8 bg-gradient-to-br from-primary/10 to-primary-container/5 border-2 border-dashed border-primary/30 hover:border-primary/60 rounded-2xl cursor-pointer transition-all flex flex-col items-center justify-center gap-3"
            >
              <Upload className="w-8 h-8 text-primary" />
              <div className="text-center">
                <p className="text-on-surface font-headline font-bold">
                  {isUploading ? 'Đang tải...' : 'Kéo thả hoặc click để chọn file'}
                </p>
                <p className="text-xs text-on-surface-variant mt-1">
                  PDF hoặc Word (.doc, .docx) - Tối đa 10MB
                </p>
              </div>
            </motion.div>
          </label>

          <div className="flex justify-end mt-4">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                if (knowledgeBase.length === 0) {
                  setError('Vui lòng tải lên ít nhất một tài liệu');
                  return;
                }
                setError('');
              }}
              className="flex items-center gap-2 px-6 py-3 bg-primary text-on-primary font-bold rounded-xl shadow-[0_0_20px_rgba(173,198,255,0.2)] hover:shadow-[0_0_20px_rgba(173,198,255,0.5)] transition-all disabled:opacity-50"
              disabled={knowledgeBase.length === 0}
            >
              <Save className="w-5 h-5" /> Hoàn tất
            </motion.button>
          </div>
        </div>

        {/* Database List */}
        <div className="bg-surface-container rounded-3xl p-8 border border-white/5 shadow-xl">
          <h2 className="text-xl font-headline font-bold mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <RefreshCw className="text-secondary w-6 h-6" /> 
              Tài Liệu Đã Tải Lên
              <span className="bg-surface-variant text-on-surface-variant text-sm px-3 py-1 rounded-full font-bold ml-2">
                {knowledgeBase.length}
              </span>
            </div>
          </h2>
          
          <div className="space-y-4">
            {knowledgeBase.length === 0 ? (
              <p className="text-on-surface-variant text-center py-8 italic bg-background/30 rounded-xl border border-dashed border-white/10">
                Chưa có tài liệu nào được tải lên.
              </p>
            ) : (
              knowledgeBase.map((file, index) => (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={index} 
                  className="group flex gap-4 p-5 bg-background border border-white/5 rounded-2xl hover:border-primary/30 transition-colors items-start"
                >
                  <div className="flex items-center justify-center shrink-0">
                    {getFileIcon(file.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-on-surface font-headline font-semibold truncate">
                      {file.name}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-on-surface-variant">
                      <span>{formatFileSize(file.size)}</span>
                      <span>•</span>
                      <span>{file.uploadedAt}</span>
                    </div>
                  </div>
                  <button 
                    onClick={() => handleDelete(index)}
                    className="p-3 text-error/70 hover:text-error hover:bg-error/10 rounded-xl transition-colors shrink-0 opacity-0 group-hover:opacity-100"
                    title="Xóa tài liệu"
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

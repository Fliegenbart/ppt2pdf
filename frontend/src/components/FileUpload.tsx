import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileIcon, Loader2 } from 'lucide-react';

interface FileUploadProps {
  onUpload: (file: File) => void;
  loading: boolean;
}

export function FileUpload({ onUpload, loading }: FileUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0]);
    }
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    },
    maxFiles: 1,
    disabled: loading,
  });

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border p-8">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Convert PowerPoint to Accessible PDF
          </h2>
          <p className="text-gray-600">
            Upload your PPTX file and let AI enhance its accessibility
          </p>
        </div>

        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
            transition-all duration-200
            ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'}
            ${loading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />

          {loading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
              <p className="text-lg font-medium text-gray-700">
                Processing your file...
              </p>
            </div>
          ) : isDragActive ? (
            <div className="flex flex-col items-center">
              <Upload className="w-12 h-12 text-blue-500 mb-4" />
              <p className="text-lg font-medium text-blue-600">
                Drop your file here
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <FileIcon className="w-8 h-8 text-blue-600" />
              </div>
              <p className="text-lg font-medium text-gray-700 mb-2">
                Drag and drop your PPTX file here
              </p>
              <p className="text-sm text-gray-500 mb-4">
                or click to browse
              </p>
              <button
                type="button"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Select File
              </button>
            </div>
          )}
        </div>

        {acceptedFiles.length > 0 && !loading && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg flex items-center gap-3">
            <FileIcon className="w-5 h-5 text-gray-400" />
            <span className="text-sm text-gray-600">{acceptedFiles[0].name}</span>
            <span className="text-xs text-gray-400">
              ({(acceptedFiles[0].size / 1024 / 1024).toFixed(2)} MB)
            </span>
          </div>
        )}

        {/* Features */}
        <div className="mt-8 grid grid-cols-2 gap-4">
          {[
            { title: 'AI Alt-Text', desc: 'Auto-generate image descriptions' },
            { title: 'Smart Reading Order', desc: 'AI-optimized content flow' },
            { title: 'PDF/UA Compliant', desc: 'Full accessibility standards' },
            { title: 'Contrast Check', desc: 'WCAG color compliance' },
          ].map((feature) => (
            <div key={feature.title} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
              <div>
                <p className="font-medium text-gray-800 text-sm">{feature.title}</p>
                <p className="text-xs text-gray-500">{feature.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

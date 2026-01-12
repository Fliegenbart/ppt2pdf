import { useState, useEffect } from 'react';
import { SlideElement } from '../types';
import { Image, Sparkles, Check, X, Eye } from 'lucide-react';
import axios from 'axios';

interface AltTextEditorProps {
  elements: SlideElement[];
  slideNumber: number;
  onUpdate: (elementId: string, slideNumber: number, altText: string, isDecorative: boolean) => void;
  jobId: string;
}

export function AltTextEditor({ elements, slideNumber, onUpdate, jobId }: AltTextEditorProps) {
  if (elements.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <Image className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>No images on this slide</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Image Alt-Text Editor
        </h3>
        <p className="text-sm text-gray-500">
          {elements.filter(e => e.alt_text || e.is_decorative).length}/{elements.length} images have descriptions
        </p>
      </div>

      <div className="space-y-4">
        {elements.map((element) => (
          <AltTextCard
            key={element.id}
            element={element}
            slideNumber={slideNumber}
            onUpdate={onUpdate}
            jobId={jobId}
          />
        ))}
      </div>
    </div>
  );
}

function AltTextCard({
  element,
  slideNumber,
  onUpdate,
  jobId,
}: {
  element: SlideElement;
  slideNumber: number;
  onUpdate: (elementId: string, slideNumber: number, altText: string, isDecorative: boolean) => void;
  jobId: string;
}) {
  const [altText, setAltText] = useState(element.alt_text || '');
  const [isDecorative, setIsDecorative] = useState(element.is_decorative || false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [saving, setSaving] = useState(false);

  // Load image preview
  useEffect(() => {
    if (element.has_image) {
      axios.get(`/api/job/${jobId}/element/${element.id}/image`)
        .then(res => {
          if (res.data.image_base64) {
            setImageUrl(`data:image/png;base64,${res.data.image_base64}`);
          }
        })
        .catch(() => {});
    }
  }, [element.id, element.has_image, jobId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdate(element.id, slideNumber, altText, isDecorative);
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = altText !== (element.alt_text || '') || isDecorative !== (element.is_decorative || false);

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="flex">
        {/* Image thumbnail */}
        <div className="w-48 h-36 bg-gray-100 flex-shrink-0 relative">
          {imageUrl ? (
            <>
              <img
                src={imageUrl}
                alt="Preview"
                className="w-full h-full object-contain"
              />
              <button
                onClick={() => setShowPreview(true)}
                className="absolute bottom-2 right-2 p-1.5 bg-black/50 text-white rounded hover:bg-black/70 transition-colors"
              >
                <Eye className="w-4 h-4" />
              </button>
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Image className="w-8 h-8 text-gray-300" />
            </div>
          )}
        </div>

        {/* Alt text editor */}
        <div className="flex-1 p-4">
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-gray-700">
                {element.content_type || 'Image'}
                {element.alt_text_generated && (
                  <span className="ml-2 inline-flex items-center gap-1 text-xs text-purple-600">
                    <Sparkles className="w-3 h-3" />
                    AI generated
                  </span>
                )}
              </p>
              <p className="text-xs text-gray-500">ID: {element.id}</p>
            </div>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={isDecorative}
                onChange={(e) => setIsDecorative(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-600">Decorative image</span>
            </label>
          </div>

          {!isDecorative && (
            <div className="space-y-2">
              <textarea
                value={altText}
                onChange={(e) => setAltText(e.target.value)}
                placeholder="Enter alt text description..."
                rows={2}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500">
                  {altText.length} characters
                  {altText.length > 125 && (
                    <span className="text-amber-600 ml-2">
                      Consider shortening (recommended: &lt;125 chars)
                    </span>
                  )}
                </p>
              </div>
            </div>
          )}

          {isDecorative && (
            <p className="text-sm text-gray-500 italic">
              This image will be marked as decorative and skipped by screen readers.
            </p>
          )}

          {hasChanges && (
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={() => {
                  setAltText(element.alt_text || '');
                  setIsDecorative(element.is_decorative || false);
                }}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
              >
                <X className="w-4 h-4 inline mr-1" />
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                <Check className="w-4 h-4 inline mr-1" />
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Image preview modal */}
      {showPreview && imageUrl && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-8"
          onClick={() => setShowPreview(false)}
        >
          <div className="max-w-4xl max-h-full">
            <img
              src={imageUrl}
              alt="Full preview"
              className="max-w-full max-h-[80vh] object-contain"
            />
          </div>
        </div>
      )}
    </div>
  );
}

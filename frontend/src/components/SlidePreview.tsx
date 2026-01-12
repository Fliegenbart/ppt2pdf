import { Slide, SlideElement } from '../types';
import { Image, Type, Table2, BarChart3, Square } from 'lucide-react';

interface SlidePreviewProps {
  slide: Slide;
}

export function SlidePreview({ slide }: SlidePreviewProps) {
  const getElementIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <Image className="w-4 h-4" />;
      case 'text':
        return <Type className="w-4 h-4" />;
      case 'table':
        return <Table2 className="w-4 h-4" />;
      case 'chart':
        return <BarChart3 className="w-4 h-4" />;
      default:
        return <Square className="w-4 h-4" />;
    }
  };

  const sortedElements = [...slide.elements].sort((a, b) => a.reading_order - b.reading_order);

  return (
    <div className="space-y-6">
      {/* Slide Info */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Slide {slide.slide_number}: {slide.title || 'Untitled'}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {slide.elements.length} elements | Reading order confidence:{' '}
            <span className={slide.reading_order_confidence > 0.7 ? 'text-green-600' : 'text-amber-600'}>
              {Math.round(slide.reading_order_confidence * 100)}%
            </span>
          </p>
        </div>
      </div>

      {/* Elements List */}
      <div className="space-y-3">
        <h4 className="font-medium text-gray-700">Content (in reading order):</h4>
        {sortedElements.map((element, index) => (
          <ElementCard key={element.id} element={element} index={index} />
        ))}
      </div>

      {/* Speaker Notes */}
      {slide.speaker_notes && (
        <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <h4 className="font-medium text-amber-800 mb-2">Speaker Notes</h4>
          <p className="text-sm text-amber-700 whitespace-pre-wrap">
            {slide.speaker_notes}
          </p>
        </div>
      )}
    </div>
  );
}

function ElementCard({ element, index }: { element: SlideElement; index: number }) {
  const getElementIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <Image className="w-4 h-4" />;
      case 'text':
        return <Type className="w-4 h-4" />;
      case 'table':
        return <Table2 className="w-4 h-4" />;
      case 'chart':
        return <BarChart3 className="w-4 h-4" />;
      default:
        return <Square className="w-4 h-4" />;
    }
  };

  const getTypeLabel = (type: string, element: SlideElement) => {
    if (type === 'text' && element.heading_level) {
      return `Heading ${element.heading_level}`;
    }
    return type.charAt(0).toUpperCase() + type.slice(1);
  };

  return (
    <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
      {/* Order number */}
      <div className="flex-shrink-0 w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-medium">
        {index + 1}
      </div>

      {/* Icon and type */}
      <div className="flex-shrink-0 flex items-center gap-2 w-24">
        <span className="text-gray-400">{getElementIcon(element.element_type)}</span>
        <span className="text-sm font-medium text-gray-600">
          {getTypeLabel(element.element_type, element)}
        </span>
      </div>

      {/* Content preview */}
      <div className="flex-1 min-w-0">
        {element.element_type === 'text' && element.text && (
          <p className="text-sm text-gray-700 line-clamp-2">{element.text}</p>
        )}

        {element.element_type === 'image' && (
          <div className="space-y-1">
            {element.is_decorative ? (
              <span className="inline-block px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded">
                Decorative
              </span>
            ) : element.alt_text ? (
              <p className="text-sm text-gray-700 italic">"{element.alt_text}"</p>
            ) : (
              <span className="inline-block px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded">
                Missing alt-text
              </span>
            )}
            {element.content_type && (
              <p className="text-xs text-gray-500">Type: {element.content_type}</p>
            )}
          </div>
        )}

        {element.element_type === 'table' && (
          <p className="text-sm text-gray-600">
            {element.table_rows} rows x {element.table_cols} columns
          </p>
        )}

        {element.element_type === 'chart' && (
          <div className="space-y-1">
            <p className="text-sm text-gray-700">{element.chart_title || 'Untitled chart'}</p>
            {element.chart_summary && (
              <p className="text-xs text-gray-500 italic">"{element.chart_summary}"</p>
            )}
          </div>
        )}
      </div>

      {/* Language tag */}
      {element.language && (
        <span className="flex-shrink-0 px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded">
          {element.language}
        </span>
      )}
    </div>
  );
}

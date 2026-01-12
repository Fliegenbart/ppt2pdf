import { useState, useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { SlideElement } from '../types';
import { GripVertical, Image, Type, Table2, BarChart3, Square, Save } from 'lucide-react';

interface ReadingOrderEditorProps {
  elements: SlideElement[];
  slideNumber: number;
  onUpdate: (slideNumber: number, orderedElementIds: string[]) => void;
}

export function ReadingOrderEditor({ elements, slideNumber, onUpdate }: ReadingOrderEditorProps) {
  const [items, setItems] = useState(() =>
    [...elements].sort((a, b) => a.reading_order - b.reading_order)
  );
  const [hasChanges, setHasChanges] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setItems((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
      setHasChanges(true);
    }
  }, []);

  const handleSave = useCallback(() => {
    const orderedIds = items.map((item) => item.id);
    onUpdate(slideNumber, orderedIds);
    setHasChanges(false);
  }, [items, slideNumber, onUpdate]);

  const handleReset = useCallback(() => {
    setItems([...elements].sort((a, b) => a.reading_order - b.reading_order));
    setHasChanges(false);
  }, [elements]);

  if (elements.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No elements on this slide</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Reading Order Editor
          </h3>
          <p className="text-sm text-gray-500">
            Drag items to reorder how screen readers will navigate this slide
          </p>
        </div>

        {hasChanges && (
          <div className="flex gap-2">
            <button
              onClick={handleReset}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            >
              Reset
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Save className="w-4 h-4" />
              Save Order
            </button>
          </div>
        )}
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={items.map(i => i.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-2">
            {items.map((item, index) => (
              <SortableItem key={item.id} element={item} index={index} />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h4 className="font-medium text-blue-800 mb-2">Tips for Reading Order</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>Place titles and headings first</li>
          <li>Group related content together</li>
          <li>Follow natural reading flow (left-to-right, top-to-bottom)</li>
          <li>Place image descriptions near their context</li>
        </ul>
      </div>
    </div>
  );
}

function SortableItem({ element, index }: { element: SlideElement; index: number }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: element.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

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

  const getPreview = (element: SlideElement) => {
    if (element.element_type === 'text' && element.text) {
      return element.text.slice(0, 60) + (element.text.length > 60 ? '...' : '');
    }
    if (element.element_type === 'image') {
      return element.alt_text || (element.is_decorative ? '(Decorative)' : '(No alt-text)');
    }
    if (element.element_type === 'chart') {
      return element.chart_title || 'Chart';
    }
    if (element.element_type === 'table') {
      return `Table (${element.table_rows}x${element.table_cols})`;
    }
    return element.element_type;
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-4 p-4 bg-white rounded-lg border ${
        isDragging ? 'shadow-lg border-blue-400' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      {/* Drag handle */}
      <button
        {...attributes}
        {...listeners}
        className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 cursor-grab active:cursor-grabbing"
      >
        <GripVertical className="w-5 h-5" />
      </button>

      {/* Order number */}
      <div className="flex-shrink-0 w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-medium">
        {index + 1}
      </div>

      {/* Icon and type */}
      <div className="flex-shrink-0 flex items-center gap-2 w-24">
        <span className="text-gray-400">{getElementIcon(element.element_type)}</span>
        <span className="text-sm font-medium text-gray-600 capitalize">
          {element.element_type}
        </span>
      </div>

      {/* Content preview */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-700 truncate">{getPreview(element)}</p>
      </div>

      {/* Heading badge */}
      {element.heading_level && (
        <span className="flex-shrink-0 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">
          H{element.heading_level}
        </span>
      )}
    </div>
  );
}

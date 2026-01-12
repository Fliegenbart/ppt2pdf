import { useState, useEffect, useCallback } from 'react';
import { FileUpload } from './components/FileUpload';
import { ProgressIndicator } from './components/ProgressIndicator';
import { SlidePreview } from './components/SlidePreview';
import { AltTextEditor } from './components/AltTextEditor';
import { ReadingOrderEditor } from './components/ReadingOrderEditor';
import { AccessibilityReport } from './components/AccessibilityReport';
import { useConversion } from './hooks/useConversion';
import { Slide, SlideElement } from './types';
import { FileText, RefreshCw, Download, CheckCircle } from 'lucide-react';

type Step = 'upload' | 'analyzing' | 'edit' | 'converting' | 'complete';

function App() {
  const [step, setStep] = useState<Step>('upload');
  const [selectedSlide, setSelectedSlide] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<'preview' | 'alttext' | 'order' | 'report'>('preview');
  const [includeSpeakerNotes, setIncludeSpeakerNotes] = useState(false);

  const {
    jobId,
    job,
    slides,
    report,
    loading,
    error,
    uploadFile,
    fetchJobStatus,
    startAnalysis,
    fetchSlides,
    fetchReport,
    updateElements,
    startConversion,
    downloadPdf,
    reset,
  } = useConversion();

  // Poll for job status during conversion (analysis is now synchronous)
  useEffect(() => {
    if (!jobId || step !== 'converting') return;

    const interval = setInterval(async () => {
      const status = await fetchJobStatus(jobId);

      if (status.status === 'complete') {
        setStep('complete');
      } else if (status.status === 'error') {
        setStep('upload');
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobId, step, fetchJobStatus]);

  const handleUpload = useCallback(async (file: File) => {
    try {
      const id = await uploadFile(file);
      setStep('analyzing');

      // Analysis is now synchronous
      await startAnalysis(id);
      await fetchSlides(id);
      await fetchReport(id);
      setStep('edit');
    } catch (err) {
      setStep('upload');
    }
  }, [uploadFile, startAnalysis, fetchSlides, fetchReport]);

  const handleUpdateAltText = useCallback(async (elementId: string, slideNumber: number, altText: string, isDecorative: boolean) => {
    if (!jobId) return;
    await updateElements(jobId, [{
      element_id: elementId,
      slide_number: slideNumber,
      alt_text: isDecorative ? undefined : altText,
      is_decorative: isDecorative,
    }]);
    if (jobId) await fetchReport(jobId);
  }, [jobId, updateElements, fetchReport]);

  const handleUpdateReadingOrder = useCallback(async (slideNumber: number, orderedElementIds: string[]) => {
    if (!jobId) return;
    const updates = orderedElementIds.map((id, index) => ({
      element_id: id,
      slide_number: slideNumber,
      reading_order: index,
    }));
    await updateElements(jobId, updates);
  }, [jobId, updateElements]);

  const handleConvert = useCallback(async () => {
    if (!jobId) return;
    setStep('converting');
    try {
      await startConversion(jobId, includeSpeakerNotes);
      setStep('complete');
    } catch (err) {
      setStep('edit');
    }
  }, [jobId, startConversion, includeSpeakerNotes]);

  const handleDownload = useCallback(() => {
    if (!jobId) return;
    downloadPdf(jobId);
  }, [jobId, downloadPdf]);

  const handleReset = useCallback(() => {
    reset();
    setStep('upload');
    setSelectedSlide(1);
    setActiveTab('preview');
  }, [reset]);

  const currentSlide: Slide | undefined = slides.find(s => s.slide_number === selectedSlide);

  const getImageElements = (slide: Slide | undefined): SlideElement[] => {
    if (!slide) return [];
    return slide.elements.filter(e => e.element_type === 'image' || e.element_type === 'chart');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  PPTX to Accessible PDF
                </h1>
                <p className="text-sm text-gray-500">
                  AI-powered accessibility conversion
                </p>
              </div>
            </div>

            {step !== 'upload' && (
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Start Over
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Upload Step */}
        {step === 'upload' && (
          <FileUpload onUpload={handleUpload} loading={loading} />
        )}

        {/* Analyzing Step */}
        {step === 'analyzing' && job && (
          <ProgressIndicator job={job} />
        )}

        {/* Edit Step */}
        {step === 'edit' && slides.length > 0 && (
          <div className="space-y-6">
            {/* Slide Navigation */}
            <div className="bg-white rounded-lg shadow-sm border p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">
                  {job?.presentation?.title || 'Presentation'}
                </h2>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={includeSpeakerNotes}
                      onChange={(e) => setIncludeSpeakerNotes(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    Include speaker notes
                  </label>
                  <button
                    onClick={handleConvert}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Generate PDF
                  </button>
                </div>
              </div>

              <div className="flex gap-2 overflow-x-auto pb-2">
                {slides.map((slide) => (
                  <button
                    key={slide.slide_number}
                    onClick={() => setSelectedSlide(slide.slide_number)}
                    className={`flex-shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedSlide === slide.slide_number
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    Slide {slide.slide_number}
                    {slide.title && (
                      <span className="ml-2 text-xs opacity-75">
                        {slide.title.slice(0, 20)}...
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="border-b">
                <nav className="flex -mb-px">
                  {[
                    { id: 'preview', label: 'Preview' },
                    { id: 'alttext', label: 'Alt Text' },
                    { id: 'order', label: 'Reading Order' },
                    { id: 'report', label: 'Accessibility Report' },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as typeof activeTab)}
                      className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                        activeTab === tab.id
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </nav>
              </div>

              <div className="p-6">
                {activeTab === 'preview' && currentSlide && (
                  <SlidePreview slide={currentSlide} />
                )}

                {activeTab === 'alttext' && currentSlide && (
                  <AltTextEditor
                    elements={getImageElements(currentSlide)}
                    slideNumber={currentSlide.slide_number}
                    onUpdate={handleUpdateAltText}
                    jobId={jobId!}
                  />
                )}

                {activeTab === 'order' && currentSlide && (
                  <ReadingOrderEditor
                    elements={currentSlide.elements}
                    slideNumber={currentSlide.slide_number}
                    onUpdate={handleUpdateReadingOrder}
                  />
                )}

                {activeTab === 'report' && report && (
                  <AccessibilityReport report={report} />
                )}
              </div>
            </div>
          </div>
        )}

        {/* Converting Step */}
        {step === 'converting' && job && (
          <ProgressIndicator job={job} />
        )}

        {/* Complete Step */}
        {step === 'complete' && (
          <div className="bg-white rounded-lg shadow-sm border p-8 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              PDF Generated Successfully!
            </h2>
            <p className="text-gray-600 mb-6">
              Your accessible PDF is ready for download.
            </p>
            <div className="flex justify-center gap-4">
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Download className="w-5 h-5" />
                Download PDF
              </button>
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                <RefreshCw className="w-5 h-5" />
                Convert Another
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

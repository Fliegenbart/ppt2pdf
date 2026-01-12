import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { Job } from '../types';

interface ProgressIndicatorProps {
  job: Job;
}

export function ProgressIndicator({ job }: ProgressIndicatorProps) {
  const steps = [
    { key: 'upload', label: 'Upload', threshold: 10 },
    { key: 'parse', label: 'Parse PPTX', threshold: 30 },
    { key: 'analyze', label: 'AI Analysis', threshold: 70 },
    { key: 'check', label: 'Accessibility Check', threshold: 80 },
    { key: 'generate', label: 'Generate PDF', threshold: 95 },
    { key: 'complete', label: 'Complete', threshold: 100 },
  ];

  const getStepStatus = (threshold: number): 'complete' | 'active' | 'pending' => {
    if (job.progress >= threshold) return 'complete';
    if (job.progress >= threshold - 20) return 'active';
    return 'pending';
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border p-8">
        <div className="text-center mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            {job.status === 'error' ? 'Processing Error' : 'Processing Your Presentation'}
          </h2>
          {job.current_step && (
            <p className="text-gray-600">{job.current_step}</p>
          )}
        </div>

        {job.status === 'error' ? (
          <div className="flex flex-col items-center py-8">
            <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
            <p className="text-red-600 text-center">{job.error_message}</p>
          </div>
        ) : (
          <>
            {/* Progress Bar */}
            <div className="mb-8">
              <div className="flex justify-between text-sm text-gray-500 mb-2">
                <span>Progress</span>
                <span>{Math.round(job.progress)}%</span>
              </div>
              <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full transition-all duration-500"
                  style={{ width: `${job.progress}%` }}
                />
              </div>
            </div>

            {/* Steps */}
            <div className="space-y-4">
              {steps.map((step, index) => {
                const status = getStepStatus(step.threshold);
                return (
                  <div
                    key={step.key}
                    className={`flex items-center gap-4 p-3 rounded-lg transition-colors ${
                      status === 'active' ? 'bg-blue-50' : ''
                    }`}
                  >
                    <div className="flex-shrink-0">
                      {status === 'complete' ? (
                        <CheckCircle className="w-6 h-6 text-green-500" />
                      ) : status === 'active' ? (
                        <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                      ) : (
                        <div className="w-6 h-6 rounded-full border-2 border-gray-300" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p
                        className={`font-medium ${
                          status === 'complete'
                            ? 'text-green-700'
                            : status === 'active'
                            ? 'text-blue-700'
                            : 'text-gray-400'
                        }`}
                      >
                        {step.label}
                      </p>
                    </div>
                    <div className="text-sm text-gray-400">
                      {index + 1}/{steps.length}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

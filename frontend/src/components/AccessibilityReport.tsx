import { AccessibilityReport as Report, AccessibilityIssue } from '../types';
import { CheckCircle, AlertTriangle, AlertCircle, Info, Shield } from 'lucide-react';

interface AccessibilityReportProps {
  report: Report;
}

export function AccessibilityReport({ report }: AccessibilityReportProps) {
  const errorCount = report.issues.filter(i => i.severity === 'error').length;
  const warningCount = report.issues.filter(i => i.severity === 'warning').length;
  const infoCount = report.issues.filter(i => i.severity === 'info').length;

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 90) return 'bg-green-100';
    if (score >= 70) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  return (
    <div className="space-y-6">
      {/* Score Overview */}
      <div className="grid grid-cols-4 gap-4">
        {/* Score */}
        <div className={`p-6 rounded-xl ${getScoreBg(report.score)}`}>
          <p className="text-sm text-gray-600 mb-1">Accessibility Score</p>
          <p className={`text-4xl font-bold ${getScoreColor(report.score)}`}>
            {report.score}
          </p>
          <p className="text-sm text-gray-500 mt-1">out of 100</p>
        </div>

        {/* PDF/UA Status */}
        <div className={`p-6 rounded-xl ${report.pdf_ua_ready ? 'bg-green-100' : 'bg-red-100'}`}>
          <p className="text-sm text-gray-600 mb-1">PDF/UA Compliance</p>
          <div className="flex items-center gap-2">
            {report.pdf_ua_ready ? (
              <>
                <CheckCircle className="w-8 h-8 text-green-600" />
                <span className="text-lg font-semibold text-green-700">Ready</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-8 h-8 text-red-600" />
                <span className="text-lg font-semibold text-red-700">Not Ready</span>
              </>
            )}
          </div>
        </div>

        {/* Image Stats */}
        <div className="p-6 rounded-xl bg-blue-50">
          <p className="text-sm text-gray-600 mb-1">Images with Alt-Text</p>
          <p className="text-4xl font-bold text-blue-600">
            {report.images_with_alt_text}/{report.total_images}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {report.total_images > 0
              ? `${Math.round((report.images_with_alt_text / report.total_images) * 100)}%`
              : 'No images'}
          </p>
        </div>

        {/* Issue Count */}
        <div className="p-6 rounded-xl bg-gray-100">
          <p className="text-sm text-gray-600 mb-1">Total Issues</p>
          <p className="text-4xl font-bold text-gray-700">{report.issues.length}</p>
          <div className="flex gap-2 mt-2 text-xs">
            <span className="text-red-600">{errorCount} errors</span>
            <span className="text-yellow-600">{warningCount} warnings</span>
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-700">{report.total_slides}</p>
          <p className="text-sm text-gray-500">Slides</p>
        </div>
        <div className="text-center border-x">
          <p className="text-2xl font-bold text-gray-700">{report.total_elements}</p>
          <p className="text-sm text-gray-500">Elements</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-700">{report.total_images}</p>
          <p className="text-sm text-gray-500">Images</p>
        </div>
      </div>

      {/* Issues List */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Issues</h3>

        {report.issues.length === 0 ? (
          <div className="text-center py-8 bg-green-50 rounded-lg border border-green-200">
            <Shield className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <p className="text-green-700 font-medium">No accessibility issues found!</p>
            <p className="text-sm text-green-600">Your presentation is ready for conversion.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Group by severity */}
            {errorCount > 0 && (
              <IssueGroup
                title="Errors"
                issues={report.issues.filter(i => i.severity === 'error')}
                severity="error"
              />
            )}
            {warningCount > 0 && (
              <IssueGroup
                title="Warnings"
                issues={report.issues.filter(i => i.severity === 'warning')}
                severity="warning"
              />
            )}
            {infoCount > 0 && (
              <IssueGroup
                title="Information"
                issues={report.issues.filter(i => i.severity === 'info')}
                severity="info"
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function IssueGroup({
  title,
  issues,
  severity,
}: {
  title: string;
  issues: AccessibilityIssue[];
  severity: 'error' | 'warning' | 'info';
}) {
  const colors = {
    error: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: <AlertCircle className="w-5 h-5 text-red-500" />,
      title: 'text-red-700',
    },
    warning: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      icon: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
      title: 'text-yellow-700',
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: <Info className="w-5 h-5 text-blue-500" />,
      title: 'text-blue-700',
    },
  };

  const style = colors[severity];

  return (
    <div className={`rounded-lg border ${style.border} ${style.bg} overflow-hidden`}>
      <div className={`px-4 py-2 border-b ${style.border} flex items-center gap-2`}>
        {style.icon}
        <span className={`font-medium ${style.title}`}>
          {title} ({issues.length})
        </span>
      </div>
      <div className="divide-y divide-gray-200">
        {issues.map((issue, index) => (
          <div key={index} className="px-4 py-3">
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">
                  {issue.message}
                </p>
                {issue.suggestion && (
                  <p className="text-sm text-gray-600 mt-1">
                    Suggestion: {issue.suggestion}
                  </p>
                )}
                <div className="flex gap-4 mt-2 text-xs text-gray-500">
                  <span>Slide {issue.slide_number || 'All'}</span>
                  {issue.element_id && <span>Element: {issue.element_id}</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


import Button from '../../components/base/Button';
import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { getUserAnalyses, getAnalysisById, type BusinessAnalysisResult } from '../../api/business-analyzer';


export default function Results() {

  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);
  const [showWatermarkDropdown, setShowWatermarkDropdown] = useState(false);
  const [watermarkName, setWatermarkName] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Dynamic data state
  const [analysisData, setAnalysisData] = useState<BusinessAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showReasoningTrace, setShowReasoningTrace] = useState(false);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowWatermarkDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch analysis data on component mount
  useEffect(() => {
    const fetchAnalysisData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const stateAnalysis = location.state?.analysis;
        if (stateAnalysis) {
          setAnalysisData(stateAnalysis);
          setIsLoading(false);
          return;
        }

        const analysisId = searchParams.get('id');
        if (analysisId) {
          try {
            const specificAnalysis = await getAnalysisById(parseInt(analysisId));
            if (specificAnalysis) {
              setAnalysisData(specificAnalysis);
            } else {
              setError("Analysis not found. It may have been deleted.");
            }
          } catch (err: any) {
            setError("Analysis not found. It may have been deleted.");
          }
          setIsLoading(false);
          return;
        }

        const analyses = await getUserAnalyses(1);
        if (analyses && analyses.length > 0) {
          setAnalysisData(analyses[0]);
        } else {
          setError("No analysis data found. Please run a business analysis first.");
        }
      } catch (err: any) {
        setError(err.message || "Failed to load analysis data. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalysisData();
  }, [location.state, searchParams]);

  // Enhanced PDF Generation Function
  const generatePDFReport = async (customWatermark?: string) => {
    if (!analysisData) return;

    try {
      setIsGeneratingPDF(true);
      setShowWatermarkDropdown(false);
      const { jsPDF } = await import('jspdf');
      const doc = new jsPDF();

      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const watermark = customWatermark || 'Lavoo';

      // Watermark function with diagonal text
      const addWatermark = (page: number) => {
        doc.setPage(page);
        doc.saveGraphicsState();
        (doc as any).setGState((doc as any).GState({ opacity: 0.1 }));
        doc.setTextColor(249, 115, 22); // Orange
        doc.setFontSize(60);
        doc.setFont('helvetica', 'bold');
        doc.text(watermark, pageWidth / 2, pageHeight / 2, {
          align: 'center',
          angle: 45
        });
        doc.restoreGraphicsState();
      };

      // Page 1: Cover with gradient background
      doc.setFillColor(255, 247, 237); // Light orange background
      doc.rect(0, 0, pageWidth, pageHeight, 'F');

      // Orange header gradient effect
      doc.setFillColor(249, 115, 22);
      doc.rect(0, 0, pageWidth, 80, 'F');

      // Watermark name
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(28);
      doc.setFont('helvetica', 'bold');
      doc.text(watermark, pageWidth / 2, 35, { align: 'center' });

      // Title
      doc.setFontSize(20);
      doc.text('BUSINESS ANALYSIS REPORT', pageWidth / 2, 55, { align: 'center' });

      // Date
      doc.setFontSize(12);
      doc.setFont('helvetica', 'normal');
      doc.text(`Generated: ${new Date().toLocaleDateString()}`, pageWidth / 2, 68, { align: 'center' });

      // Metrics cards
      const {
        bottlenecks = [],
        business_strategies = [],
        ai_confidence_score = 92
      } = analysisData;

      const metrics = [
        { label: 'Bottlenecks', value: bottlenecks.length.toString(), color: [239, 68, 68] },
        { label: 'Solutions', value: business_strategies.length.toString(), color: [34, 197, 94] },
        { label: 'Confidence', value: `${ai_confidence_score}%`, color: [147, 51, 234] },
        { label: 'Projected ROI', value: '$13,900', color: [249, 115, 22] }
      ];

      let yPos = 100;
      metrics.forEach((metric, index) => {
        const xPos = 20 + (index % 2) * 90;
        if (index % 2 === 0 && index > 0) yPos += 45;

        const [r, g, b] = metric.color;
        doc.setFillColor(r, g, b);
        doc.roundedRect(xPos, yPos, 85, 35, 3, 3, 'F');

        doc.setTextColor(255, 255, 255);
        doc.setFontSize(20);
        doc.setFont('helvetica', 'bold');
        doc.text(metric.value, xPos + 42.5, yPos + 15, { align: 'center' });

        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.text(metric.label, xPos + 42.5, yPos + 25, { align: 'center' });
      });

      addWatermark(1);

      // Page 2: Income Diagnosis
      doc.addPage();
      doc.setFillColor(255, 247, 237);
      doc.rect(0, 0, pageWidth, pageHeight, 'F');

      doc.setFillColor(249, 115, 22);
      doc.rect(0, 0, pageWidth, 15, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('INCOME DIAGNOSIS', pageWidth / 2, 10, { align: 'center' });

      yPos = 30;
      doc.setTextColor(31, 41, 55);
      doc.setFontSize(16);
      doc.text('Primary Bottleneck', 20, yPos);

      yPos += 10;
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      const primaryBottleneck = bottlenecks[0];
      doc.text(primaryBottleneck?.title || 'No bottleneck data', 20, yPos);

      yPos += 8;
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      const descLines = doc.splitTextToSize(primaryBottleneck?.description || '', pageWidth - 40);
      doc.text(descLines, 20, yPos);
      yPos += descLines.length * 5 + 10;

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      doc.text('Impact:', 20, yPos);
      doc.setFont('helvetica', 'normal');
      const impactLines = doc.splitTextToSize(primaryBottleneck?.impact || '', pageWidth - 40);
      doc.text(impactLines, 20, yPos + 6);

      addWatermark(2);

      // Page 3: Key Evidence
      doc.addPage();
      doc.setFillColor(255, 247, 237);
      doc.rect(0, 0, pageWidth, pageHeight, 'F');

      doc.setFillColor(249, 115, 22);
      doc.rect(0, 0, pageWidth, 15, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(14);
      doc.text('KEY EVIDENCE', pageWidth / 2, 10, { align: 'center' });

      yPos = 30;
      const keyEvidence = [
        { title: 'Revenue Model Mismatch', desc: 'Expert-level audience converts better to coaching models' },
        { title: 'High Pain-Point Audience', desc: 'Struggling with monetization - high intent' },
        { title: 'Low Production Capacity', desc: 'Currently 10 hours/week - traditional scaling risky' }
      ];

      keyEvidence.forEach((evidence) => {
        doc.setFillColor(254, 243, 199);
        doc.rect(20, yPos - 3, pageWidth - 40, 25, 'F');

        doc.setTextColor(249, 115, 22);
        doc.setFontSize(11);
        doc.setFont('helvetica', 'bold');
        doc.text(evidence.title, 25, yPos + 3);

        doc.setTextColor(75, 85, 99);
        doc.setFontSize(9);
        doc.setFont('helvetica', 'normal');
        const evidenceLines = doc.splitTextToSize(evidence.desc, pageWidth - 50);
        doc.text(evidenceLines, 25, yPos + 10);

        yPos += 35;
      });

      addWatermark(3);

      // Page 4: Ranked Action Plan
      doc.addPage();
      doc.setFillColor(255, 247, 237);
      doc.rect(0, 0, pageWidth, pageHeight, 'F');

      doc.setFillColor(249, 115, 22);
      doc.rect(0, 0, pageWidth, 15, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(14);
      doc.text('RANKED ACTION PLAN', pageWidth / 2, 10, { align: 'center' });

      yPos = 30;
      business_strategies.slice(0, 5).forEach((strategy, index) => {
        if (yPos > 250) {
          addWatermark(doc.internal.pages.length - 1);
          doc.addPage();
          doc.setFillColor(255, 247, 237);
          doc.rect(0, 0, pageWidth, pageHeight, 'F');
          yPos = 20;
        }

        // Priority badge
        doc.setFillColor(249, 115, 22);
        doc.roundedRect(pageWidth - 50, yPos - 3, 30, 8, 2, 2, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(8);
        doc.setFont('helvetica', 'bold');
        doc.text(`PRIORITY ${index + 1}`, pageWidth - 35, yPos + 2, { align: 'center' });

        // Title
        doc.setTextColor(31, 41, 55);
        doc.setFontSize(12);
        doc.text(strategy.title, 20, yPos + 2);
        yPos += 8;

        // Description
        doc.setFontSize(9);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(75, 85, 99);
        const strategyLines = doc.splitTextToSize(strategy.description, pageWidth - 40);
        doc.text(strategyLines, 20, yPos);
        yPos += strategyLines.length * 4 + 15;
      });

      addWatermark(doc.internal.pages.length - 1);

      // Save
      const filename = `${watermark.replace(/\s+/g, '_')}_Business_Analysis_${new Date().toISOString().split('T')[0]}.pdf`;
      doc.save(filename);

      toast.success('Report downloaded');
      setWatermarkName('');
    } catch (error) {
      console.error('PDF Error:', error);
      toast.error('Failed to generate PDF');
    } finally {
      setIsGeneratingPDF(false);
    }
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-orange-500 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Loading Analysis...</h2>
          <p className="text-gray-600">Please wait while we fetch your business analysis</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (error || !analysisData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="ri-error-warning-line text-3xl text-red-600"></i>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {error ? "Error Loading Analysis" : "No Analysis Data"}
          </h2>
          <p className="text-gray-600 mb-6">
            {error || "Please run a business analysis first to see results."}
          </p>
          <div className="flex gap-3 justify-center">
            <Button variant="primary" onClick={() => navigate('/dashboard/analyze')}>
              <i className="ri-add-line mr-2"></i>
              Create New Analysis
            </Button>
            <Button variant="outline" onClick={() => window.location.reload()}>
              <i className="ri-refresh-line mr-2"></i>
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const {
    bottlenecks = [],
    business_strategies: businessStrategies = [],
    ai_tools: aiTools = [],
    ai_confidence_score: aiConfidenceScore = 92
  } = analysisData;

  const primaryBottleneck = bottlenecks[0];
  const actions = businessStrategies.slice(0, 5);

  const keyEvidence = [
    {
      id: 1,
      type: 'Signal',
      title: 'Revenue Model Mismatch',
      description: '"Expert-level/labor" audience only generally convert to coaching models that pay your rates, rather than flat-fee (low-ticket) subscription models.'
    },
    {
      id: 2,
      type: 'Signal',
      title: 'High Pain-Point Audience',
      description: 'Your audience ("struggling with monetization") is in pain and aware of needing support.'
    },
    {
      id: 3,
      type: 'Signal',
      title: 'Low Production Capacity',
      description: 'Currently: 10 hours/week capacity for content. Traditional scaling is risky (both time and financial).'
    }
  ];

  const assumptions = [
    'You have not yet mapped out a high-ticket offer (HTO). The strategy assumes you will design it rather than inherit one.',
    'No concurrent work pipeline as of analysis time.',
    'Any conflicting work will shift the timeline for results.',
    'Assuming 10hr capacity made the current seed vs. growth trade-off ($200/wk revenue for content build vs. pursuit of larger-generating work and program traffic).'
  ];

  const reasoningSteps = [
    'Addresses cognitive shortcut (audience signals): "DON\'t try to generate $200/m, which is impossible to do rapidly (trust & nurturing), vs. reach $5000/m."',
    'The "Safe Creator" is a VEE: illustrated in Business / Podcaster/ Thread platform (often low-LTV, slow-build).',
    'Prioritizing a Hybrid sell (HT or Cohort vs. B2B one-time paid) reflects the sustainable revenue for weeks.',
    'The user has strict time constraints (10h/week). Creating a course takes 10+ hours. Hosting a live cohort needs 6 hours (4-week total).',
    'Accountability lets the user ship fast because: (1) Community tab for deliverables. (2) Technical Skills. (3) Not hosting meta-classes in biz for 3wz. (4) time management.'
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-purple-50 pb-20" style={{ fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      {/* Header / Top Navigation */}
      <div className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-end">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/analysis-history')}
              className="text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors hover:bg-gray-100"
            >
              <i className="ri-history-line mr-1.5"></i>
              History
            </button>

            {/* Download Report with Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onMouseEnter={() => setShowWatermarkDropdown(true)}
                disabled={isGeneratingPDF}
                className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-4 py-1.5 rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all shadow-md hover:shadow-lg text-sm font-semibold flex items-center space-x-2"
              >
                {isGeneratingPDF ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                ) : (
                  <i className="ri-download-2-line"></i>
                )}
                <span>Download Report</span>
              </button>

              {/* Watermark Dropdown */}
              {showWatermarkDropdown && !isGeneratingPDF && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-xl border border-gray-200 p-4 z-50">
                  <div className="mb-3">
                    <label className="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                      Custom Watermark
                    </label>
                    <input
                      type="text"
                      value={watermarkName}
                      onChange={(e) => setWatermarkName(e.target.value)}
                      placeholder="Enter company name..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none"
                    />
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => generatePDFReport('Lavoo')}
                      className="flex-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-semibold transition-colors"
                    >
                      Use Default (Lavoo)
                    </button>
                    <button
                      onClick={() => generatePDFReport(watermarkName || 'Lavoo')}
                      disabled={!watermarkName.trim() && watermarkName !== ''}
                      className="flex-1 px-3 py-2 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white rounded-lg text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Generate PDF
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* LAYER 1: Income Diagnosis */}
        <section className="mb-8">
          <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-t-xl px-5 py-3 flex items-center space-x-2 shadow-md">
            <i className="ri-stethoscope-line text-white text-lg"></i>
            <h2 className="text-white font-bold text-sm tracking-wide">INCOME DIAGNOSIS</h2>
          </div>

          <div className="bg-white border-x border-b border-gray-200 rounded-b-xl p-6 md:p-8 shadow-lg">
            <div className="mb-6">
              <span className="text-xs font-bold text-orange-600 uppercase tracking-wider block mb-2">THE DIAGNOSIS:</span>
              <h3 className="text-xl md:text-2xl font-bold text-gray-900 leading-snug">
                {primaryBottleneck?.description || "You are attempting to monetise a high-value B2B audience with a low-value mass-media model (AdSense)."}
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gradient-to-br from-orange-50 to-white p-5 rounded-lg border border-orange-100">
                <span className="text-xs font-bold text-orange-600 uppercase tracking-wider block mb-2">PRIMARY BOTTLENECK</span>
                <p className="text-base font-bold text-gray-900 mb-2">{primaryBottleneck?.title || "Lack of a Direct High-Ticket Offer"}</p>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {primaryBottleneck?.impact || "You can't scale slow revenue enough (even $1,000/month is hard to reach), because the income per viewer will never grow beyond pennies."}
                </p>
              </div>

              <div className="bg-gradient-to-br from-purple-50 to-white p-5 rounded-lg border border-purple-100">
                <span className="text-xs font-bold text-purple-600 uppercase tracking-wider block mb-2">CONTEXTUAL WHY</span>
                <p className="text-sm text-gray-700 leading-relaxed">
                  With only 10 hours a week, you cannot scale slow volume enough to make revenue. Your CPC could triple eventually ($1.50/hour, vs. $0.50/hour per stream now). But scaling per-viewer income is more efficient than sheer audience volume.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Key Evidence + Confidence Section */}
        <section className="mb-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                <i className="ri-flashlight-line text-orange-500 mr-2"></i>
                Key Evidence
              </h3>

              {keyEvidence.map((evidence) => (
                <div key={evidence.id} className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="inline-block px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-bold rounded uppercase">
                      {evidence.type}
                    </span>
                    <h4 className="font-bold text-gray-900 text-sm">{evidence.title}</h4>
                  </div>
                  <p className="text-sm text-gray-600 leading-relaxed">{evidence.description}</p>
                </div>
              ))}
            </div>

            <div>
              <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 shadow-md">
                <div className="flex items-center space-x-2 mb-4">
                  <i className="ri-pie-chart-line text-orange-600"></i>
                  <h4 className="font-bold text-gray-900 text-sm">Confidence</h4>
                </div>

                <div className="flex justify-center mb-4">
                  <div className="relative w-32 h-32">
                    <svg className="w-32 h-32 transform -rotate-90">
                      <circle cx="64" cy="64" r="56" stroke="#fee2e2" strokeWidth="8" fill="none" />
                      <circle
                        cx="64" cy="64" r="56"
                        stroke="url(#orangeGradient)"
                        strokeWidth="8"
                        fill="none"
                        strokeDasharray={`${2 * Math.PI * 56 * (aiConfidenceScore / 100)} ${2 * Math.PI * 56}`}
                        strokeLinecap="round"
                      />
                      <defs>
                        <linearGradient id="orangeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#f97316" />
                          <stop offset="100%" stopColor="#ea580c" />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-3xl font-bold text-orange-600">{aiConfidenceScore}%</span>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-gray-600 text-center leading-relaxed">
                  Based on your audience signals, time constraints, and competitive positioning, this diagnosis has a {aiConfidenceScore}% accuracy.
                </p>
              </div>

              <div className="bg-gradient-to-br from-orange-50 to-orange-100 border border-orange-200 rounded-lg p-5 shadow-sm">
                <div className="flex items-center space-x-2 mb-3">
                  <i className="ri-alert-line text-orange-600 text-sm"></i>
                  <h4 className="font-bold text-orange-900 text-xs uppercase tracking-wide">Assumptions & Missing Data</h4>
                </div>
                <ul className="space-y-2">
                  {assumptions.map((assumption, idx) => (
                    <li key={idx} className="flex items-start space-x-2 text-xs text-orange-900">
                      <i className="ri-checkbox-blank-circle-fill text-orange-400 text-[6px] mt-1.5 flex-shrink-0"></i>
                      <span className="leading-relaxed">{assumption}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* LAYER 2: Ranked Action Plan */}
        <section className="mb-8">
          <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-t-xl px-5 py-3 flex items-center justify-between shadow-md">
            <div className="flex items-center space-x-2">
              <i className="ri-list-check-2 text-white text-lg"></i>
              <h2 className="text-white font-bold text-sm tracking-wide">RANKED ACTION PLAN</h2>
            </div>
          </div>

          <div className="border-x border-b border-gray-200 rounded-b-xl p-6 bg-white shadow-lg space-y-6">
            {actions.map((action, index) => {
              const hasAITool = aiTools[index];
              const effortLabel = index === 0 ? 'MEDIUM (MOST LEVERAGE)' : index === 1 ? 'LOW (IMMEDIATE)' : 'VERY LOW';
              const eta = index === 0 ? '7-14 DAYS' : index === 1 ? '24 HOURS' : '24-48 HOURS';

              return (
                <div key={action.id} className="border-2 border-gray-200 rounded-xl p-6 hover:border-orange-300 hover:shadow-lg transition-all bg-gradient-to-br from-white to-gray-50">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">
                        EFFORT: {effortLabel}
                      </span>
                      <span className="text-xs font-bold text-orange-600 uppercase tracking-wider">
                        ETA: {eta}
                      </span>
                    </div>
                    <span className="px-3 py-1 bg-gradient-to-r from-orange-500 to-orange-600 text-white text-xs font-bold rounded-full shadow-md">
                      PRIORITY {String(index + 1).padStart(2, '0')}
                    </span>
                  </div>

                  <h3 className="text-lg md:text-xl font-bold text-gray-900 mb-4">
                    {action.title}
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="text-xs font-bold text-orange-600 uppercase tracking-wider mb-3">How to Execute</h4>
                      <ol className="space-y-2">
                        {action.description.split('.').filter(s => s.trim()).slice(0, 4).map((step, idx) => (
                          <li key={idx} className="text-sm text-gray-700 flex items-start">
                            <span className="font-bold text-orange-600 mr-2">{idx + 1}.</span>
                            <span>{step.trim()}.</span>
                          </li>
                        ))}
                      </ol>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-orange-600 uppercase tracking-wider mb-3">Expected Impact</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        Higher revenue potential (~$5000 vs. $0)
                      </p>
                      <div className="space-y-2 text-xs text-gray-600 bg-orange-50 p-3 rounded-lg">
                        <div><span className="font-semibold">SUCCESS METRIC:</span> Build and{index === 0 ? ' launch' : ' validate'}</div>
                        <div><span className="font-semibold">FIRST SIGNAL:</span> {eta}</div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-6 border-t border-gray-200">
                    {hasAITool ? (
                      <div className="bg-gradient-to-r from-orange-50 to-purple-50 rounded-lg p-4 border border-orange-200">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-2">
                              <div className="w-6 h-6 bg-gradient-to-r from-orange-500 to-orange-600 rounded flex items-center justify-center shadow-sm">
                                <span className="text-white text-xs font-bold">{hasAITool.title[0]}</span>
                              </div>
                              <h5 className="font-bold text-gray-900 text-sm">{hasAITool.title}</h5>
                            </div>
                            <p className="text-xs text-gray-600 mb-3">{hasAITool.description}</p>
                          </div>
                          <button
                            onClick={() => hasAITool.website && window.open(hasAITool.website, '_blank')}
                            className="ml-4 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-orange-600 text-white text-xs font-bold rounded hover:from-orange-600 hover:to-orange-700 transition-all whitespace-nowrap shadow-md"
                          >
                            Explore Tool
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
                        <div className="flex items-start space-x-3">
                          <i className="ri-checkbox-circle-line text-green-600 text-lg mt-0.5"></i>
                          <div>
                            <p className="text-sm font-semibold text-gray-900 mb-1">No AI tool is necessary for this step.</p>
                            <p className="text-xs text-gray-600">Manual execution is sufficient and often more effective for this particular action.</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {index === 0 && (
                    <div className="mt-6">
                      <button className="w-full bg-gradient-to-r from-orange-500 to-orange-600 text-white py-3 px-6 rounded-lg font-bold hover:from-orange-600 hover:to-orange-700 transition-all shadow-lg hover:shadow-xl flex items-center justify-center space-x-2">
                        <i className="ri-calendar-check-line"></i>
                        <span>Generate 7-Day Execution Plan</span>
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* REASONING TRACE Section */}
        <section className="mb-8">
          <button
            onClick={() => setShowReasoningTrace(!showReasoningTrace)}
            className="w-full bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 rounded-lg px-5 py-3 flex items-center justify-between transition-all shadow-sm"
          >
            <div className="flex items-center space-x-2">
              <i className="ri-git-branch-line text-gray-600"></i>
              <h2 className="font-semibold text-gray-900 text-sm">Reasoning Trace</h2>
            </div>
            <i className={`ri-arrow-${showReasoningTrace ? 'up' : 'down'}-s-line text-gray-600`}></i>
          </button>

          {showReasoningTrace && (
            <div className="mt-4 bg-white border border-gray-200 rounded-lg p-6 shadow-md">
              <ol className="space-y-3">
                {reasoningSteps.map((step, idx) => (
                  <li key={idx} className="flex items-start space-x-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-full flex items-center justify-center text-xs font-bold shadow-sm">
                      {idx + 1}
                    </span>
                    <p className="text-sm text-gray-700 leading-relaxed flex-1">{step}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

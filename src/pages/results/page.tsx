
import Button from '../../components/base/Button';
import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { getUserAnalyses, getAnalysisById, type BusinessAnalysisResult, type BusinessStrategy } from '../../api/business-analyzer';

interface StrategyCardProps {
  action: BusinessStrategy;
  index: number;
  hasAITool: any;
}

function StrategyCard({ action, index, hasAITool }: StrategyCardProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const steps = action.description.split('.').filter(s => s.trim()).map(s => s.trim() + '.');

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start mb-24 last:mb-0">
      {/* Action Card */}
      <div className="lg:col-span-8 bg-white border border-gray-100 rounded-[2rem] shadow-2xl overflow-hidden group hover:border-orange-200 transition-all duration-500 hover:shadow-orange-100/50">
        <div className="p-10 md:p-14">
          <div className="flex items-center justify-between mb-10">
            <div className="flex items-center space-x-4">
              <span className="bg-orange-600 text-white text-[10px] font-medium px-4 py-1.5 rounded-full uppercase tracking-widest shadow-lg shadow-orange-200">
                Priority {String(index + 1).padStart(2, '0')}
              </span>
              <span className="text-[10px] font-medium text-gray-400 uppercase tracking-[0.2em]">
                {index === 0 ? 'Urgent Implementation' : 'Strategic Phase'}
              </span>
            </div>
          </div>

          <div className="mb-10">
            <div className="text-[10px] font-medium text-orange-600 uppercase tracking-widest mb-3">Focus Area</div>
            <h3 className="text-3xl font-medium text-gray-900 mb-6 group-hover:text-orange-600 transition-colors tracking-tight leading-tight">
              {action.title}
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mb-12">
            <div>
              <div className="text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-4 border-b border-gray-50 pb-3">Strategic Action</div>
              <div className="text-gray-800 leading-relaxed font-medium text-lg">
                Package your expert knowledge into a high-ticket offering that directly addresses the burning pain points of your specific niche audience.
              </div>
            </div>
            <div>
              <div className="text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-4 border-b border-gray-50 pb-3">Strategic Impact</div>
              <div className="text-gray-600 leading-relaxed font-medium">
                This shifts your business from a volume-based commodity model to a value-based premium model, instantly increasing your revenue potential per client.
              </div>
            </div>
          </div>

          <div className="bg-gray-50/50 rounded-3xl p-10 mb-10 border border-gray-100">
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-widest mb-6 flex items-center">
              <i className="ri-navigation-line mr-3 text-sm"></i>
              Step-by-Step Implementation
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-5">
              {steps.slice(0, 6).map((step, idx) => (
                <div key={idx} className="flex items-start text-sm text-gray-700 font-medium">
                  <span className="w-6 h-6 flex-shrink-0 bg-white border border-gray-200 rounded-lg flex items-center justify-center text-[10px] font-medium text-gray-400 mr-4 mt-0.5 shadow-sm">
                    {idx + 1}
                  </span>
                  {step}
                </div>
              ))}
            </div>
          </div>

          {/* AI Tool Recommendation */}
          {hasAITool && (
            <div className="mt-10 pt-10 border-t border-gray-100">
              <div className="text-[10px] font-medium text-purple-600 uppercase tracking-widest mb-6 flex items-center">
                <i className="ri-magic-line mr-3 text-sm"></i>
                AI-Driven Acceleration
              </div>
              <div className="bg-purple-50/50 rounded-3xl p-8 border border-purple-100 flex flex-col md:flex-row items-center gap-8">
                <div className="w-20 h-20 bg-white rounded-2xl shadow-xl flex items-center justify-center border border-purple-50 flex-shrink-0">
                  <span className="text-3xl font-medium text-purple-600">{hasAITool.title[0]}</span>
                </div>
                <div className="flex-1 text-center md:text-left">
                  <h5 className="font-medium text-purple-900 text-xl mb-1">{hasAITool.title}</h5>
                  <p className="text-sm text-purple-800/60 mb-4 font-medium">Helpful for {hasAITool.description.split('.')[0]}.</p>
                  <div className="flex flex-wrap justify-center md:justify-start gap-3">
                    <span className="px-3 py-1 bg-white rounded-full text-[10px] font-medium text-purple-500 border border-purple-100 shadow-sm uppercase tracking-widest">CONTENT GENERATION</span>
                    <span className="px-3 py-1 bg-white rounded-full text-[10px] font-medium text-purple-500 border border-purple-100 shadow-sm uppercase tracking-widest">AUDIENCE ANALYSIS</span>
                  </div>
                </div>
                <button
                  onClick={() => hasAITool.website && window.open(hasAITool.website, '_blank')}
                  className="px-8 py-3.5 bg-purple-600 text-white rounded-2xl text-xs font-medium shadow-xl shadow-purple-200 hover:bg-purple-700 transition-all flex-shrink-0 uppercase tracking-widest"
                >
                  Explore Tool
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Context / Roadmap Sidebar */}
      <div className="lg:col-span-4 space-y-8">
        <div className="bg-orange-950 rounded-[2rem] p-10 text-white shadow-2xl relative overflow-hidden group/roadmap">
          <div className="absolute top-0 right-0 p-6 opacity-10 group-hover/roadmap:scale-110 transition-transform duration-700">
            <i className="ri-rocket-line text-8xl"></i>
          </div>
          <div className="relative z-10">
            <div className="text-[10px] font-medium uppercase tracking-[0.3em] text-orange-400 mb-6 opacity-80">Execution Timeline</div>
            <h4 className="text-2xl font-medium mb-8 tracking-tight">7-Day Sprint</h4>

            <div className="space-y-6 mb-12">
              <div className="flex items-center gap-5 group/item cursor-default">
                <div className="w-2.5 h-2.5 rounded-full bg-orange-500 shadow-lg shadow-orange-500/50"></div>
                <div className="text-sm font-medium opacity-80 group-hover/item:opacity-100 transition-opacity">Identify 3 core expertise areas</div>
              </div>
              <div className="flex items-center gap-5 group/item cursor-default">
                <div className="w-2.5 h-2.5 rounded-full bg-orange-500 shadow-lg shadow-orange-500/50"></div>
                <div className="text-sm font-medium opacity-80 group-hover/item:opacity-100 transition-opacity">Define target client avatar</div>
              </div>
              <div className="flex items-center gap-5 group/item cursor-default">
                <div className="w-2.5 h-2.5 rounded-full bg-orange-400 opacity-50"></div>
                <div className="text-sm font-medium opacity-60 group-hover/item:opacity-100 transition-opacity">Draft value proposition</div>
              </div>
            </div>

            <div className="relative">
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="w-full bg-orange-500 text-white py-4 px-8 rounded-2xl font-medium text-[10px] uppercase tracking-[0.2em] hover:bg-orange-600 transition-all shadow-xl shadow-orange-900/20 flex items-center justify-center gap-3"
              >
                <i className="ri-settings-4-fill text-sm"></i>
                Optimize with {hasAITool ? hasAITool.title : 'AI Tool'}
                <i className={`ri-arrow-${isDropdownOpen ? 'up' : 'down'}-s-line text-lg ml-1`}></i>
              </button>

              {isDropdownOpen && (
                <div className="absolute bottom-full left-0 right-0 mb-4 bg-white rounded-3xl shadow-2xl p-6 text-gray-900 border border-gray-100 z-50 animate-in fade-in zoom-in-95 duration-300">
                  <div className="text-[10px] font-medium text-orange-600 uppercase tracking-widest mb-4 border-b border-gray-50 pb-3">Growth Strategies</div>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4">
                      <div className="w-6 h-6 bg-orange-50 rounded-lg flex items-center justify-center text-orange-600 flex-shrink-0 shadow-sm">
                        <i className="ri-speed-mini-line text-xs font-bold"></i>
                      </div>
                      <div className="text-[11px] leading-relaxed text-gray-600">
                        <span className="font-medium text-gray-900 block mb-0.5">Rapid Prototyping</span>
                        Use the tool to generate 5 variations of your offer in 15 minutes.
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="w-6 h-6 bg-orange-50 rounded-lg flex items-center justify-center text-orange-600 flex-shrink-0 shadow-sm">
                        <i className="ri-search-eye-line text-xs font-bold"></i>
                      </div>
                      <div className="text-[11px] leading-relaxed text-gray-600">
                        <span className="font-medium text-gray-900 block mb-0.5">Audience Testing</span>
                        Simulate audience response to different pricing models.
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white border border-gray-100 rounded-3xl p-8 shadow-xl">
          <div className="text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-3 flex items-center">
            <i className="ri-information-line mr-2 text-sm"></i>
            Strategic Note
          </div>
          <p className="text-[11px] text-gray-500 leading-relaxed italic font-medium">
            This plan specifically excludes traditional ad-spend strategies and complex technical builds that would exceed your current 10-hour weekly capacity.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function Results() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
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

  // Fetch analysis data
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
              setError("Analysis not found");
            }
          } catch (err: any) {
            setError("Analysis not found");
          }
          setIsLoading(false);
          return;
        }

        const analyses = await getUserAnalyses(1);
        if (analyses && analyses.length > 0) {
          setAnalysisData(analyses[0]);
        } else {
          setError("No analysis data found");
        }
      } catch (err: any) {
        setError(err.message || "Failed to load analysis data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalysisData();
  }, [location.state, searchParams]);

  // PDF Generation (Enhanced, uses dynamic data)
  const generatePDFReport = async (customWatermark: string = 'Lavoo') => {
    if (!analysisData) return;

    try {
      setShowWatermarkDropdown(false);
      const { jsPDF } = await import('jspdf');
      const doc = new jsPDF();
      const pageWidth = doc.internal.pageSize.getWidth();

      // Simple report generation for now
      doc.setFontSize(22);
      doc.text("Business Analysis Report", pageWidth / 2, 40, { align: 'center' });
      doc.setFontSize(12);
      doc.text(`Generated for: ${customWatermark}`, pageWidth / 2, 50, { align: 'center' });

      doc.save(`analysis-report-${(analysisData as any).id || 'selected'}.pdf`);
      toast.success('Report downloaded');
    } catch (error) {
      toast.error('Failed to generate PDF');
    } finally {
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-orange-500 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900">Loading Analysis...</h2>
        </div>
      </div>
    );
  }

  if (error || !analysisData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="ri-error-warning-line text-3xl text-red-600"></i>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Analysis</h2>
          <Button variant="primary" onClick={() => navigate('/dashboard/analyze')}>
            Create New Analysis
          </Button>
        </div>
      </div>
    );
  }

  const {
    bottlenecks = [],
    business_strategies: businessStrategies = [],
    ai_tools: aiTools = [],
    ai_confidence_score: aiConfidenceScore = 92,
  } = analysisData;

  const primaryBottleneck = bottlenecks[0];
  const secondaryBottlenecks = bottlenecks.slice(1);
  const reasoningSteps = [
    'Addresses cognitive shortcut: "DON\'t try to generate $200/m rapidly vs. reach $5000/m"',
    'The "Safe Creator" is a VEE: illustrated in Business / Podcaster / Thread platforms',
    'Prioritizing a Hybrid sell reflects the sustainable revenue for weeks',
    'User has strict time constraints (10h/week). Creating a course takes 10+ hours',
    'Accountability lets the user ship fast because of direct outcome focus'
  ];

  return (
    <div className="min-h-screen bg-gray-50 pb-20" style={{ fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="text-orange-600 font-medium text-xl flex items-center cursor-pointer" onClick={() => navigate('/dashboard')}>
              <i className="ri-flashlight-fill mr-2"></i>
              Lavoo
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/analysis-history')}
              className="text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors hover:bg-gray-100"
            >
              <i className="ri-history-line mr-1.5"></i>
              History
            </button>

            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setShowWatermarkDropdown(!showWatermarkDropdown)}
                className="bg-orange-500 text-white px-4 py-1.5 rounded-lg hover:bg-orange-600 transition-all shadow-md text-sm font-semibold flex items-center space-x-2"
              >
                <i className="ri-download-2-line"></i>
                <span>Download Report</span>
              </button>

              {showWatermarkDropdown && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-2xl border border-gray-100 p-6 z-50">
                  <div className="mb-4">
                    <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-2">Watermark Name</label>
                    <input
                      type="text"
                      value={watermarkName}
                      onChange={(e) => setWatermarkName(e.target.value)}
                      placeholder="e.g. Acme Corp"
                      className="w-full px-4 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                  <button
                    onClick={() => generatePDFReport(watermarkName)}
                    className="w-full bg-orange-500 text-white py-2 rounded-lg text-xs font-medium uppercase tracking-widest hover:bg-orange-600 transition-all"
                  >
                    Generate PDF
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Banner */}
        <div className="bg-orange-600 rounded-[2rem] p-10 mb-12 text-white shadow-2xl flex flex-col md:flex-row items-center justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -mr-32 -mt-32"></div>
          <div className="relative z-10 mb-6 md:mb-0">
            <h1 className="text-3xl md:text-5xl font-medium mb-4 uppercase tracking-tighter leading-tight">
              Growth blocked by {bottlenecks.length} Key Constraints
            </h1>
            <p className="text-orange-100 opacity-90 text-lg font-medium">
              Precision analysis triggered by current ecosystem signals.
            </p>
          </div>
          <div className="relative z-10">
            <div className="bg-white/20 backdrop-blur-xl p-6 rounded-3xl border border-white/20 shadow-2xl">
              <div className="text-[10px] font-medium uppercase tracking-widest text-orange-100 mb-2">AI Engine Confidence</div>
              <div className="text-5xl font-medium tracking-tighter">{aiConfidenceScore}%</div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 mb-20">
          <div className="lg:col-span-8">
            <div className="bg-white rounded-[2.5rem] border border-gray-100 shadow-[0_20px_50px_rgba(0,0,0,0.05)] overflow-hidden h-full flex flex-col">
              <div className="bg-orange-50/50 px-10 py-5 border-b border-orange-100/50 flex items-center justify-between">
                <div className="flex items-center text-orange-800 font-medium uppercase tracking-[0.2em] text-[10px]">
                  <i className="ri-stethoscope-line mr-3 text-lg text-orange-600"></i>
                  primary bottleneck
                </div>
                <div className="bg-orange-600 text-white text-[10px] font-medium py-2 px-6 rounded-full uppercase tracking-widest shadow-lg shadow-orange-200">
                  fix this first
                </div>
              </div>
              <div className="p-12 md:p-16 flex-1">
                <div className="mb-6">
                  <span className="text-xs font-medium text-orange-600 uppercase tracking-[0.3em]">Critical Strategic Priority</span>
                </div>
                <h2 className="text-4xl font-medium text-gray-900 mb-10 leading-tight tracking-tight">
                  {primaryBottleneck?.title}
                </h2>
                <div className="text-2xl text-gray-600 leading-relaxed mb-12 font-medium">
                  {primaryBottleneck?.description}
                </div>

                <div className="grid grid-cols-1 gap-8">
                  <div className="bg-gray-50/50 border border-gray-100 p-10 rounded-3xl">
                    <div className="text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-6 border-b border-gray-100 pb-4">Execution Impact</div>
                    <div className="text-gray-900 font-medium leading-relaxed text-lg">
                      {primaryBottleneck?.impact}
                    </div>
                  </div>
                  <div className="bg-orange-50/50 border border-orange-100 p-10 rounded-3xl">
                    <div className="text-[10px] font-medium text-orange-600 uppercase tracking-widest mb-6 border-b border-orange-100 pb-4">Strategic Recommendation</div>
                    <div className="text-gray-900 font-medium leading-relaxed text-lg">
                      Focus all resources on high-ticket conversion before mass-market scaling.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-4 flex flex-col gap-8">
            <div className="bg-white rounded-[2rem] border border-gray-100 shadow-xl p-10">
              <div className="flex items-center text-gray-900 font-medium uppercase tracking-[0.2em] text-[10px] mb-10 border-b border-gray-50 pb-6">
                <i className="ri-error-warning-line mr-3 text-orange-500 text-lg"></i>
                secondary constraints
              </div>
              <div className="space-y-10">
                {secondaryBottlenecks.length > 0 ? (
                  secondaryBottlenecks.map((b, i) => (
                    <div key={i} className="flex gap-6 group">
                      <div className="flex-shrink-0 w-12 h-12 bg-gray-50 border border-gray-100 rounded-2xl flex items-center justify-center font-medium text-gray-400 group-hover:bg-orange-50 group-hover:text-orange-500 transition-all duration-300 shadow-sm">
                        {String(i + 2).padStart(2, '0')}
                      </div>
                      <div>
                        <div className="font-medium text-gray-900 mb-1.5 text-base tracking-tight">{b.title}</div>
                        <div className="text-xs text-gray-500 leading-relaxed font-medium">{b.description}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-gray-400 text-xs italic text-center py-12">No significant secondary constraints.</div>
                )}
              </div>
            </div>

            <div className="bg-red-50/50 rounded-[2rem] border border-red-100 shadow-sm p-10">
              <div className="flex items-center text-red-700 font-medium uppercase tracking-[0.2em] text-[10px] mb-6">
                <i className="ri-close-circle-line mr-3 text-lg"></i>
                Business Efficiency Focus
              </div>
              <div className="text-red-900 font-medium text-2xl mb-4 tracking-tight">Stop This Now</div>
              <p className="text-sm text-red-800/70 leading-relaxed font-medium">
                Stop mass-market content distribution. It drains capacity without equivalent high-ticket ROI.
              </p>
            </div>
          </div>
        </div>

        {/* Action Plan Section */}
        <section className="mt-32">
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-16 gap-8">
            <div>
              <h2 className="text-5xl font-medium text-gray-900 mb-6 uppercase tracking-tighter">Execution Roadmap</h2>
              <div className="h-2.5 w-40 bg-orange-500 rounded-full shadow-lg shadow-orange-200"></div>
            </div>
            <div className="flex items-center bg-white border border-gray-100 px-8 py-4 rounded-[1.5rem] text-[10px] font-medium text-gray-500 uppercase tracking-[0.3em] shadow-sm">
              <i className="ri-list-check-2 mr-4 text-orange-500 text-lg"></i>
              {businessStrategies.length} Phase Delivery Strategy
            </div>
          </div>

          <div className="space-y-4">
            {businessStrategies.map((action, index) => (
              <StrategyCard
                key={action.id}
                action={action}
                index={index}
                hasAITool={aiTools[index]}
              />
            ))}
          </div>
        </section>

        {/* Reasoning Trace */}
        <section className="mt-32">
          <button
            onClick={() => setShowReasoningTrace(!showReasoningTrace)}
            className="group w-full flex items-center justify-between border-t border-gray-200 pt-16"
          >
            <div className="flex items-center gap-8">
              <div className="w-20 h-20 bg-gray-50 rounded-[1.5rem] flex items-center justify-center text-gray-400 group-hover:bg-orange-50 group-hover:text-orange-500 transition-all duration-300 shadow-sm">
                <i className="ri-node-tree text-4xl"></i>
              </div>
              <div className="text-left">
                <h3 className="text-3xl font-medium text-gray-900 uppercase tracking-tight">Why we recommended this</h3>
                <p className="text-base text-gray-500 font-medium">Explore the logic behind your custom strategy</p>
              </div>
            </div>
            <div className="w-16 h-16 rounded-full border border-gray-100 flex items-center justify-center group-hover:border-orange-200 group-hover:bg-orange-100/50 transition-all duration-300">
              <i className={`ri-arrow-${showReasoningTrace ? 'up' : 'down'}-s-line text-3xl text-gray-400 group-hover:text-orange-600`}></i>
            </div>
          </button>

          {showReasoningTrace && (
            <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10 animate-in fade-in slide-in-from-top-10 duration-700">
              {reasoningSteps.map((step, idx) => (
                <div key={idx} className="bg-white border border-gray-100 p-10 rounded-[2rem] shadow-sm hover:shadow-2xl transition-all duration-500 hover:-translate-y-2">
                  <div className="w-12 h-12 bg-orange-100 rounded-2xl flex items-center justify-center text-orange-600 font-medium text-base mb-8 shadow-inner">
                    {String(idx + 1).padStart(2, '0')}
                  </div>
                  <p className="text-gray-700 leading-relaxed font-medium text-lg">
                    {step}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="fixed bottom-12 right-12 z-50">
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="w-16 h-16 bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl flex items-center justify-center text-gray-400 hover:text-orange-600 border border-gray-100 transition-all hover:-translate-y-2 group"
        >
          <i className="ri-arrow-up-line text-3xl group-hover:scale-110 transition-transform"></i>
        </button>
      </div>
    </div>
  );
}

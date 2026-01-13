
import Button from '../../components/base/Button';
import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { getUserAnalyses, getAnalysisById, type BusinessAnalysisResult, type BusinessStrategy } from '../../api/business-analyzer';

interface StrategyCardProps {
  action: BusinessStrategy;
  index: number;
  hasAITool: any;
  effort?: string;
}

function StrategyCard({ action, index, hasAITool, effort = 'Low' }: StrategyCardProps) {
  const steps = action.description.split('.').filter(s => s.trim()).map(s => s.trim() + '.');

  return (
    <div className="bg-white border border-gray-100 rounded-[2rem] shadow-2xl overflow-hidden group hover:border-orange-200 transition-all duration-500 hover:shadow-orange-100/50 mb-12 last:mb-0">
      <div className="p-10 md:p-14">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-3 flex-1 min-w-0">
            <span className="w-8 h-8 bg-orange-600 text-white rounded-full flex items-center justify-center font-bold text-sm shadow-lg shadow-orange-200 flex-shrink-0">
              {index + 1}
            </span>
            <h3 className="text-sm font-bold text-gray-900 group-hover:text-orange-600 transition-colors tracking-tight leading-tight truncate uppercase tracking-widest">
              {action.title}
            </h3>
          </div>
          <div className="flex items-center space-x-2 ml-4 flex-shrink-0">
            <span className="bg-orange-50 text-orange-700 text-[10px] font-bold px-3 py-1.5 rounded-lg uppercase tracking-widest border border-orange-100 italic whitespace-nowrap">
              Effort: {effort}
            </span>
          </div>
        </div>

        <div className="space-y-8 mb-10">
          <div>
            <div className="flex flex-col space-y-2">
              <div className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 rounded-full bg-gray-900"></div>
                <div className="text-sm font-bold text-gray-900 uppercase tracking-widest">What to do:</div>
              </div>
              <div className="text-gray-700 leading-relaxed font-medium text-base overflow-hidden" style={{ maxHeight: '3rem', display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2 }}>
                {action.description.split('.')[0]}.
              </div>
            </div>
          </div>
          <div>
            <div className="flex flex-col space-y-2">
              <div className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 rounded-full bg-gray-900"></div>
                <div className="text-sm font-bold text-gray-900 uppercase tracking-widest">Why this matters:</div>
              </div>
              <div className="text-gray-600 leading-relaxed font-medium text-base overflow-hidden" style={{ maxHeight: '3rem', display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2 }}>
                {steps[1] || "This represents the highest leverage move for your current business stage."}
              </div>
            </div>
          </div>
        </div>

        {/* AI Tool Recommendation */}
        {hasAITool && (
          <div className="mt-10 pt-10 border-t border-gray-100">
            <div className="text-sm font-bold text-orange-600 uppercase tracking-[0.2em] mb-8 flex items-center">
              <i className="ri-flashlight-fill mr-3 text-lg"></i>
              OPTIONAL AI ACCELERATION
            </div>
            <div className="bg-orange-50/30 rounded-3xl p-10 border border-orange-100/50">
              <div className="space-y-8">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-base font-bold text-gray-900 uppercase tracking-tight">Tool Name:</span>
                    <span className="ml-2 text-xl font-black text-orange-600 tracking-tight">{hasAITool.title}</span>
                  </div>
                  {hasAITool.website && (
                    <a
                      href={hasAITool.website.startsWith('http') ? hasAITool.website : `https://${hasAITool.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-4 py-2 bg-orange-100 text-orange-700 text-[10px] font-bold rounded-lg uppercase tracking-widest hover:bg-orange-600 hover:text-white transition-all shadow-sm group-hover:scale-105 active:scale-95"
                    >
                      Explore
                      <i className="ri-external-link-line"></i>
                    </a>
                  )}
                </div>
                <div>
                  <div className="text-base font-bold text-gray-900 mb-2 uppercase tracking-tight">What it helps with:</div>
                  <p className="text-gray-700 leading-relaxed font-medium text-base overflow-hidden" style={{ maxHeight: '3rem', display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2 }}>
                    {hasAITool.description}
                  </p>
                </div>
                <div>
                  <div className="text-base font-bold text-gray-900 mb-2 uppercase tracking-tight">Why this tool:</div>
                  <p className="text-gray-700 leading-relaxed font-medium text-base overflow-hidden" style={{ maxHeight: '3rem', display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2 }}>
                    {hasAITool.pros?.[0] || `Built specifically for rapid ${hasAITool.title[0]} generation with minimal technical overhead.`}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {!hasAITool && (
          <div className="mt-10 pt-10 border-t border-gray-100">
            <div className="text-sm font-bold text-orange-600 uppercase tracking-[0.2em] mb-4 flex items-center">
              <i className="ri-flashlight-fill mr-3 text-lg"></i>
              OPTIONAL AI ACCELERATION
            </div>
            <p className="text-gray-500 italic text-sm font-medium">No AI tool is necessary for this step. Manual execution is sufficient.</p>
          </div>
        )}
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
  const [inspirationalMessage, setInspirationalMessage] = useState('');

  const motivationalQuotes = [
    "You are not behind. You are just early in the sequence.",
    "Precision beats speed when the direction is right.",
    "Focus on the bottleneck, and the rest becomes noise.",
    "Growth is a series of solved problems. You're on the next one.",
    "The best time to optimize was yesterday. The second best time is NOW."
  ];

  useEffect(() => {
    setInspirationalMessage(motivationalQuotes[Math.floor(Math.random() * motivationalQuotes.length)]);
  }, []);

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
        <div className="bg-orange-700 rounded-[2rem] p-10 mb-12 text-white shadow-2xl flex flex-col md:flex-row items-center justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -mr-32 -mt-32"></div>
          <div className="relative z-10 mb-6 md:mb-0">
            <h1 className="text-3xl md:text-5xl font-medium mb-4 uppercase tracking-tighter leading-tight">
              Your growth is being slowed down by <span className="font-extrabold text-white">{bottlenecks.length} critical bottlenecks</span>
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
            <div className="bg-white rounded-[2.5rem] border border-gray-100 shadow-[0_20px_50px_rgba(0,0,0,0.05)] overflow-hidden flex flex-col">
              <div className="p-12 md:p-16 bg-green-50/40">
                <div className="flex flex-col">
                  <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-6">
                      <div className="w-16 h-16 bg-orange-100 rounded-2xl flex items-center justify-center text-orange-500 shadow-inner">
                        <i className="ri-lightbulb-flash-line text-4xl"></i>
                      </div>
                      <h2 className="text-xl font-bold text-gray-900 uppercase tracking-widest">Primary Bottleneck</h2>
                    </div>
                    <div className="bg-orange-600 text-white text-[10px] font-bold py-2 px-6 rounded-full uppercase tracking-widest shadow-lg shadow-orange-200">
                      fix this first
                    </div>
                  </div>

                  <div className="mb-8">
                    <h3 className="text-4xl font-black text-orange-600 tracking-tighter leading-tight mb-4">
                      {primaryBottleneck?.title || "Operational Constraint"}
                    </h3>
                    <div className="text-lg text-gray-600 leading-relaxed font-medium">
                      {primaryBottleneck?.description}
                    </div>
                  </div>

                  <div className="mt-10 pt-10 border-t border-gray-100/50">
                    <div className="flex items-center gap-3 mb-4">
                      <i className="ri-error-warning-line text-orange-500 text-lg"></i>
                      <div className="text-[10px] font-bold text-gray-900 uppercase tracking-widest">Consequence if ignored</div>
                    </div>
                    <p className="text-gray-600 font-medium leading-relaxed text-lg">
                      {primaryBottleneck?.impact || "Your current growth plateau will persist, leading to wasted resources and missed market opportunities."}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 bg-white rounded-[2.5rem] border border-gray-100 shadow-[0_20px_50px_rgba(0,0,0,0.05)] overflow-hidden p-12 md:p-16">
              <div className="flex items-center gap-6 mb-8">
                <div className="w-16 h-16 bg-orange-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-orange-200">
                  <i className="ri-flashlight-fill text-4xl"></i>
                </div>
                <h2 className="text-xl font-bold text-gray-900 uppercase tracking-widest">Strategic Priority</h2>
              </div>
              <p className="text-3xl font-extrabold text-gray-900 tracking-tighter leading-tight">
                {businessStrategies[0]?.description || "Execute the primary action plan item to resolve the core bottleneck."}
              </p>
            </div>
          </div>

          <div className="lg:col-span-4 flex flex-col gap-8">
            <div className="bg-white rounded-[2rem] border border-gray-100 shadow-xl p-10">
              <div className="flex items-center text-gray-900 font-medium uppercase tracking-[0.2em] text-sm mb-10 border-b border-gray-50 pb-6">
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
                        <div className="font-bold text-gray-900 mb-1.5 text-base tracking-tight">{b.title}</div>
                        <div className="text-xs text-gray-500 leading-relaxed font-medium">
                          {b.description !== b.title ? b.description : "Secondary priority addressed after implementation of the primary solution."}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-gray-400 text-xs italic text-center py-12">No significant secondary constraints.</div>
                )}
              </div>
            </div>

            <div className="bg-white border border-gray-100 rounded-[2rem] shadow-xl p-10">
              <div className="flex items-center text-red-600 font-bold uppercase tracking-[0.3em] text-[10px] mb-6">
                <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center mr-4 shadow-sm border border-red-200/50">
                  <i className="ri-prohibited-fill text-2xl text-red-600"></i>
                </div>
                STOP
              </div>
              <p className="text-base text-gray-500 leading-relaxed font-medium">
                Stop wasting time on broad promotions that aren't translating into sales; they are not effective and won't change your revenue situation.
              </p>
            </div>
          </div>
        </div>

        {/* Action Plan Section */}
        <section className="mt-32">
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-16 gap-8">
            <div>
              <h2 className="text-5xl font-bold text-gray-900 mb-4 uppercase tracking-tighter">Ranked Action Plan</h2>
              <p className="text-gray-500 font-medium text-lg">These actions are ordered by leverage. Do them in sequence.</p>
            </div>
            <div className="flex items-center bg-white border border-gray-100 px-8 py-4 rounded-[1.5rem] text-[10px] font-medium text-gray-500 uppercase tracking-[0.3em] shadow-sm">
              <i className="ri-list-check-2 mr-4 text-orange-500 text-lg"></i>
              {businessStrategies.length} Phase Delivery Strategy
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
            <div className="lg:col-span-8 space-y-4">
              {businessStrategies.map((action, index) => (
                <StrategyCard
                  key={action.id}
                  action={action}
                  index={index}
                  hasAITool={aiTools[index]}
                  effort={aiTools[index]?.implementation?.difficulty}
                />
              ))}
            </div>

            <div className="lg:col-span-4 space-y-8">
              <div className="bg-white border border-gray-100 rounded-3xl p-10 shadow-xl">
                <div className="text-[12px] font-bold text-gray-900 uppercase tracking-[0.2em] mb-6 flex items-center">
                  Note on exclusions:
                </div>
                <p className="text-sm text-gray-500 leading-relaxed italic font-medium">
                  {analysisData.objective?.toLowerCase().includes('ad')
                    ? "I excluded actions related to \"paid advertising\" and \"increasing post frequency\" because you have already promoted heavily without results. Fixing the offer is the prerequisite for success."
                    : "This plan specifically excludes traditional ad-spend strategies and complex technical builds that would exceed your current 10-hour weekly capacity."}
                </p>
              </div>

              <div className="bg-orange-900 rounded-[2.5rem] p-10 text-white shadow-2xl relative overflow-hidden">
                <div className="relative z-10">
                  <div className="text-[12px] font-bold uppercase tracking-[0.3em] text-orange-400 mb-8 opacity-80">Execution Roadmap: 7-Day Sprint</div>

                  <div className="space-y-10">
                    <div>
                      <div className="text-sm font-bold text-orange-300 mb-4 uppercase tracking-widest">Days 1-2: The Fix</div>
                      <div className="space-y-4">
                        <div className="flex items-start gap-4">
                          <div className="w-1.5 h-1.5 rounded-full bg-orange-500 mt-1.5 flex-shrink-0"></div>
                          <div className="text-sm font-medium opacity-90">Analyze competitor 1-star reviews. List the top 3 missing features.</div>
                        </div>
                        <div className="flex items-start gap-4">
                          <div className="w-1.5 h-1.5 rounded-full bg-orange-500 mt-1.5 flex-shrink-0"></div>
                          <div className="text-sm font-medium opacity-90">Rewrite Headline & Bullets to target those missing features.</div>
                        </div>
                      </div>
                    </div>

                    <div>
                      <div className="text-sm font-bold text-orange-300 mb-4 uppercase tracking-widest">Day 3: The Build</div>
                      <div className="flex items-start gap-4">
                        <div className="w-1.5 h-1.5 rounded-full bg-orange-500 mt-1.5 flex-shrink-0"></div>
                        <div className="text-sm font-medium opacity-90">Update your sales page/landing page with the new copy only. Do not change the design.</div>
                      </div>
                    </div>

                    <div>
                      <div className="text-sm font-bold text-orange-300 mb-4 uppercase tracking-widest">Days 4-7: The Test (No Ads)</div>
                      <div className="space-y-4">
                        <div className="flex items-start gap-4">
                          <div className="w-1.5 h-1.5 rounded-full bg-orange-500 mt-1.5 flex-shrink-0"></div>
                          <div className="text-sm font-medium opacity-90">Post the new concept in 3 relevant niche communities. Ask for specific feedback.</div>
                        </div>
                        <div className="flex items-start gap-4">
                          <div className="w-1.5 h-1.5 rounded-full bg-orange-500 mt-1.5 flex-shrink-0"></div>
                          <div className="text-sm font-medium opacity-90">Engage with commenters. Track interest levels. Do not sell.</div>
                        </div>
                      </div>
                    </div>

                    <div className="pt-6 border-t border-orange-800">
                      <div className="text-sm font-bold text-orange-300 mb-4 uppercase tracking-widest">Decision Point (Day 8)</div>
                      <div className="space-y-3">
                        <div className="text-sm opacity-90"><span className="font-bold">High Interest:</span> Resume paid ads.</div>
                        <div className="text-sm opacity-90"><span className="font-bold">Silence:</span> Your headline is still too generic. Iterate again.</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="text-center pt-8">
                <div className="bg-orange-50 border border-orange-100 rounded-2xl p-8 inline-block">
                  <p className="text-orange-900 italic font-medium text-lg">"{inspirationalMessage}"</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Reasonable Trace / Logic Section removed per request */}

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

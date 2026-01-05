
import Button from '../../components/base/Button';
import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { getUserAnalyses, getAnalysisById, type BusinessAnalysisResult } from '../../api/business-analyzer';


export default function Results() {

  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState('bottlenecks');
  const [showToast, setShowToast] = useState(false);
  const [implementedSolutions, setImplementedSolutions] = useState<Set<number>>(new Set());
  const [selectedTools, setSelectedTools] = useState<{ [key: number]: number[] }>({
    1: [], // Low online visibility
    2: [], // Inefficient customer onboarding
    3: [], // Limited payment options
  });

  const [showComparison, setShowComparison] = useState<{ [key: number]: boolean }>({
    1: false,
    2: false,
    3: false,
  });

  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);
  const [showWatermarkForm, setShowWatermarkForm] = useState(false);
  const [customWatermark, setCustomWatermark] = useState('');
  const [expandedImplementations, setExpandedImplementations] = useState<Set<number>>(new Set());
  const [selectedBottleneckForSolutions, setSelectedBottleneckForSolutions] = useState<number | null>(null);

  // Dynamic data state
  const [analysisData, setAnalysisData] = useState<BusinessAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch analysis data on component mount
  useEffect(() => {
    const fetchAnalysisData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Priority 1: Check if analysis was passed via navigation state (from new analysis)
        const stateAnalysis = location.state?.analysis;
        if (stateAnalysis) {
          console.log("✅ Using analysis from navigation state");
          console.log("Analysis data received:", JSON.stringify(stateAnalysis, null, 2));
          console.log("Bottlenecks:", stateAnalysis.bottlenecks);
          console.log("Business Strategies:", stateAnalysis.business_strategies);
          console.log("AI Tools:", stateAnalysis.ai_tools);
          setAnalysisData(stateAnalysis);
          setIsLoading(false);
          return;
        }

        // Priority 2: Check if specific analysis ID is in query params (from history)
        const analysisId = searchParams.get('id');
        if (analysisId) {
          console.log("Fetching specific analysis with ID:", analysisId);
          try {
            const specificAnalysis = await getAnalysisById(parseInt(analysisId));
            if (specificAnalysis) {
              setAnalysisData(specificAnalysis);
            } else {
              setError("Analysis not found. It may have been deleted.");
            }
          } catch (err: any) {
            console.error("Error fetching analysis by ID:", err);
            setError("Analysis not found. It may have been deleted.");
          }
          setIsLoading(false);
          return;
        }

        // Priority 3: Fetch latest analysis if no state or ID
        console.log("Fetching latest analysis...");
        const analyses = await getUserAnalyses(1);
        if (analyses && analyses.length > 0) {
          setAnalysisData(analyses[0]);
        } else {
          setError("No analysis data found. Please run a business analysis first.");
        }
      } catch (err: any) {
        console.error("Error fetching analysis data:", err);
        setError(err.message || "Failed to load analysis data. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalysisData();
  }, [location.state, searchParams]);

  // Company configuration - can be changed to any company name
  const companyConfig = {
    name: 'Guufs Global',
    reportTitle: 'Business Intelligence Report',
    generatedDate: new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  };

  const handleImplemented = (solutionId: number) => {
    setImplementedSolutions((prev) => new Set([...prev, solutionId]));
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const handleToolSelection = (bottleneckId: number, toolId: number) => {
    setSelectedTools((prev) => {
      const currentTools = prev[bottleneckId] || [];
      const isSelected = currentTools.includes(toolId);
      const newTools = isSelected
        ? currentTools.filter((id) => id !== toolId)
        : [...currentTools, toolId];

      // Update comparison visibility
      setShowComparison((prevComp) => ({
        ...prevComp,
        [bottleneckId]: newTools.length >= 2,
      }));

      return { ...prev, [bottleneckId]: newTools };
    });
  };

  const toggleImplementationDropdown = (toolId: number) => {
    setExpandedImplementations((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(toolId)) {
        newSet.delete(toolId);
      } else {
        newSet.add(toolId);
      }
      return newSet;
    });
  };

  const handleBottleneckClick = (bottleneckId: number) => {
    setSelectedBottleneckForSolutions(bottleneckId);
    setActiveTab('solutions');
  };

  const handleLearnMoreFromSolution = (bottleneckId: number) => {
    setSelectedBottleneckForSolutions(bottleneckId);
    setActiveTab('efficiency-tools');
  };

  const generatePDFReport = async (watermarkText?: string) => {
    setIsGeneratingPDF(true);
    setShowWatermarkForm(false);

    try {
      // Dynamic import for better performance
      const jsPDF = (await import('jspdf')).default;

      const doc = new jsPDF('p', 'mm', 'a4');
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();

      // Use custom watermark or default company name
      const finalWatermark = watermarkText || companyConfig.name;

      // Add watermark function with larger, more visible text
      const addWatermark = (page: number) => {
        doc.setPage(page);
        doc.saveGraphicsState();
        // const gState = "watermark";
        // doc.addGState({ opacity: 0.25 }, gState); // --- Changed line ---
        // doc.setGState(gState) // Increased opacity from 0.1 to 0.25
        (doc as any).setGState((doc as any).GState({ opacity: 0.25 }));
        doc.setTextColor(128, 128, 128);
        doc.setFontSize(60); // Increased from 40 to 60
        doc.setFont('helvetica', 'bold');
        doc.text(finalWatermark, pageWidth / 2, pageHeight / 2, {
          align: 'center',
          angle: 45
        });
        doc.restoreGraphicsState();
      };

      // Page 1: Cover Page
      doc.setFillColor(249, 115, 22); // Orange background
      doc.rect(0, 0, pageWidth, 80, 'F');

      // Company logo area
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(24);
      doc.setFont('helvetica', 'bold');
      doc.text(finalWatermark, pageWidth / 2, 30, { align: 'center' });

      // Report title
      doc.setFontSize(32);
      //doc.text(companyConfig.reportTitle, pageWidth / 2, 50, { align: 'center' });

      // Generated date
      doc.setFontSize(14);
      doc.setFont('helvetica', 'normal');
      doc.text(`Generated by ${companyConfig.name} on ${companyConfig.generatedDate}`, pageWidth / 2, 65, { align: 'center' });

      // Business summary section
      doc.setTextColor(51, 51, 51);
      doc.setFontSize(18);
      doc.setFont('helvetica', 'bold');
      doc.text('Executive Summary', 20, 100);

      doc.setFontSize(12);
      doc.setFont('helvetica', 'normal');
      const summaryText = `This comprehensive business intelligence report analyzes your current business operations and provides actionable insights for growth. Our AI-powered analysis has identified 3 key bottlenecks and recommends strategic solutions with projected ROI of $13,900 over 12 months.`;

      const summaryLines = doc.splitTextToSize(summaryText, pageWidth - 40);
      doc.text(summaryLines, 20, 115);

      // Key metrics boxes
      const metrics = [
        { label: 'Bottlenecks Identified', value: '3', color: [239, 68, 68] },
        { label: 'Solutions Recommended', value: '7', color: [34, 197, 94] },
        { label: 'AI Confidence Score', value: '85%', color: [147, 51, 234] },
        { label: 'Projected ROI', value: '$13,900', color: [249, 115, 22] }
      ];

      let yPos = 150;
      metrics.forEach((metric, index) => {
        const xPos = 20 + (index % 2) * 85;
        if (index % 2 === 0 && index > 0) yPos += 40;

        const [r, g, b] = metric.color;
        doc.setFillColor(r, g, b);
        doc.roundedRect(xPos, yPos, 80, 30, 3, 3, 'F');

        doc.setTextColor(255, 255, 255);
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text(metric.value, xPos + 40, yPos + 12, { align: 'center' });

        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.text(metric.label, xPos + 40, yPos + 22, { align: 'center' });
      });

      addWatermark(1);

      // Page 2: Bottlenecks Analysis
      doc.addPage();

      doc.setTextColor(51, 51, 51);
      doc.setFontSize(20);
      doc.setFont('helvetica', 'bold');
      doc.text('Identified Bottlenecks', 20, 30);

      let currentY = 50;

      bottlenecks.forEach((bottleneck, index) => {
        // Bottleneck header
        doc.setFillColor(254, 243, 199);
        doc.rect(20, currentY - 5, pageWidth - 40, 25, 'F');

        doc.setTextColor(249, 115, 22);
        doc.setFontSize(14);
        doc.setFont('helvetica', 'bold');
        doc.text(`#${index + 1} ${bottleneck.title}`, 25, currentY + 5);

        doc.setTextColor(185, 28, 28);
        doc.setFontSize(10);
        doc.text(`${bottleneck.priority} PRIORITY`, pageWidth - 45, currentY + 5);

        currentY += 30;

        // Description
        doc.setTextColor(75, 85, 99);
        doc.setFontSize(11);
        doc.setFont('helvetica', 'normal');
        const descLines = doc.splitTextToSize(bottleneck.description, pageWidth - 50);
        doc.text(descLines, 25, currentY);
        currentY += descLines.length * 5 + 5;

        // Impact
        doc.setFont('helvetica', 'bold');
        doc.text('Impact: ', 25, currentY);
        doc.setFont('helvetica', 'normal');
        const impactLines = doc.splitTextToSize(bottleneck.impact, pageWidth - 60);
        doc.text(impactLines, 45, currentY);
        currentY += impactLines.length * 5 + 15;

        if (currentY > 250) {
          addWatermark(2);
          doc.addPage();
          currentY = 30;
        }
      });

      addWatermark(2);

      // Page 3: Solutions & Tools
      doc.addPage();

      doc.setTextColor(51, 51, 51);
      doc.setFontSize(20);
      doc.setFont('helvetica', 'bold');
      doc.text('Recommended Solutions', 20, 30);

      currentY = 50;

      // Business Strategies
      doc.setFontSize(16);
      doc.setTextColor(34, 197, 94);
      doc.text('Business Strategies', 20, currentY);
      currentY += 15;

      businessStrategies.slice(0, 2).forEach((strategy) => {
        doc.setFillColor(240, 253, 244);
        doc.rect(20, currentY - 5, pageWidth - 40, 35, 'F');

        doc.setTextColor(51, 51, 51);
        doc.setFontSize(12);
        doc.setFont('helvetica', 'bold');
        doc.text(strategy.title, 25, currentY + 5);

        doc.setTextColor(75, 85, 99);
        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        const strategyLines = doc.splitTextToSize(strategy.description, pageWidth - 50);
        doc.text(strategyLines, 25, currentY + 15);

        currentY += 45;
      });

      // AI Tools
      doc.setFontSize(16);
      doc.setTextColor(147, 51, 234);
      doc.text('AI Efficiency Tools', 20, currentY);
      currentY += 15;

      aiTools.slice(0, 2).forEach((tool) => {
        doc.setFillColor(250, 245, 255);
        doc.rect(20, currentY - 5, pageWidth - 40, 35, 'F');

        doc.setTextColor(51, 51, 51);
        doc.setFontSize(12);
        doc.setFont('helvetica', 'bold');
        doc.text(tool.title, 25, currentY + 5);

        doc.setTextColor(147, 51, 234);
        doc.setFontSize(10);
        doc.text(tool.price, pageWidth - 45, currentY + 5);

        doc.setTextColor(75, 85, 99);
        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        const toolLines = doc.splitTextToSize(tool.description, pageWidth - 50);
        doc.text(toolLines, 25, currentY + 15);

        currentY += 45;
      });

      addWatermark(3);

      // Page 4: ROI Analysis
      doc.addPage();

      doc.setTextColor(51, 51, 51);
      doc.setFontSize(20);
      doc.setFont('helvetica', 'bold');
      doc.text('ROI Impact Analysis', 20, 30);

      // ROI Summary boxes
      const roiMetrics = [
        { label: 'Monthly Revenue Increase', value: '$1,000', color: [34, 197, 94] },
        { label: 'Monthly Cost Savings', value: '$200', color: [59, 130, 246] },
        { label: 'Implementation Cost', value: '$500', color: [249, 115, 22] },
        { label: '12-Month Projected Gain', value: '$13,900', color: [147, 51, 234] }
      ];

      let roiY = 60;
      roiMetrics.forEach((metric, index) => {
        const xPos = 20 + (index % 2) * 85;
        if (index % 2 === 0 && index > 0) roiY += 50;

        const [r, g, b] = metric.color;
        doc.setFillColor(r, g, b);
        doc.roundedRect(xPos, roiY, 80, 40, 3, 3, 'F');

        doc.setTextColor(255, 255, 255);
        doc.setFontSize(18);
        doc.setFont('helvetica', 'bold');
        doc.text(metric.value, xPos + 40, roiY + 15, { align: 'center' });

        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        const labelLines = doc.splitTextToSize(metric.label, 70);
        labelLines.forEach((line: string, lineIndex: number) => {
          doc.text(line, xPos + 40, roiY + 25 + (lineIndex * 4), { align: 'center' });
        });
      });

      // AI Confidence Score
      doc.setFillColor(147, 51, 234);
      doc.circle(pageWidth / 2, 200, 30, 'F');

      doc.setTextColor(255, 255, 255);
      doc.setFontSize(24);
      doc.setFont('helvetica', 'bold');
      doc.text('85%', pageWidth / 2, 205, { align: 'center' });

      doc.setTextColor(51, 51, 51);
      doc.setFontSize(14);
      doc.text('AI Confidence Score', pageWidth / 2, 245, { align: 'center' });

      addWatermark(4);

      // Page 5: Implementation Roadmap
      doc.addPage();

      doc.setTextColor(51, 51, 51);
      doc.setFontSize(20);
      doc.setFont('helvetica', 'bold');
      doc.text('Implementation Roadmap', 20, 30);

      const roadmapSteps = [
        { step: 1, title: 'Content Marketing Strategy', timeline: '2-3 weeks', difficulty: 'Medium' },
        { step: 2, title: 'SEMrush Deployment', timeline: '1 week', difficulty: 'Easy' },
        { step: 3, title: 'Jasper AI Integration', timeline: '1 week', difficulty: 'Easy' },
        { step: 4, title: 'Customer Journey Redesign', timeline: '3-4 weeks', difficulty: 'Hard' },
        { step: 5, title: 'Intercom Implementation', timeline: '2 weeks', difficulty: 'Medium' },
        { step: 6, title: 'Payment Optimization', timeline: '2-3 weeks', difficulty: 'Medium' }
      ];

      let roadmapY = 50;
      roadmapSteps.forEach((step) => {
        // Step number circle
        doc.setFillColor(249, 115, 22);
        doc.circle(30, roadmapY + 5, 8, 'F');

        doc.setTextColor(255, 255, 255);
        doc.setFontSize(12);
        doc.setFont('helvetica', 'bold');
        doc.text(step.step.toString(), 30, roadmapY + 8, { align: 'center' });

        // Step details
        doc.setTextColor(51, 51, 51);
        doc.setFontSize(12);
        doc.setFont('helvetica', 'bold');
        doc.text(step.title, 45, roadmapY + 5);

        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(75, 85, 99);
        doc.text(`Timeline: ${step.timeline}`, 45, roadmapY + 15);
        doc.text(`Difficulty: ${step.difficulty}`, 120, roadmapY + 15);

        roadmapY += 25;
      });

      addWatermark(5);

      // Save the PDF
      const filename = watermarkText
        ? `${watermarkText.replace(/\s+/g, '_')}_Business_Intelligence_Report_${new Date().toISOString().split('T')[0]}.pdf`
        : `${companyConfig.name.replace(/\s+/g, '_')}_Business_Intelligence_Report_${new Date().toISOString().split('T')[0]}.pdf`;

      doc.save(filename);

      // Show success toast
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);

    } catch (error) {
      console.error('Error generating PDF:', error);
      toast.error('Error generating PDF report. Please try again.');
    } finally {
      setIsGeneratingPDF(false);
      setCustomWatermark('');
    }
  };

  const handleWatermarkSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customWatermark.trim()) {
      generatePDFReport(customWatermark.trim());
    }
  };

  // Use dynamic data from API or fallback to hardcoded data
  const bottlenecks = analysisData?.bottlenecks || [
    {
      id: 1,
      title: 'Low online visibility',
      description:
        'Your business has limited presence in search results and social media platforms, making it difficult for potential customers to discover your services.',
      priority: 'HIGH',
      impact: 'Reduced customer acquisition and brand awareness',
    },
    {
      id: 2,
      title: 'Inefficient customer onboarding',
      description:
        'The current onboarding process is lengthy and confusing, leading to customer drop-offs and reduced satisfaction rates.',
      priority: 'MEDIUM',
      impact: 'Lower conversion rates and customer retention',
    },
    {
      id: 3,
      title: 'Limited payment options',
      description:
        'Customers can only pay through traditional methods, missing out on modern payment preferences and mobile transactions.',
      priority: 'MEDIUM',
      impact: 'Lost sales opportunities and customer inconvenience',
    },
  ];

  const businessStrategies = analysisData?.business_strategies || [
    {
      id: 1,
      bottleneckId: 1,
      title: 'Content Marketing Strategy',
      description:
        'Develop a comprehensive content marketing approach to improve organic visibility.',
      price: '$500-2000/month',
      rating: '88/100',
      features: ['Blog content creation', 'Social media campaigns', 'SEO optimization', 'Brand storytelling'],
      pros: ['Long-term organic growth', 'Builds brand authority', 'Cost-effective over time'],
      cons: ['Takes time to see results', 'Requires consistent effort'],
    },
    {
      id: 2,
      bottleneckId: 1,
      title: 'Influencer Partnership Program',
      description: 'Partner with industry influencers to expand reach and credibility.',
      price: '$1000-5000/month',
      rating: '85/100',
      features: [
        'Influencer identification',
        'Partnership negotiations',
        'Campaign management',
        'Performance tracking',
      ],
      pros: ['Quick visibility boost', 'Authentic endorsements', 'Access to new audiences'],
      cons: ['Dependent on influencer reputation', 'Can be expensive'],
    },
    {
      id: 3,
      bottleneckId: 2,
      title: 'Customer Journey Mapping',
      description:
        'Redesign the customer onboarding experience based on user behavior analysis.',
      price: '$2000-8000 one-time',
      rating: '92/100',
      features: [
        'User experience audit',
        'Journey optimization',
        'Touchpoint analysis',
        'Process streamlining',
      ],
      pros: ['Improves conversion rates', 'Reduces customer confusion', 'Data-driven approach'],
      cons: ['Requires initial investment', 'May need staff retraining'],
    },
    {
      id: 4,
      bottleneckId: 3,
      title: 'Payment Experience Optimization',
      description: 'Redesign checkout process to accommodate modern payment preferences.',
      price: '$1500-5000 one-time',
      rating: '89/100',
      features: [
        'Checkout flow redesign',
        'Mobile optimization',
        'Payment method integration',
        'Security enhancement',
      ],
      pros: ['Reduces cart abandonment', 'Improves user experience', 'Increases conversion rates'],
      cons: ['Implementation complexity', 'Requires testing period'],
    },
  ];

  const aiTools = analysisData?.ai_tools || [
    {
      id: 1,
      bottleneckId: 1,
      title: 'SEMrush',
      description: 'AI-powered SEO and online marketing tool for visibility optimization.',
      price: '$119.95/month',
      rating: '85/100',
      features: [
        'AI keyword research',
        'Automated site audit',
        'Competitor analysis',
        'Content optimization',
      ],
      pros: ['Comprehensive SEO features', 'AI-driven insights', 'User-friendly interface'],
      cons: ['Cost may be high for small businesses', 'Learning curve required'],
      website: 'https://www.semrush.com',
      comparison: {
        pricing: '$119.95/month',
        easeOfUse: '8/10',
        features: 'Comprehensive',
        support: '24/7 Chat',
        integration: '100+ tools',
        learningCurve: 'Medium',
      },
      implementation: {
        timeframe: "2 weeks",
        difficulty: 'Easy',
        steps: [
          '1. Look up the procedure for the tool',
          '2. Follow the instructions properly',
        ],
        requirements: ["Strength"],
      },
    },
    {
      id: 2,
      bottleneckId: 1,
      title: 'Jasper AI',
      description: 'AI content creation tool for marketing and social media.',
      price: '$49/month',
      rating: '87/100',
      features: [
        'AI content generation',
        'Brand voice training',
        'Multi-platform optimization',
        'SEO content creation',
      ],
      pros: ['Fast content creation', 'Consistent brand voice', 'Multiple content types'],
      cons: ['Requires human editing', 'May lack creativity'],
      website: 'https://www.jasper.ai',
      comparison: {
        pricing: '$49/month',
        easeOfUse: '9/10',
        features: 'Content-focused',
        support: 'Email & Chat',
        integration: '50+ tools',
        learningCurve: 'Low',
      },
      implementation: {
        timeframe: "2 weeks",
        difficulty: 'Easy',
        steps: [
          '1. Look up the procedure for the tool',
          '2. Follow the instructions properly',
        ],
        requirements: ["Diligence"],
      },
    },
    {
      id: 3,
      bottleneckId: 2,
      title: 'Intercom',
      description: 'AI-powered customer onboarding and support platform.',
      price: '$89/month',
      rating: '90/100',
      features: [
        'AI chatbot assistance',
        'Automated onboarding flows',
        'Smart user segmentation',
        'Predictive support',
      ],
      pros: ['24/7 automated support', 'Personalized experiences', 'Reduces support workload'],
      cons: ['Setup complexity', 'Monthly subscription cost'],
      website: 'https://www.intercom.com',
      comparison: {
        pricing: '$89/month',
        easeOfUse: '7/10',
        features: 'Customer-focused',
        support: '24/7 Phone',
        integration: '200+ tools',
        learningCurve: 'Medium',
      },
      implementation: {
        timeframe: "2 weeks",
        difficulty: 'Easy',
        steps: [
          '1. Look up the procedure for the tool',
          '2. Follow the instructions properly',
        ],
        requirements: ["Composure"],
      },
    },
    {
      id: 4,
      bottleneckId: 2,
      title: 'Pendo',
      description: 'AI-driven product analytics and user onboarding optimization.',
      price: '$2000/month',
      rating: '88/100',
      features: [
        'User behavior analytics',
        'AI-powered insights',
        'Automated user guides',
        'Feature adoption tracking',
      ],
      pros: ['Data-driven optimization', 'Improves user adoption', 'Comprehensive analytics'],
      cons: ['High cost for small businesses', 'Complex implementation'],
      website: 'https://www.pendo.io',
      comparison: {
        pricing: '$2000/month',
        easeOfUse: '6/10',
        features: 'Analytics-focused',
        support: 'Dedicated Manager',
        integration: '75+ tools',
        learningCurve: 'High',
      },
      implementation: {
        timeframe: "2 weeks",
        difficulty: 'Easy',
        steps: [
          '1. Look up the procedure for the tool',
          '2. Follow the instructions properly',
        ],
        requirements: ["Resilience"],
      },
    },
    {
      id: 5,
      bottleneckId: 3,
      title: 'Stripe Radar',
      description: 'AI-powered fraud detection and payment optimization.',
      price: '$0.05 per transaction',
      rating: '94/100',
      features: [
        'AI fraud detection',
        'Payment optimization',
        'Risk scoring',
        'Automated blocking',
      ],
      pros: [
        'Reduces fraudulent transactions',
        'Improves payment success rates',
        'Machine learning adaptation',
      ],
      cons: ['Per-transaction fees', 'May block legitimate transactions'],
      website: "www.stripe.com",
      comparison: {
        pricing: '$0.05/transaction',
        easeOfUse: '9/10',
        features: 'Security-focused',
        support: '24/7 Email',
        integration: 'Stripe ecosystem',
        learningCurve: 'Low',
      },
      implementation: {
        timeframe: "2 weeks",
        difficulty: 'Easy',
        steps: [
          '1. Look up the procedure for the tool',
          '2. Follow the instructions properly',
        ],
        requirements: ["Growth"],
      },
    },
    {
      id: 6,
      bottleneckId: 3,
      title: 'PayPal Advanced Checkout',
      description: 'AI-enhanced payment processing with smart recommendations.',
      price: '2.9% + $0.30 per transaction',
      rating: '86/100',
      features: [
        'Smart payment routing',
        'AI risk assessment',
        'Dynamic checkout',
        'Payment method optimization',
      ],
      pros: [
        'Wide payment method support',
        'AI-optimized conversion',
        'Global reach',
      ],
      cons: ['Transaction fees', 'Limited customization'],
      website: "www.paypal.com",
      comparison: {
        pricing: '2.9% + $0.30/transaction',
        easeOfUse: '8/10',
        features: 'Payment-focused',
        support: 'Phone & Chat',
        integration: 'Global platforms',
        learningCurve: 'Low',
      },
      implementation: {
        timeframe: "2 weeks",
        difficulty: 'Easy',
        steps: [
          '1. Look up the procedure for the tool',
          '2. Follow the instructions properly',
        ],
        requirements: ["Love"],
      },
    },
  ];

  const roadmapSteps = analysisData?.roadmap || [];
  const roiMetrics = analysisData?.roi_metrics;
  const aiConfidenceScore = analysisData?.ai_confidence_score || 85;

  const getCurrentStrategies = () => {
    if (activeTab === 'solutions') {
      if (selectedBottleneckForSolutions) {
        return businessStrategies.filter((strategy) => strategy.bottleneckId === selectedBottleneckForSolutions);
      }
      return businessStrategies;
    }
    // default to showing strategies for the first bottleneck when on the bottlenecks tab
    return businessStrategies.filter((strategy) => strategy.bottleneckId === 1);
  };

  const getCurrentTools = () => {
    if (activeTab === 'efficiency-tools') {
      if (selectedBottleneckForSolutions) {
        return aiTools.filter((tool) => tool.bottleneckId === selectedBottleneckForSolutions);
      }
      return aiTools;
    }
    // default to showing tools for the first bottleneck when on the bottlenecks tab
    return aiTools.filter((tool) => tool.bottleneckId === 1);
  };

  const getSelectedToolsForBottleneck = (bottleneckId: number) => {
    const selectedIds = selectedTools[bottleneckId] || [];
    return aiTools.filter((tool) => selectedIds.includes(tool.id));
  };

  const ComparisonTable = ({
    bottleneckId,
    tools,
  }: {
    bottleneckId: number;
    tools: any[];
  }) => {
    if (!showComparison[bottleneckId] || tools.length < 2) return null;
    return (
      <div className="mt-6 bg-orange-50 border border-orange-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold text-gray-900">Tool Comparison</h4>
          <button
            onClick={() =>
              setShowComparison((prev) => ({ ...prev, [bottleneckId]: false }))
            }
            className="text-orange-600 hover:text-orange-700 text-sm font-medium"
          >
            <i className="ri-close-line mr-1"></i>
            Collapse
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-orange-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-900">
                  Feature
                </th>
                {tools.map((tool) => (
                  <th
                    key={tool.id}
                    className="text-left py-3 px-4 font-semibold text-gray-900"
                  >
                    {tool.title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Pricing</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison?.pricing || tool.price}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Ease of Use</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison?.easeOfUse || 'N/A'}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Learning Curve</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${tool.comparison?.learningCurve === 'Easy' ? 'bg-green-100 text-green-800' :
                        tool.comparison?.learningCurve === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                          tool.comparison?.learningCurve === 'Hard' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                      }`}>
                      {tool.comparison?.learningCurve || 'N/A'}
                    </span>
                  </td>
                ))}
              </tr>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Integration</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison?.integration || 'N/A'}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-orange-100 bg-green-50">
                <td className="py-3 px-4 font-medium text-gray-700">
                  <div className="flex items-center space-x-2">
                    <i className="ri-thumb-up-line text-green-600"></i>
                    <span>Pros</span>
                  </div>
                </td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    <ul className="space-y-1 text-xs">
                      {tool.pros?.slice(0, 3).map((pro: string, idx: number) => (
                        <li key={idx} className="flex items-start space-x-1">
                          <i className="ri-checkbox-circle-fill text-green-500 text-sm mt-0.5 flex-shrink-0"></i>
                          <span className="leading-tight">{pro}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                ))}
              </tr>
              <tr className="bg-red-50">
                <td className="py-3 px-4 font-medium text-gray-700">
                  <div className="flex items-center space-x-2">
                    <i className="ri-thumb-down-line text-red-600"></i>
                    <span>Cons</span>
                  </div>
                </td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    <ul className="space-y-1 text-xs">
                      {tool.cons?.slice(0, 2).map((con: string, idx: number) => (
                        <li key={idx} className="flex items-start space-x-1">
                          <i className="ri-alert-fill text-red-500 text-sm mt-0.5 flex-shrink-0"></i>
                          <span className="leading-tight">{con}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
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
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="ri-error-warning-line text-3xl text-red-600"></i>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Analysis</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="flex gap-3 justify-center">
            <Button
              variant="primary"
              onClick={() => navigate('/dashboard/analyze')}
            >
              <i className="ri-add-line mr-2"></i>
              Create New Analysis
            </Button>
            <Button
              variant="outline"
              onClick={() => window.location.reload()}
            >
              <i className="ri-refresh-line mr-2"></i>
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 relative">
      {/* Toast Notification */}
      {showToast && (
        <div className="fixed top-4 right-4 z-50 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2 animate-fade-in">
          <i className="ri-check-circle-line text-xl"></i>
          <span className="font-medium">
            {isGeneratingPDF ? 'PDF Report Generated Successfully!' : 'Solution implemented! +15 points added'}
          </span>
        </div>
      )}


      <div className="bg-gradient-to-br from-orange-50 to-white">

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 space-y-4 sm:space-y-0">
            <p className="text-gray-600 mt-2 text-right">
              Generated on {new Date().toLocaleDateString()}
            </p>
          </div>
          <div className="flex space-x-3 justify-end items-start relative">
            <div className='relative'>
              <button
                onClick={() => generatePDFReport()}
                onMouseEnter={() => setShowWatermarkForm(true)}
                onMouseLeave={() => !customWatermark && setShowWatermarkForm(false)}
                disabled={isGeneratingPDF}
                className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 transition-colors duration-200 flex items-center space-x-2 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGeneratingPDF ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <i className="ri-download-line"></i>
                    <span>Download Report</span>
                  </>)}
              </button>

              {/* Watermark Customization Dropdown */}
              {showWatermarkForm && (
                <div
                  className="absolute top-full left-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg p-4 z-50"
                  onMouseEnter={() => setShowWatermarkForm(true)}
                  onMouseLeave={() => setShowWatermarkForm(false)}
                >
                  <form onSubmit={handleWatermarkSubmit}>
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Custom Watermark Name
                      </label>
                      <input
                        type="text"
                        value={customWatermark}
                        onChange={(e) => setCustomWatermark(e.target.value)}
                        placeholder="Enter company/brand name"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm"
                        autoFocus
                      />
                    </div>
                    <div className="flex flex-col space-y-2">
                      <button
                        type="submit"
                        disabled={!customWatermark.trim() || isGeneratingPDF}
                        className="w-full bg-orange-500 text-white px-3 py-2 rounded-lg hover:bg-orange-600 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Generate with Custom Name
                      </button>
                      <button
                        type="button"
                        onClick={() => generatePDFReport()}
                        disabled={isGeneratingPDF}
                        className="w-full bg-gray-100 text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Use Default
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>

            <button
              onClick={() => navigate('/analysis-history')}
              className="bg-white text-gray-700 border border-gray-300 px-6 py-2 rounded-lg hover:bg-gray-50 transition-colors duration-200 flex items-center space-x-2 whitespace-nowrap"
            >
              <i className="ri-history-line"></i>
              <span>Analysis History</span>
            </button>
          </div>
        </div>

        {/* Hero Section */}
        <section className="bg-gradient-to-br from-orange-50 to-white pt-10 sm:pt-12 md:pt-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-6 sm:mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 bg-green-100 rounded-full mb-4 sm:mb-6">
                <i className="ri-check-line text-green-500 text-2xl sm:text-3xl"></i>
              </div>
              <h1 className="text-3xl sm:text-4xl  font-bold text-black mb-3 sm:mb-4 px-2">
                Your AI Strategy is Ready!
              </h1>
              <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-3xl mx-auto px-4">
                Based on your business profile, we've identified various AI solutions
                that can transform your operations and drive growth.
              </p>
            </div>

          </div>
        </section>


        {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-sm mb-8">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              {[
                { id: 'bottlenecks', label: 'Bottlenecks', icon: 'ri-error-warning-line' },
                { id: 'solutions', label: 'Solutions', icon: 'ri-lightbulb-line' },
                { id: 'efficiency-tools', label: 'Efficiency Tools', icon: 'ri-robot-line' },
                { id: 'roadmap', label: 'Roadmap', icon: 'ri-roadster-line' },
                { id: 'roi', label: 'ROI Impact', icon: 'ri-line-chart-line' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 whitespace-nowrap ${activeTab === tab.id
                      ? 'border-orange-500 text-orange-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                >
                  <i className={tab.icon}></i>
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          {/* Bottlenecks Tab */}
          {activeTab === 'bottlenecks' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Diagnosed Bottlenecks
              </h2>
              <div className="space-y-6">
                {bottlenecks.map((bottleneck, index) => (
                  <div
                    key={bottleneck.id}
                    className="border-l-4 border-orange-500 bg-orange-50 p-6 rounded-r-lg cursor-pointer hover:bg-orange-100 transition-colors duration-200"
                    onClick={() => handleBottleneckClick(bottleneck.id)}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <span className="bg-orange-100 text-orange-800 text-sm font-medium px-2.5 py-0.5 rounded">
                            #{index + 1}
                          </span>
                          <span
                            className={`text-xs font-semibold px-2 py-1 rounded ${bottleneck.priority === 'HIGH'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                              }`}
                          >
                            {bottleneck.priority} PRIORITY
                          </span>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                          {bottleneck.title}
                        </h3>
                        <p className="text-gray-600 mb-3">{bottleneck.description}</p>
                        <div className="text-sm text-gray-500">
                          <strong>Impact:</strong> {bottleneck.impact}
                        </div>
                      </div>
                      <div className="ml-4">
                        <i className="ri-arrow-right-line text-orange-600 text-xl"></i>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Solutions Tab */}
          {activeTab === 'solutions' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  Business Strategy Solutions
                </h2>
                {selectedBottleneckForSolutions && (
                  <button
                    onClick={() => setSelectedBottleneckForSolutions(null)}
                    className="text-orange-600 hover:text-orange-700 text-sm font-medium flex items-center space-x-1"
                  >
                    <i className="ri-close-line"></i>
                    <span>Show All Solutions</span>
                  </button>
                )}
              </div>

              {selectedBottleneckForSolutions && (
                <div className="mb-6 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                  <h3 className="font-semibold text-orange-800">
                    Solutions for: {bottlenecks.find(b => b.id === selectedBottleneckForSolutions)?.title}
                  </h3>
                </div>
              )}

              {/* Iterate over each bottleneck */}
              {bottlenecks.map((b) => {
                if (selectedBottleneckForSolutions && b.id !== selectedBottleneckForSolutions) {
                  return null;
                }

                return (
                  <div key={b.id} className="mb-12">
                    {!selectedBottleneckForSolutions && (
                      <h3 className="text-xl font-semibold text-gray-800 mb-6">
                        Strategies for: {b.title}
                      </h3>
                    )}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {getCurrentStrategies()
                        .filter((s) => s.bottleneckId === b.id)
                        .map((strategy) => (
                          <div
                            key={strategy.id}
                            className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow duration-200 bg-white"
                          >
                            <div className="flex items-start mb-4">
                              <div className="flex items-center space-x-2">
                                <i className="ri-strategy-line text-orange-500 text-xl"></i>
                                <h4 className="text-lg font-semibold text-gray-900">
                                  {strategy.title}
                                </h4>
                              </div>
                            </div>

                            <p className="text-gray-600 mb-4">{strategy.description}</p>

                            <div className="mb-4">
                              <h5 className="font-medium text-gray-900 mb-2">
                                Features:
                              </h5>
                              <ul className="space-y-1">
                                {strategy.features?.map((feature, idx) => (
                                  <li
                                    key={idx}
                                    className="flex items-center space-x-2 text-sm text-gray-600"
                                  >
                                    <i className="ri-check-line text-orange-500 text-xs"></i>
                                    <span>{feature}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>

                            <div className="flex space-x-3">
                              <button
                                onClick={() => handleLearnMoreFromSolution(b.id)}
                                className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors duration-200 text-sm font-medium whitespace-nowrap"
                              >
                                Learn More
                              </button>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}


          {/* Efficiency Tools Tab */}
          {activeTab === 'efficiency-tools' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  AI Efficiency Tools
                </h2>
                {selectedBottleneckForSolutions && (
                  <button
                    onClick={() => setSelectedBottleneckForSolutions(null)}
                    className="text-orange-600 hover:text-orange-700 text-sm font-medium flex items-center space-x-1"
                  >
                    <i className="ri-close-line"></i>
                    <span>Show All Tools</span>
                  </button>
                )}
              </div>

              {selectedBottleneckForSolutions && (
                <div className="mb-6 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                  <h3 className="font-semibold text-orange-800">
                    AI Tools for: {bottlenecks.find(b => b.id === selectedBottleneckForSolutions)?.title}
                  </h3>
                </div>
              )}

              {/* Iterate over each bottleneck */}
              {bottlenecks.map((b) => {
                if (selectedBottleneckForSolutions && b.id !== selectedBottleneckForSolutions) {
                  return null;
                }

                return (
                  <div key={b.id} className="mb-12">
                    {!selectedBottleneckForSolutions && (
                      <h3 className="text-xl font-semibold text-gray-800 mb-6">
                        AI Tools for: {b.title}
                      </h3>
                    )}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                      {getCurrentTools()
                        .filter((tool) => tool.bottleneckId === b.id)
                        .map((tool) => (
                          <div key={tool.id} className="space-y-4 flex flex-col">
                            <div className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow duration-200 bg-white flex flex-col h-full">
                              <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center space-x-2">
                                  <input
                                    type="checkbox"
                                    checked={selectedTools[b.id]?.includes(tool.id) || false}
                                    onChange={() => handleToolSelection(b.id, tool.id)}
                                    className="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500 focus:ring-2"
                                  />
                                  <i className="ri-robot-line text-orange-500 text-xl"></i>
                                  <h4 className="text-lg font-semibold text-gray-900">
                                    {tool.title}
                                  </h4>
                                </div>
                                <div className="text-right">
                                  <div className="text-lg font-bold text-orange-600">
                                    {tool.price}
                                  </div>
                                  <div className="text-sm text-orange-600 bg-orange-100 px-2 py-1 rounded mt-1">
                                    {tool.rating}
                                  </div>
                                </div>
                              </div>

                              <p className="text-gray-600 mb-4 leading-relaxed">{tool.description}</p>

                              <div className="mb-4 flex-grow">
                                <h5 className="font-medium text-gray-900 mb-2">
                                  Key Features:
                                </h5>
                                <ul className="space-y-2">
                                  {tool.features?.map((feature, idx) => (
                                    <li
                                      key={idx}
                                      className="flex items-start space-x-2 text-sm text-gray-600"
                                    >
                                      <i className="ri-check-line text-orange-500 text-sm mt-0.5 flex-shrink-0"></i>
                                      <span className="leading-relaxed">{feature}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              <div className="flex space-x-3 mt-auto">
                                <button
                                  onClick={() => tool.website && window.open(tool.website, '_blank')}
                                  className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors duration-200 text-sm font-medium whitespace-nowrap"
                                >
                                  Learn More
                                </button>
                                <button
                                  onClick={() => toggleImplementationDropdown(tool.id)}
                                  disabled={implementedSolutions.has(tool.id + 100)}
                                  className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors duration-200 whitespace-nowrap ${implementedSolutions.has(tool.id + 100)
                                      ? 'bg-green-100 text-green-700 cursor-not-allowed'
                                      : 'bg-orange-500 text-white hover:bg-orange-600'
                                    }`}
                                >
                                  {implementedSolutions.has(tool.id + 100) ? (
                                    <span className="flex items-center justify-center space-x-1">
                                      <i className="ri-check-line"></i>
                                      <span>Implemented</span>
                                    </span>
                                  ) : (
                                    'How to'
                                  )}
                                </button>
                              </div>
                            </div>

                            {/* Implementation Dropdown */}
                            {expandedImplementations.has(tool.id) && (
                              <div className="space-y-4">
                                {/* Implementation Guide Section */}
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                                  <div className="flex items-center justify-between mb-4">
                                    <h5 className="text-lg font-semibold text-blue-900 flex items-center space-x-2">
                                      <i className="ri-settings-line"></i>
                                      <span>Implementation Guide for {tool.title}</span>
                                    </h5>
                                    <button
                                      onClick={() => toggleImplementationDropdown(tool.id)}
                                      className="text-blue-600 hover:text-blue-700 p-1 rounded-full hover:bg-blue-100 transition-colors"
                                    >
                                      <i className="ri-close-line text-xl"></i>
                                    </button>
                                  </div>

                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                    <div className="bg-white p-3 rounded-lg border border-blue-200">
                                      <div className="text-sm font-medium text-blue-800 mb-1">Timeframe</div>
                                      <div className="text-blue-600 font-semibold">{tool.implementation?.timeframe || 'N/A'}</div>
                                    </div>
                                    <div className="bg-white p-3 rounded-lg border border-blue-200">
                                      <div className="text-sm font-medium text-blue-800 mb-1">Difficulty</div>
                                      <div className={`font-semibold ${tool.implementation?.difficulty === 'Easy' ? 'text-green-600' :
                                          tool.implementation?.difficulty === 'Medium' ? 'text-yellow-600' :
                                            'text-red-600'
                                        }`}>
                                        {tool.implementation?.difficulty || 'N/A'}
                                      </div>
                                    </div>
                                    <div className="bg-white p-3 rounded-lg border border-blue-200">
                                      <div className="text-sm font-medium text-blue-800 mb-1">Steps</div>
                                      <div className="text-blue-600 font-semibold">{tool.implementation?.steps?.length || 0} steps</div>
                                    </div>
                                  </div>

                                  <div className="mb-6">
                                    <h6 className="font-semibold text-blue-900 mb-3 flex items-center space-x-2">
                                      <i className="ri-file-list-line"></i>
                                      <span>Requirements:</span>
                                    </h6>
                                    <div className="flex flex-wrap gap-2">
                                      {tool.implementation?.requirements?.map((req, idx) => (
                                        <span key={idx} className="bg-blue-100 text-blue-800 text-sm px-3 py-1 rounded-full font-medium">
                                          {req}
                                        </span>
                                      ))}
                                    </div>
                                  </div>

                                  <div>
                                    <h6 className="font-semibold text-blue-900 mb-3 flex items-center space-x-2">
                                      <i className="ri-list-ordered"></i>
                                      <span>Implementation Steps:</span>
                                    </h6>
                                    <div className="space-y-3">
                                      {tool.implementation?.steps?.map((step, idx) => (
                                        <div key={idx} className="flex items-start space-x-3 bg-white p-3 rounded-lg border border-blue-100">
                                          <span className="flex-shrink-0 w-7 h-7 bg-blue-500 text-white text-sm rounded-full flex items-center justify-center font-semibold">
                                            {idx + 1}
                                          </span>
                                          <span className="text-sm text-gray-700 leading-relaxed pt-0.5">{step}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>

                                  <div className="mt-6 pt-4 border-t border-blue-200">
                                    <button
                                      onClick={() => {
                                        handleImplemented(tool.id + 100);
                                        toggleImplementationDropdown(tool.id);
                                      }}
                                      className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors text-sm font-semibold flex items-center space-x-2"
                                    >
                                      <i className="ri-check-line text-lg"></i>
                                      <span>Mark as Implemented</span>
                                    </button>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                    </div>

                    {/* Comparison Table */}
                    <ComparisonTable
                      bottleneckId={b.id}
                      tools={getSelectedToolsForBottleneck(b.id)}
                    />
                  </div>
                );
              })}
            </div>
          )}

          {/* Roadmap Tab */}
          {activeTab === 'roadmap' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Implementation Roadmap
              </h2>
              <p className="text-gray-600 mb-8">
                Follow these steps in order for maximum impact based on your identified solutions and efficiency tools
              </p>

              <div className="space-y-6">
                {roadmapSteps.length > 0 ? (
                  roadmapSteps.map((step) => {
                    // Determine badge colors based on difficulty
                    const getDifficultyColor = (difficulty: string) => {
                      switch (difficulty?.toLowerCase()) {
                        case 'easy':
                          return 'bg-green-100 text-green-800';
                        case 'medium':
                          return 'bg-yellow-100 text-yellow-800';
                        case 'hard':
                          return 'bg-red-100 text-red-800';
                        default:
                          return 'bg-gray-100 text-gray-800';
                      }
                    };

                    return (
                      <div key={step.step} className="flex items-start space-x-4">
                        <div className="flex-shrink-0">
                          <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                            {step.step}
                          </div>
                        </div>
                        <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-lg font-semibold text-gray-900">
                              {step.title}
                            </h3>
                            <div className="flex items-center space-x-3">
                              <span className={`text-xs font-medium px-2.5 py-0.5 rounded ${getDifficultyColor(step.difficulty)}`}>
                                {step.difficulty}
                              </span>
                              <div className="flex items-center text-sm text-gray-500">
                                <i className="ri-time-line mr-1"></i>
                                {step.timeline}
                              </div>
                            </div>
                          </div>
                          <p className="text-gray-600 mb-4">
                            {step.description}
                          </p>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
                    <i className="ri-road-map-line text-4xl text-gray-400 mb-3"></i>
                    <p className="text-gray-600">No roadmap steps available yet.</p>
                    <p className="text-sm text-gray-500 mt-2">Run a new analysis to generate your implementation roadmap.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ROI Tab */}
          {activeTab === 'roi' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                ROI Impact Analysis
              </h2>
              <p className="text-gray-600 mb-8">
                Projected financial impact of implementing the recommended solutions and efficiency tools
              </p>

              {roiMetrics ? (
                <>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                    {/* Revenue Impact Card */}
                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                      <div className="flex items-center mb-4">
                        <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                          <i className="ri-line-chart-line text-green-600"></i>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900">Revenue Impact</h3>
                      </div>

                      <div className="space-y-4">
                        <div>
                          <p className="text-sm text-gray-600 mb-1">Monthly Cost Savings</p>
                          <p className="text-2xl font-bold text-green-600">
                            ${roiMetrics.monthly_cost_savings?.toLocaleString() || '0'}
                          </p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 mb-1">Monthly Revenue Increase</p>
                          <p className="text-2xl font-bold text-green-600">
                            ${roiMetrics.monthly_revenue_increase?.toLocaleString() || '0'}
                          </p>
                        </div>
                        <div className="border-t border-gray-200 pt-4">
                          <p className="text-sm text-gray-600 mb-1">Total Monthly Impact</p>
                          <p className="text-3xl font-bold text-green-600">
                            ${((roiMetrics.monthly_cost_savings || 0) + (roiMetrics.monthly_revenue_increase || 0)).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Investment & ROI Card */}
                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                      <div className="flex items-center mb-4">
                        <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center mr-3">
                          <i className="ri-money-dollar-circle-line text-orange-600"></i>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900">Investment & ROI</h3>
                      </div>

                      <div className="space-y-4">
                        <div>
                          <p className="text-sm text-gray-600 mb-1">Implementation Cost</p>
                          <p className="text-2xl font-bold text-orange-600">
                            ${roiMetrics.implementation_cost?.toLocaleString() || '0'}
                          </p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 mb-1">Break-even Timeline</p>
                          <p className="text-2xl font-bold text-orange-600">
                            {roiMetrics.break_even_months || 0} month{roiMetrics.break_even_months !== 1 ? 's' : ''}
                          </p>
                        </div>
                        <div className="border-t border-gray-200 pt-4">
                          <p className="text-sm text-gray-600 mb-1">12-Month Projected Gain</p>
                          <p className="text-3xl font-bold text-orange-600">
                            ${roiMetrics.twelve_month_projected_gain?.toLocaleString() || '0'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Additional Metrics */}
                  {(roiMetrics.time_savings_per_week || roiMetrics.efficiency_gain_percent) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                      {roiMetrics.time_savings_per_week && (
                        <div className="bg-white border border-gray-200 rounded-lg p-6">
                          <div className="flex items-center mb-2">
                            <i className="ri-time-line text-blue-600 text-xl mr-2"></i>
                            <h4 className="font-semibold text-gray-900">Time Savings</h4>
                          </div>
                          <p className="text-3xl font-bold text-blue-600">
                            {roiMetrics.time_savings_per_week} hrs/week
                          </p>
                          <p className="text-sm text-gray-600 mt-1">Freed up for strategic work</p>
                        </div>
                      )}
                      {roiMetrics.efficiency_gain_percent && (
                        <div className="bg-white border border-gray-200 rounded-lg p-6">
                          <div className="flex items-center mb-2">
                            <i className="ri-speed-up-line text-purple-600 text-xl mr-2"></i>
                            <h4 className="font-semibold text-gray-900">Efficiency Gain</h4>
                          </div>
                          <p className="text-3xl font-bold text-purple-600">
                            {roiMetrics.efficiency_gain_percent}%
                          </p>
                          <p className="text-sm text-gray-600 mt-1">Process improvement</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* AI Confidence Score */}
                  <div className="bg-white border border-gray-200 rounded-lg p-8 text-center mb-8">
                    <div className="w-24 h-24 bg-purple-500 text-white rounded-full flex items-center justify-center mx-auto mb-4">
                      <span className="text-2xl font-bold">{aiConfidenceScore}%</span>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Confidence Score</h3>
                    <p className="text-gray-600 max-w-2xl mx-auto">
                      Based on market data, competitor analysis, and implementation complexity, our AI is {aiConfidenceScore}% confident these recommendations will deliver results.
                    </p>
                  </div>

                  {/* Detailed Breakdown */}
                  {businessStrategies.length > 0 && (
                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                      <h4 className="text-lg font-semibold text-gray-900 mb-4">Projected Strategy Impact</h4>
                      <div className="space-y-4">
                        {businessStrategies.slice(0, 4).map((strategy) => {
                          // Calculate estimated monthly impact per strategy
                          const estimatedImpact = Math.round((roiMetrics.monthly_revenue_increase || 1000) / businessStrategies.length);

                          return (
                            <div key={strategy.id} className="flex justify-between items-center py-2 border-b border-gray-100">
                              <span className="text-gray-600">{strategy.title}</span>
                              <span className="font-semibold text-green-600">
                                +${estimatedImpact.toLocaleString()}/month
                              </span>
                            </div>
                          );
                        })}
                        <div className="flex justify-between items-center py-2 pt-4 border-t-2 border-gray-200">
                          <span className="font-semibold text-gray-900">Total Monthly Impact</span>
                          <span className="font-bold text-green-600 text-lg">
                            +${((roiMetrics.monthly_cost_savings || 0) + (roiMetrics.monthly_revenue_increase || 0)).toLocaleString()}/month
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
                  <i className="ri-money-dollar-circle-line text-4xl text-gray-400 mb-3"></i>
                  <p className="text-gray-600">No ROI data available yet.</p>
                  <p className="text-sm text-gray-500 mt-2">Run a new analysis to generate ROI projections.</p>
                </div>
              )}
            </div>
          )}

        </div>

        {/* CTA Section */}
        <section className="py-10 sm:py-12 md:py-16 bg-gradient-to-br from-orange-50 to-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-4 sm:mb-6 text-black">
              Ready to Get Started?
            </h2>
            <p className="text-base sm:text-lg md:text-xl mb-6 sm:mb-8 text-gray-600 px-4">
              Our team of AI implementation experts is ready to help you bring these recommendations to life.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
              <Button variant="primary" size="lg" className="w-full sm:w-auto text-base sm:text-lg px-6 sm:px-8"
                onClick={() => navigate('/dashboard/customer-service')}>
                <i className="ri-calendar-line mr-2"></i>
                Contact us
              </Button>
              <Button onClick={generatePDFReport}
                disabled={isGeneratingPDF}
                variant="outline" size="lg" className="w-full sm:w-auto text-base sm:text-lg px-6 sm:px-8">
                <i className="ri-download-line mr-2"></i>
                Download Report
              </Button>
            </div>
          </div>
        </section>
      </div>

    </div>
  );
}

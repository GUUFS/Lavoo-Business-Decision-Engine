
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';

interface Message {
  id: number;
  sender: 'user' | 'admin';
  content: string;
  timestamp: string;
}

export default function CustomerServiceConversationPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);
  const [newMessage, setNewMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Load report and conversation data
  useEffect(() => {
    if (!id) return;

    const reports = JSON.parse(localStorage.getItem('userReports') || '[]');
    const currentReport = reports.find((r: any) => r.id === parseInt(id));
    
    if (currentReport) {
      setReport(currentReport);
      
      // Load or create conversation messages
      const conversationKey = `conversation_${id}`;
      const existingMessages = localStorage.getItem(conversationKey);
      
      if (existingMessages) {
        setMessages(JSON.parse(existingMessages));
      } else {
        // Create initial admin response for demo
        const initialMessages: Message[] = [
          {
            id: 1,
            sender: 'admin',
            content: `Thank you for reporting this issue. We've received your request regarding: "${currentReport.issue.substring(0, 100)}${currentReport.issue.length > 100 ? '...' : ''}". Our team is looking into this matter and we'll provide updates as we investigate further.`,
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString() // 2 hours ago
          },
          {
            id: 2,
            sender: 'admin',
            content: 'We\'ve identified the issue and are working on a solution. We expect to have this resolved within the next 24-48 hours. We\'ll keep you updated on our progress.',
            timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString() // 30 minutes ago
          }
        ];
        setMessages(initialMessages);
        localStorage.setItem(conversationKey, JSON.stringify(initialMessages));
      }
    }
  }, [id]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || isSubmitting) return;

    setIsSubmitting(true);

    const userMessage: Message = {
      id: Date.now(),
      sender: 'user',
      content: newMessage.trim(),
      timestamp: new Date().toISOString()
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);

    // Save to localStorage
    const conversationKey = `conversation_${id}`;
    localStorage.setItem(conversationKey, JSON.stringify(updatedMessages));

    setNewMessage('');
    setIsSubmitting(false);

    // Simulate admin auto-response after a delay
    setTimeout(() => {
      const adminResponse: Message = {
        id: Date.now() + 1,
        sender: 'admin',
        content: 'Thank you for your message. We\'ve received your update and our team will review it shortly. We\'ll respond with more information as soon as possible.',
        timestamp: new Date().toISOString()
      };

      const finalMessages = [...updatedMessages, adminResponse];
      setMessages(finalMessages);
      localStorage.setItem(conversationKey, JSON.stringify(finalMessages));
    }, 2000);
  };

  const handleBackToReports = () => {
    navigate('/dashboard/customer-service');
  };

  const isMobile = windowWidth < 768;

  if (!report) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <DashboardSidebar 
          isMobileMenuOpen={isMobileMenuOpen}
          setIsMobileMenuOpen={setIsMobileMenuOpen}
        />
        <div className={`flex-1 transition-all duration-300 ${isMobile ? 'ml-0' : 'ml-64'}`}>
          <div className="p-8 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="ri-error-warning-line text-gray-400 text-2xl"></i>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Report Not Found</h2>
            <p className="text-gray-600 mb-4">The requested report could not be found.</p>
            <button
              onClick={handleBackToReports}
              className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium whitespace-nowrap"
            >
              Back to Reports
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Dashboard Sidebar */}
      <DashboardSidebar 
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      {/* Main Content */}
      <div className={`flex-1 transition-all duration-300 ${isMobile ? 'ml-0' : 'ml-64'}`}>
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6">
              <div className="flex items-center gap-4 mb-4">
                <button
                  onClick={handleBackToReports}
                  className="flex items-center text-orange-600 hover:text-orange-700 font-medium whitespace-nowrap"
                >
                  <i className="ri-arrow-left-line mr-2"></i>
                  Back to Reports
                </button>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
                Report #{report.id} - Conversation
              </h1>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  report.status === 'Pending' 
                    ? 'bg-yellow-100 text-yellow-800'
                    : report.status === 'In Progress'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-green-100 text-green-800'
                }`}>
                  {report.status}
                </span>
                <span className="text-sm text-gray-500">
                  Submitted on {new Date(report.submittedAt).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            </div>

            {/* Original Report */}
            <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm mb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Original Report</h2>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-800">{report.issue}</p>
              </div>
            </div>

            {/* Conversation */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              {/* Messages */}
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Conversation</h2>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                        message.sender === 'user'
                          ? 'bg-orange-500 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium opacity-75">
                            {message.sender === 'user' ? 'You' : 'Admin Support'}
                          </span>
                          <span className="text-xs opacity-60">
                            {new Date(message.timestamp).toLocaleTimeString('en-US', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        </div>
                        <p className="text-sm">{message.content}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Message Form */}
              <div className="p-6">
                <form onSubmit={handleSendMessage} className="space-y-4">
                  <div>
                    <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
                      Send a message
                    </label>
                    <textarea
                      id="message"
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Type your message here..."
                      rows={4}
                      maxLength={500}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none text-sm"
                      required
                    />
                    <div className="flex justify-between items-center mt-2">
                      <p className="text-xs text-gray-500">
                        Our support team typically responds within 2-4 hours
                      </p>
                      <p className="text-xs text-gray-500">
                        {newMessage.length}/500 characters
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={isSubmitting || !newMessage.trim()}
                      className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium text-sm whitespace-nowrap"
                    >
                      {isSubmitting ? (
                        <span className="flex items-center">
                          <i className="ri-loader-4-line animate-spin mr-2"></i>
                          Sending...
                        </span>
                      ) : (
                        <span className="flex items-center">
                          <i className="ri-send-plane-line mr-2"></i>
                          Send Message
                        </span>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>

            {/* Help Information */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3 flex-shrink-0">
                  <i className="ri-information-line text-blue-600"></i>
                </div>
                <div>
                  <h3 className="font-semibold text-blue-800 mb-1">Need immediate assistance?</h3>
                  <p className="text-sm text-blue-700">
                    For urgent issues, you can also contact us directly at support@aistrategy.com or call 1-800-AI-HELP.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

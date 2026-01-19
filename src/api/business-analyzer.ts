/**
 * Business Analyzer API Service
 * Handles communication with the backend AI business analysis endpoints
 */

import axios from "axios";
import Cookies from "js-cookie";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Create authenticated axios config
 * Uses both cookies (httponly) and Authorization header (from js-cookie)
 */
const getAuthConfig = () => {
  // Try to get token from js-cookie (set by frontend)
  const token = Cookies.get("access_token");

  const config: any = {
    withCredentials: true, // This sends httponly cookies automatically
  };

  // If token exists in js-cookie, add Authorization header
  if (token) {
    config.headers = {
      'Authorization': `Bearer ${token}`
    };
  }

  return config;
};

// Type definitions matching backend V3 models

// Primary Bottleneck
export interface PrimaryBottleneck {
  title: string;
  description: string;
  consequence: string;
}

// Secondary Constraint
export interface SecondaryConstraint {
  id: number;
  title: string;
  description: string;
}

// Action Plan with optional toolkit
export interface ActionPlan {
  id: number;
  title: string;
  what_to_do: string;
  why_it_matters: string;
  effort_level: "Low" | "Medium" | "High";
  toolkit?: {
    tool_name: string;
    what_it_helps: string;
    why_this_tool: string;
    website: string;
  } | null;
}

// Execution Roadmap Phase
export interface ExecutionPhase {
  phase: string; // e.g., "Days 1-3: The Fix"
  days: number;
  title: string;
  tasks: string[];
}

// Complete Analysis Result (V3)
export interface BusinessAnalysisResult {
  analysis_id: number;
  business_goal: string;
  // Primary bottleneck
  primary_bottleneck: PrimaryBottleneck;
  // Secondary constraints
  secondary_constraints: SecondaryConstraint[];
  // Strategic direction
  what_to_stop: string;
  strategic_priority: string;
  // Action plans
  action_plans: ActionPlan[];
  total_phases: number;
  // Execution roadmap
  estimated_days: number;
  execution_roadmap: ExecutionPhase[];
  // Additional context
  exclusions_note: string;
  motivational_quote: string;
  // Metadata
  created_at: string;
  ai_model?: string;
}

// DEPRECATED: Legacy types for backward compatibility
export interface Bottleneck {
  id: number;
  title: string;
  description: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  impact: string;
}

export interface BusinessStrategy {
  id: number;
  bottleneckId: number;
  title: string;
  description: string;
  features: string[];
}

export interface AITool {
  id: number;
  bottleneckId: number;
  title: string;
  description: string; // Concise description
  price: string; // Simplified pricing
  rating: string;
  features: string[]; // 4-5 key features
  pros: string[]; // 3-4 key advantages
  cons: string[]; // 2-3 main considerations
  website: string;
  comparison: {
    pricing: string; // Pricing tier summary
    easeOfUse: string; // X/10 rating
    learningCurve: string; // Easy|Medium|Hard
    integration: string; // Integration summary
  };
  implementation: {
    timeframe: string; // e.g. "1-2 weeks"
    difficulty: string; // Easy|Medium|Hard
    steps: string[]; // 4 specific implementation steps
    requirements: string[]; // 2-3 requirements
  };
}

export interface RoadmapStage {
  step: number;
  title: string;
  timeline: string;
  difficulty: string;
  description: string;
}

export interface ROIMetrics {
  monthly_revenue_increase: number;
  monthly_cost_savings: number;
  implementation_cost: number;
  twelve_month_projected_gain: number;
  break_even_months: number;
  time_savings_per_week: number;
  efficiency_gain_percent: number;
}

/**
 * Submit a business goal for AI analysis
 */
export const analyzeBusinessGoal = async (
  businessGoal: string
): Promise<BusinessAnalysisResult> => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/api/business/analyze`,
      { business_goal: businessGoal },
      getAuthConfig()
    );

    if (response.data.success) {
      return response.data.data;
    }
    throw new Error(response.data.message || "Analysis failed");
  } catch (error: any) {
    console.error("Error analyzing business goal:", error);

    // Handle authentication errors
    if (error.response?.status === 401) {
      throw new Error("Session expired. Please login again.");
    }

    // Handle other errors
    const errorMessage = error.response?.data?.detail ||
                         error.response?.data?.message ||
                         error.message ||
                         "Failed to analyze business goal. Please try again.";

    throw new Error(errorMessage);
  }
};

/**
 * Get a specific analysis by ID
 */
export const getAnalysisById = async (
  analysisId: number
): Promise<BusinessAnalysisResult> => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/business/analyses/${analysisId}`,
      getAuthConfig()
    );

    if (response.data.success) {
      return response.data.data;
    }
    throw new Error("Failed to fetch analysis");
  } catch (error: any) {
    console.error("Error fetching analysis:", error);

    if (error.response?.status === 401) {
      throw new Error("Not authenticated. Please login first.");
    }

    throw new Error(
      error.response?.data?.detail || error.message || "Failed to fetch analysis"
    );
  }
};

/**
 * Get user's previous analyses
 */
export const getUserAnalyses = async (limit: number = 10) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/business/analyses?limit=${limit}`,
      getAuthConfig()
    );

    if (response.data.success) {
      return response.data.data;
    }
    throw new Error("Failed to fetch analyses");
  } catch (error: any) {
    console.error("Error fetching user analyses:", error);

    if (error.response?.status === 401) {
      throw new Error("Not authenticated. Please login first.");
    }

    throw new Error(
      error.response?.data?.detail || error.message || "Failed to fetch user analyses"
    );
  }
};

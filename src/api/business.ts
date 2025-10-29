/**
 * Business Analysis API Services
 * 
 * This file contains functions that communicate with the FastAPI backend
 * to get AI recommendations and business analysis.
 */

import { instance } from "../lib/axios";

// ============================================
// TYPE DEFINITIONS (TypeScript Interfaces)
// ============================================

/**
 * Interface for AI Tool Recommendation
 * This defines what data we expect from the backend
 */
export interface ToolRecommendation {
  tool_name: string;           // Name of the AI tool
  similarity_score: number;    // How well it matches (0-1)
  description: string;         // Tool description
}

/**
 * Interface for Business Analysis Request
 * This is the data we send TO the backend
 */
export interface BusinessAnalysisRequest {
  companyName: string;
  industry: string;
  companySize: string;
  businessDescription: string;
  currentChallenges: string;
  goals: string;
  budget?: string;             // Optional (? means not required)
  timeline?: string;
  email: string;
}

/**
 * Interface for SWOT Analysis Response
 * This is what we get BACK from the backend
 */
export interface SwotAnalysis {
  Strengths: string[];
  Weaknesses: string[];
  Opportunities: string[];
  Threats: string[];
}

// ============================================
// API FUNCTIONS
// ============================================

/**
 * Get AI tool recommendations based on user query
 * 
 * @param query - User's search query (e.g., "customer service automation")
 * @param topK - Number of recommendations to return (default: 3)
 * @returns Promise with array of tool recommendations
 * 
 * Example usage:
 *   const tools = await getRecommendations("email marketing", 5);
 */
export const getRecommendations = async (
  query: string,
  topK: number = 3
): Promise<ToolRecommendation[]> => {
  try {
    // Make GET request to /api/recommend endpoint
    // The `instance` already has the base URL (http://localhost:8000)
    const response = await instance.get<ToolRecommendation[]>("/api/recommend", {
      params: {
        query: query,
        top_k: topK,
      },
    });

    // Return the data from response
    return response.data;
  } catch (error) {
    console.error("Error fetching recommendations:", error);
    throw error; // Re-throw so component can handle it
  }
};

/**
 * Get business SWOT analysis based on user role
 * 
 * @param userRole - User's role or industry (e.g., "entrepreneur", "marketer")
 * @returns Promise with SWOT analysis
 * 
 * Example usage:
 *   const analysis = await getBusinessAnalysis("entrepreneur");
 */
export const getBusinessAnalysis = async (
  userRole: string
): Promise<SwotAnalysis> => {
  try {
    const response = await instance.get<SwotAnalysis>("/api/analyze", {
      params: {
        user_role: userRole,
      },
    });

    return response.data;
  } catch (error) {
    console.error("Error fetching business analysis:", error);
    throw error;
  }
};

/**
 * Analyze business and get comprehensive recommendations
 * 
 * This is a COMBINED function that:
 * 1. Gets AI tool recommendations based on challenges/goals
 * 2. Gets SWOT analysis based on industry
 * 3. Returns both together with top tool separated
 * 
 * @param data - Complete business form data
 * @returns Promise with top recommendation, other recommendations, and analysis
 */
export const analyzeBusinessQuery = async (
  data: BusinessAnalysisRequest
): Promise<{
  topRecommendation: ToolRecommendation;
  recommendations: ToolRecommendation[];
  swot: SwotAnalysis;
  formData: BusinessAnalysisRequest;
}> => {
  try {
    // Build a search query from user's challenges and goals
    // This helps the AI find the most relevant tools
    const searchQuery = `${data.currentChallenges} ${data.goals} ${data.industry}`;

    // Call both APIs in parallel using Promise.all
    // This is faster than calling them one by one
    const [allRecommendations, swot] = await Promise.all([
      getRecommendations(searchQuery, 5), // Get top 5 recommendations
      getBusinessAnalysis(data.industry), // Get SWOT for their industry
    ]);

    // Separate the top recommendation from the rest
    const topRecommendation = allRecommendations[0];
    const recommendations = allRecommendations.slice(1, 5); // Get next 4 tools

    // Return combined results
    return {
      topRecommendation,
      recommendations,
      swot,
      formData: data, // Include original form data for display
    };
  } catch (error) {
    console.error("Error analyzing business query:", error);
    throw error;
  }
};

/**
 * Compare multiple AI tools side-by-side
 * 
 * @param toolNames - Array of tool names to compare (2-4 tools)
 * @returns Promise with comparison data
 * 
 * Example usage:
 *   const comparison = await compareTools(["Monica", "ChatGPT", "Jasper"]);
 */
export const compareTools = async (
  toolNames: string[]
): Promise<Record<string, any>> => {
  try {
    // Join tool names with commas for API
    const toolsParam = toolNames.join(",");

    const response = await instance.get("/api/compare", {
      params: {
        tools: toolsParam,
      },
    });

    return response.data;
  } catch (error) {
    console.error("Error comparing tools:", error);
    throw error;
  }
};

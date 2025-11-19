// paypal.tsx
import { useEffect, useRef, useState } from "react";

interface PayPalCheckoutProps {
  amount: number;
  onSuccess: (result: any) => void;
  onError?: (error: any) => void;
}

declare global {
  interface Window {
    paypal?: {
      Buttons: (options: any) => { 
        render: (element: HTMLElement | null) => Promise<void>;
        close?: () => void;
      };
    };
  }
}

export default function PayPalCheckout({ amount, onSuccess, onError }: PayPalCheckoutProps) {
  const paypalRef = useRef<HTMLDivElement | null>(null);
  const [sdkReady, setSdkReady] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const renderedRef = useRef(false);

  // Load PayPal SDK
  useEffect(() => {
    const clientId = import.meta.env.VITE_PAYPAL_CLIENT_ID;
    
    if (!clientId) {
      setError("PayPal Client ID not configured");
      console.error("VITE_PAYPAL_CLIENT_ID is missing");
      return;
    }

    console.log("Loading PayPal SDK...");

    // Remove any existing PayPal script
    const existingScript = document.querySelector(`script[src*="paypal.com/sdk/js"]`);
    if (existingScript) {
      existingScript.remove();
    }

    const script = document.createElement("script");
    script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=USD`;
    script.async = true;
    
    script.onload = () => {
      console.log("✅ PayPal SDK loaded");
      setSdkReady(true);
    };

    script.onerror = () => {
      console.error("❌ Failed to load PayPal SDK");
      setError("Failed to load PayPal SDK");
    };

    document.body.appendChild(script);

    return () => {
      renderedRef.current = false;
    };
  }, []);

  // Render PayPal buttons
  useEffect(() => {
    if (!sdkReady || !window.paypal || !paypalRef.current || renderedRef.current) {
      return;
    }

    const renderButtons = async () => {
      if (!paypalRef.current) return;

      setIsRendering(true);
      renderedRef.current = true;

      try {
        console.log("🎨 Rendering PayPal buttons for $", amount);

        const buttons = window.paypal!.Buttons({
          style: {
            layout: 'vertical',
            color: 'gold',
            shape: 'rect',
            label: 'paypal'
          },

          createOrder: async () => {
            try {
              console.log("📝 Creating PayPal order...");
              const res = await fetch("http://localhost:8000/api/paypal/create-order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ amount: amount.toFixed(2) }),
              });

              if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`Failed to create order: ${errorText}`);
              }

              const data = await res.json();
              console.log("✅ Order created:", data.id);
              return data.id;
            } catch (err) {
              console.error("❌ Create order error:", err);
              setError("Failed to create order. Check console.");
              throw err;
            }
          },

          onApprove: async (data: { orderID: string }) => {
            try {
              console.log("💰 Capturing payment...");
              const res = await fetch("http://localhost:8000/api/paypal/capture-order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ order_id: data.orderID }),
              });

              if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`Capture failed: ${errorText}`);
              }

              const result = await res.json();
              console.log("✅ Payment successful:", result);
              onSuccess(result);
            } catch (err) {
              console.error("❌ Capture error:", err);
              setError("Payment capture failed");
              onError?.(err);
            }
          },

          onCancel: (data: any) => {
            console.log("❌ Payment cancelled by user:", data);
            setError("Payment was cancelled. Please try again.");
          },

          onError: (err: any) => {
            console.error("❌ PayPal error:", err);
            setError("Payment error occurred");
            onError?.(err);
          }
        });

        await buttons.render(paypalRef.current);
        console.log("✅ PayPal buttons rendered successfully");
        setIsRendering(false);
      } catch (err) {
        console.error("❌ Render error:", err);
        setError("Failed to render PayPal buttons");
        setIsRendering(false);
      }
    };

    renderButtons();
  }, [sdkReady, amount]);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
        <p className="text-red-600 text-sm mb-2">⚠️ {error}</p>
        <button
          onClick={() => window.location.reload()}
          className="text-sm text-red-700 underline hover:text-red-800"
        >
          Reload Page
        </button>
      </div>
    );
  }

  if (!sdkReady || isRendering) {
    return (
      <div className="bg-blue-50 rounded-lg p-6 text-center">
        <div className="animate-spin w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full mx-auto mb-3"></div>
        <p className="text-sm text-blue-600 font-medium">Loading PayPal...</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div ref={paypalRef} className="w-full"></div>
    </div>
  );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSearchParams } from "react-router-dom";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import Header from "../../components/feature/Header";
import Footer from "../../components/feature/Footer";
import Button from "../../components/base/Button";
import Input from "../../components/base/Input";
import { useSignup } from "../../api/authentication";
import { toast } from "react-toastify";

// ✅ Validation schema
const signupSchema = z
  .object({
    fullName: z.string().min(2, "Full name is required"),
    email: z.string().email("Invalid email address"),
    password: z.string().min(6, "Password must be at least 6 characters"),
    confirmPassword: z.string().min(6, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    path: ["confirmPassword"],
    message: "Passwords do not match",
  });

type SignupFormData = z.infer<typeof signupSchema>;

export default function SignUp() {
  const navigate = useNavigate();
  const { mutate, isPending } = useSignup();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [searchParams] = useSearchParams();
  const referralCode = searchParams.get("ref");

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
  });

  const onSubmit = (data: SignupFormData) => {
    const payload = new FormData();
    payload.append("email", data.email);
    payload.append("password", data.password);
    payload.append("name", data.fullName);
    payload.append("confirm_password", data.confirmPassword);

    if (referralCode) {
      payload.append("referrer_code", referralCode);
      console.log("DEBUG - Sending referral code:", referralCode);
    }

    console.log("🔍 DEBUG - FormData contents:");
  for (let [key, value] of payload.entries()) {
    console.log(`  ${key}:`, value);
  }
    mutate(payload, {
      onSuccess: () => {
        toast.success("Account created successfully!");
        reset();
        navigate("/login");
      },
      onError: (error) => {
        toast.error("Failed to sign up. Please try again.");
        console.error("Signup Error:", error);
      },
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white flex flex-col">
      <Header />

      <div className="flex-1 flex items-center justify-center py-10 sm:py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full">
          <div className="text-center mb-6 sm:mb-8">
            <h1 className="text-3xl sm:text-4xl font-bold text-black mb-3 sm:mb-4">
              Create Your Account
            </h1>
            <p className="text-base sm:text-lg text-gray-600">
              Start your AI transformation journey today
            </p>
          </div>

          <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg border border-gray-100">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 sm:space-y-6">
              <div>
                <Input
                  label="Full Name"
                  placeholder="John Doe"
                  {...register("fullName")}
                />
                {errors.fullName && (
                  <p className="text-red-500 text-sm mt-1">{errors.fullName.message}</p>
                )}
              </div>

              <div>
                <Input
                  label="Email Address"
                  type="email"
                  placeholder="your@email.com"
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-red-500 text-sm mt-1">{errors.email.message}</p>
                )}
              </div>

              <div className="relative">
                <Input
                  label="Password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a strong password"
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-[42px] text-gray-500 hover:text-orange-500"
                >
                  <i className={`ri-${showPassword ? "eye-off-line" : "eye-line"} text-lg`} />
                </button>
                {errors.password && (
                  <p className="text-red-500 text-sm mt-1">{errors.password.message}</p>
                )}
              </div>

              <div className="relative">
                <Input
                  label="Confirm Password"
                  type={showConfirm ? "text" : "password"}
                  placeholder="Confirm your password"
                  {...register("confirmPassword")}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-4 top-[42px] text-gray-500 hover:text-orange-500"
                >
                  <i className={`ri-${showConfirm ? "eye-off-line" : "eye-line"} text-lg`} />
                </button>
                {errors.confirmPassword && (
                  <p className="text-red-500 text-sm mt-1">
                    {errors.confirmPassword.message}
                  </p>
                )}
              </div>

              <div className="flex items-start">
                <input
                  type="checkbox"
                  required
                  className="w-4 h-4 mt-1 text-orange-500 border-gray-300 rounded focus:ring-orange-500"
                />
                <label className="ml-2 text-sm text-gray-600">
                  I agree to the{" "}
                  <button
                    type="button"
                    className="text-orange-500 hover:text-orange-600 font-medium whitespace-nowrap"
                  >
                    Terms of Service
                  </button>{" "}
                  and{" "}
                  <button
                    type="button"
                    className="text-orange-500 hover:text-orange-600 font-medium whitespace-nowrap"
                  >
                    Privacy Policy
                  </button>
                </label>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                disabled={isPending}
                className="w-full text-base sm:text-lg"
              >
                {isPending ? (
                  <>
                    <i className="ri-loader-4-line mr-2 animate-spin"></i>
                    Creating account...
                  </>
                ) : (
                  <>
                    <i className="ri-user-add-line mr-2"></i>
                    Create Account
                  </>
                )}
              </Button>
            </form>

            <p className="mt-6 sm:mt-8 text-center text-sm text-gray-600">
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => navigate("/login")}
                className="text-orange-500 hover:text-orange-600 font-medium whitespace-nowrap"
              >
                Log in
              </button>
            </p>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}

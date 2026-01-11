import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "react-toastify";
import { useQueryClient } from "@tanstack/react-query";
import Header from "../../components/feature/Header";
import Footer from "../../components/feature/Footer";
import Button from "../../components/base/Button";
import Input from "../../components/base/Input";
import { useLogin } from "../../api/authentication";


// ✅ Zod schema for validation
const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z
    .string()
    .min(6, "Password must be at least 6 characters long"),
});

type LoginFormData = z.infer<typeof loginSchema>;


export default function Login() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { mutateAsync: loginUser } = useLogin();
  // const {mutateAsync: loginAdmin} = useAdmin<AuthResponse>();
  // const { mutate, isPending } = useLogin();
  const [isPending, setIsPending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // ✅ React Hook Form setup
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // ✅ Handle login
  const onSubmit = async (data: LoginFormData) => {
    setIsPending(true);

    try {
      const res = await loginUser(data); // call your backend login
      // Save token
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("auth_token", res.access_token);
      localStorage.setItem("user_token", res.access_token);
      localStorage.setItem("user_id", String(res.id));
      localStorage.setItem("role", res.role);

      // ✅ Invalidate currentUser query to ensure fresh data in dashboard
      await queryClient.invalidateQueries({ queryKey: ["currentUser"] });

      // Redirect based on role (redirect provides immediate feedback, no toast needed)
      if (res.role === "admin") {
        navigate("/admin");
      } else {
        navigate("/dashboard");
      }
    } catch (error: any) {
      toast.error(error?.message || "Login failed. Please check your credentials.");
    } finally {
      setIsPending(false);
    }
    //  ?? const adminData = await loginAdmin(data);
    // localStorage.setItem("isAdmin", "true");
    // navigate("/admin/dashboard");
    // return;
    // } catch (error) {
    // try {
    // await loginUser(data);
    // localStorage.setItem("isAdmin", "false");
    // navigate("/dashboard");
    // return;
    // } catch (error) {
    // toast.error("Login failed. Please check your credentials.");
    // }
    // toast.error("Admin Login failed. Please check your credentials.");
    // }
    // mutate(data, {
    // onSuccess: () => {
    // navigate("/dashboard");
    // },
    // onError: (err) => {
    // toast.error(err.message || "Login failed");
    // },
    // });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white flex flex-col">
      <Header />

      <div className="flex-1 flex items-center justify-center py-10 sm:py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full">
          <div className="text-center mb-6 sm:mb-8">
            <h1 className="text-3xl sm:text-4xl font-bold text-black mb-3 sm:mb-4">
              Welcome Back
            </h1>
            <p className="text-base sm:text-lg text-gray-600">
              Log in to access your AI strategy dashboard
            </p>
          </div>

          <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg border border-gray-100">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 sm:space-y-6">
              {/* Email */}
              <div>
                <Input
                  label="Email Address"
                  type="email"
                  placeholder="your@email.com"
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-sm text-red-500 mt-1">
                    {errors.email.message}
                  </p>
                )}
              </div>

              {/* Password with toggle */}
              <div className="relative">
                <Input
                  label="Password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-9 text-gray-500 hover:text-gray-700"
                >
                  {showPassword ? (
                    <i className="ri-eye-off-line"></i>
                  ) : (
                    <i className="ri-eye-line"></i>
                  )}
                </button>
                {errors.password && (
                  <p className="text-sm text-red-500 mt-1">
                    {errors.password.message}
                  </p>
                )}
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-0">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="w-4 h-4 text-orange-500 border-gray-300 rounded focus:ring-orange-500"
                  />
                  <span className="ml-2 text-sm text-gray-600">Remember me</span>
                </label>
                <button
                  type="button"
                  className="text-sm text-orange-500 hover:text-orange-600 font-medium whitespace-nowrap"
                >
                  Forgot password?
                </button>
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
                    Logging in...
                  </>
                ) : (
                  <>
                    <i className="ri-login-box-line mr-2"></i>
                    Log In
                  </>
                )}
              </Button>
            </form>

            <p className="mt-6 sm:mt-8 text-center text-sm text-gray-600">
              Don’t have an account?{" "}
              <button
                type="button"
                onClick={() => navigate("/signup")}
                className="text-orange-500 hover:text-orange-600 font-medium whitespace-nowrap"
              >
                Sign up for free
              </button>
            </p>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}

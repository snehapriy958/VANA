import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useLocation, useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Trees, Lock, Mail, AlertCircle, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { HealthIndicator } from "@/components/shared/HealthIndicator";

const loginSchema = z.object({
  email: z.string().trim().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginView: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [authError, setAuthError] = useState<string | null>(null);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/dashboard";

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  // If already authenticated, redirect to destination
  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const onSubmit = async (data: LoginFormData) => {
    setAuthError(null);
    try {
      await login(data.email, data.password);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      if (err instanceof Error) {
        setAuthError(err.message);
      } else {
        setAuthError("Authentication failed. Please verify your credentials.");
      }
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-b from-vana-ivory/80 via-white to-vana-sage/10 flex flex-col justify-between p-4 sm:p-6 lg:p-8 font-sans">
      {/* Top Bar with Brand & Health Probe */}
      <div className="flex items-center justify-between max-w-6xl mx-auto w-full">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-vana-forest text-white flex items-center justify-center shadow-subtle">
            <Trees className="h-4.5 w-4.5 text-vana-sage" />
          </div>
          <span className="font-heading font-extrabold text-lg tracking-tight text-vana-forest">
            VANA
          </span>
        </div>
        <HealthIndicator />
      </div>

      {/* Main Login Card */}
      <div className="max-w-md w-full mx-auto my-8">
        <Card className="border-vana-forest/15 shadow-lifted bg-white/95 backdrop-blur-xs">
          <CardHeader className="space-y-1.5 text-center pb-4">
            <div className="mx-auto w-12 h-12 rounded-xl bg-vana-forest text-white flex items-center justify-center shadow-subtle mb-1">
              <Lock className="h-5 w-5 text-vana-gold" />
            </div>
            <CardTitle className="text-2xl font-extrabold font-heading text-vana-forest tracking-tight">
              Sign In to VANA
            </CardTitle>
            <CardDescription className="text-xs text-vana-charcoal/70">
              Environmental Operations &amp; Impact Intelligence Platform
            </CardDescription>
          </CardHeader>

          <CardContent>
            {authError && (
              <div
                className="mb-4 p-3 rounded-md bg-vana-crimson/10 border border-vana-crimson/30 flex items-start gap-2.5 text-xs text-vana-crimson"
                role="alert"
              >
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <div className="flex-1 font-medium">{authError}</div>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-vana-charcoal flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5 text-vana-charcoal/60" />
                  <span>Email Address</span>
                </label>
                <Input
                  type="email"
                  placeholder="operator@akshayavana.com"
                  autoComplete="email"
                  disabled={isSubmitting}
                  className={errors.email ? "border-vana-crimson focus-visible:ring-vana-crimson" : ""}
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-[11px] text-vana-crimson font-medium">
                    {errors.email.message}
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-vana-charcoal flex items-center gap-1.5">
                  <Lock className="h-3.5 w-3.5 text-vana-charcoal/60" />
                  <span>Password</span>
                </label>
                <Input
                  type="password"
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  disabled={isSubmitting}
                  className={errors.password ? "border-vana-crimson focus-visible:ring-vana-crimson" : ""}
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-[11px] text-vana-crimson font-medium">
                    {errors.password.message}
                  </p>
                )}
              </div>

              <Button
                type="submit"
                variant="default"
                disabled={isSubmitting}
                className="w-full mt-2 font-semibold shadow-subtle flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Verifying Credentials...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>

          <CardFooter className="pt-2 border-t border-vana-charcoal/10 flex flex-col gap-2 text-center text-xs text-vana-charcoal/60">
            <div>Akshaya Vana Climate Ventures &bull; Ground Truth Operations</div>
            <div className="text-[10px] text-vana-charcoal/50">
              Role-Based Access Control enforced server-side. Unauthorized access is logged.
            </div>
          </CardFooter>
        </Card>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-vana-charcoal/50">
        &copy; {new Date().getFullYear()} Akshaya Vana Platform. All rights reserved.
      </div>
    </div>
  );
};

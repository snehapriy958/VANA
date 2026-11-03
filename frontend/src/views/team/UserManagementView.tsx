import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { apiClient } from "@/services/apiClient";
import { useAuth } from "@/context/AuthContext";
import { UserRole } from "@/types";
import { UserProfile } from "@/types/auth";
import { PageContainer } from "@/components/layout/PageContainer";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Users,
  UserPlus,
  ShieldCheck,
  PowerOff,
  Power,
  RefreshCw,
  AlertCircle,
  Loader2,
} from "lucide-react";

const provisionUserSchema = z.object({
  email: z.string().trim().email("Valid email required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  full_name: z.string().min(2, "Full name must be at least 2 characters"),
  role: z.enum(["ADMIN", "PROJECT_MANAGER", "FIELD_OFFICER"] as const),
});

type ProvisionFormData = z.infer<typeof provisionUserSchema>;

export const UserManagementView: React.FC = () => {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const isAdmin = currentUser?.role === "ADMIN";

  // Form for user provisioning
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProvisionFormData>({
    resolver: zodResolver(provisionUserSchema),
    defaultValues: {
      email: "",
      password: "",
      full_name: "",
      role: "FIELD_OFFICER",
    },
  });

  // Query users
  const {
    data: userData,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<{ users: UserProfile[]; total: number }>({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await apiClient.get<{ users: UserProfile[]; total: number }>("/users");
      return res.data;
    },
  });

  // Provision User Mutation
  const provisionMutation = useMutation({
    mutationFn: async (data: ProvisionFormData) => {
      const res = await apiClient.post<UserProfile>("/users", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      reset();
      setDialogOpen(false);
      setActionError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof Error) {
        setActionError(err.message);
      } else {
        setActionError("Failed to provision user.");
      }
    },
  });

  // Toggle Activation Mutation
  const toggleActiveMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) => {
      const res = await apiClient.put<UserProfile>(`/users/${id}`, { is_active });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setActionError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof Error) {
        setActionError(err.message);
      } else {
        setActionError("Status update failed.");
      }
    },
  });

  const onProvisionSubmit = (data: ProvisionFormData) => {
    setActionError(null);
    provisionMutation.mutate(data);
  };

  const getRoleVariant = (role: UserRole) => {
    switch (role) {
      case "ADMIN":
        return "verified";
      case "PROJECT_MANAGER":
        return "pending";
      case "FIELD_OFFICER":
      default:
        return "sage";
    }
  };

  return (
    <PageContainer
      title="Team & User Management"
      description="Organization Directory, RBAC Assignments, & Security Status"
      action={
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin text-vana-forest" : ""}`} />
            <span>Refresh</span>
          </Button>

          {isAdmin && (
            <Button
              variant="default"
              size="sm"
              onClick={() => {
                setActionError(null);
                setDialogOpen(true);
              }}
              className="flex items-center gap-1.5 shadow-subtle"
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span>Provision User</span>
            </Button>
          )}
        </div>
      }
    >
      {/* Banner / Notices */}
      {actionError && (
        <div
          className="p-3 bg-vana-crimson/10 border border-vana-crimson/30 rounded-md flex items-center gap-2 text-xs text-vana-crimson"
          role="alert"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Users Table Card */}
      <Card>
        <CardHeader className="pb-3 border-b border-vana-charcoal/10">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <CardTitle className="text-base font-heading text-vana-forest flex items-center gap-2">
                <Users className="h-4.5 w-4.5 text-vana-forest" />
                <span>Personnel Directory ({userData?.total || 0})</span>
              </CardTitle>
              <CardDescription className="text-xs">
                {isAdmin
                  ? "Organization-wide user roster with administrative provisioning authority."
                  : "Personnel roster scoped to projects under your active management."}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="neutral" className="text-[11px] font-mono">
                Actor: {currentUser?.role}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 flex flex-col items-center justify-center gap-3 text-vana-charcoal/60">
              <Loader2 className="h-6 w-6 animate-spin text-vana-forest" />
              <span className="text-xs">Loading authorized user directory...</span>
            </div>
          ) : isError ? (
            <div className="p-8 text-center text-xs text-vana-crimson">
              Failed to load directory: {String((error as Error)?.message || "Network error")}
            </div>
          ) : !userData?.users || userData.users.length === 0 ? (
            <div className="p-8 text-center text-xs text-vana-charcoal/60">
              No users found matching current authorization scope.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-vana-ivory/50 border-b border-vana-charcoal/10 text-vana-charcoal/70 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-4 py-3 font-semibold">User</th>
                    <th className="px-4 py-3 font-semibold">Email</th>
                    <th className="px-4 py-3 font-semibold">Role</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold">Created</th>
                    {isAdmin && <th className="px-4 py-3 font-semibold text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-vana-charcoal/10">
                  {userData.users.map((u) => {
                    const isSelf = u.id === currentUser?.id;
                    return (
                      <tr key={u.id} className="hover:bg-vana-sage/5 transition-colors">
                        <td className="px-4 py-3 font-medium text-vana-charcoal flex items-center gap-2">
                          <span>{u.full_name}</span>
                          {isSelf && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-vana-forest/10 text-vana-forest font-semibold">
                              You
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-vana-charcoal/80 font-mono text-[11px]">
                          {u.email}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={getRoleVariant(u.role)} className="text-[10px]">
                            {u.role}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          {u.is_active ? (
                            <Badge variant="verified" className="text-[10px]">
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="rejected" className="text-[10px]">
                              Deactivated
                            </Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 text-vana-charcoal/60 text-[11px]">
                          {new Date(u.created_at).toLocaleDateString()}
                        </td>
                        {isAdmin && (
                          <td className="px-4 py-3 text-right">
                            {!isSelf && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  toggleActiveMutation.mutate({
                                    id: u.id,
                                    is_active: !u.is_active,
                                  })
                                }
                                disabled={toggleActiveMutation.isPending}
                                className={`h-7 px-2 text-[11px] ${
                                  u.is_active
                                    ? "text-vana-crimson hover:bg-vana-crimson/10"
                                    : "text-emerald-700 hover:bg-emerald-50"
                                }`}
                              >
                                {u.is_active ? (
                                  <>
                                    <PowerOff className="h-3 w-3 mr-1" />
                                    <span>Deactivate</span>
                                  </>
                                ) : (
                                  <>
                                    <Power className="h-3 w-3 mr-1" />
                                    <span>Activate</span>
                                  </>
                                )}
                              </Button>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Provision User Modal Dialog */}
      {isAdmin && (
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-vana-forest" />
                <span>Provision Organization User</span>
              </DialogTitle>
              <DialogDescription className="text-xs">
                Creates a new user account with initial role. Action will be recorded in immutable audit log.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit(onProvisionSubmit)} className="space-y-3.5 py-2">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-vana-charcoal">Full Name</label>
                <Input
                  placeholder="e.g. Ananya Sharma"
                  disabled={isSubmitting}
                  className={errors.full_name ? "border-vana-crimson" : ""}
                  {...register("full_name")}
                />
                {errors.full_name && (
                  <p className="text-[11px] text-vana-crimson">{errors.full_name.message}</p>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-vana-charcoal">Email Address</label>
                <Input
                  type="email"
                  placeholder="user@akshayavana.com"
                  disabled={isSubmitting}
                  className={errors.email ? "border-vana-crimson" : ""}
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-[11px] text-vana-crimson">{errors.email.message}</p>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-vana-charcoal">Initial Password</label>
                <Input
                  type="password"
                  placeholder="Minimum 8 characters"
                  disabled={isSubmitting}
                  className={errors.password ? "border-vana-crimson" : ""}
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-[11px] text-vana-crimson">{errors.password.message}</p>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-vana-charcoal">Assigned Role</label>
                <select
                  disabled={isSubmitting}
                  className="w-full px-3 py-2 text-xs rounded-md border border-vana-charcoal/20 bg-white text-vana-charcoal focus:outline-none focus:ring-2 focus:ring-vana-forest"
                  {...register("role")}
                >
                  <option value="FIELD_OFFICER">FIELD_OFFICER (Assigned Project Submissions)</option>
                  <option value="PROJECT_MANAGER">PROJECT_MANAGER (Project Management &amp; Verification)</option>
                  <option value="ADMIN">ADMIN (Organization-Wide Authority)</option>
                </select>
                {errors.role && (
                  <p className="text-[11px] text-vana-crimson">{errors.role.message}</p>
                )}
              </div>

              <DialogFooter className="pt-3 gap-2 sm:gap-0">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDialogOpen(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="default" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                      <span>Provisioning...</span>
                    </>
                  ) : (
                    <span>Create User</span>
                  )}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}
    </PageContainer>
  );
};

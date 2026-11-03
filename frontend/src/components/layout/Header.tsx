import React from "react";
import { Menu, UserCircle2, LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { HealthIndicator } from "@/components/shared/HealthIndicator";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface HeaderProps {
  onMenuClick: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  const { user, logout } = useAuth();

  const getRoleBadgeVariant = (role?: string) => {
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
    <header className="h-16 border-b border-vana-charcoal/10 bg-white/80 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          className="lg:hidden text-vana-charcoal"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </Button>
        <div className="hidden sm:block">
          <span className="text-xs font-semibold text-vana-charcoal/60 uppercase tracking-wider block">
            Environmental Operations
          </span>
          <span className="text-sm font-bold text-vana-forest font-heading">
            Akshaya Vana Platform
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* Backend Live Health Probe */}
        <HealthIndicator />

        {/* Authenticated User Profile Pill */}
        {user && (
          <div className="flex items-center gap-2.5 pl-3 border-l border-vana-charcoal/10">
            <div className="h-8 w-8 rounded-full bg-vana-forest/10 flex items-center justify-center text-vana-forest">
              <UserCircle2 className="h-5 w-5" />
            </div>
            <div className="hidden md:block text-left text-xs">
              <div className="font-semibold text-vana-charcoal flex items-center gap-1.5">
                <span>{user.full_name}</span>
                <Badge variant={getRoleBadgeVariant(user.role)} className="text-[10px] py-0 px-1.5">
                  {user.role}
                </Badge>
              </div>
              <div className="text-[10px] text-vana-charcoal/60">{user.email}</div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => logout()}
              className="h-8 w-8 text-vana-charcoal/60 hover:text-vana-crimson hover:bg-vana-crimson/10 transition-colors"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </header>
  );
};

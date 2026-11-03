import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  Map as MapIcon,
  ClipboardList,
  ShieldCheck,
  BarChart3,
  Users,
  History,
  Trees,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { UserRole } from "@/types";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  allowedRoles?: UserRole[];
}

const navigation: NavItem[] = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Projects", href: "/projects", icon: FolderKanban },
  { name: "Living Earth Map", href: "/map", icon: MapIcon },
  { name: "Field Operations", href: "/operations", icon: ClipboardList },
  {
    name: "Verification Centre",
    href: "/verification",
    icon: ShieldCheck,
    allowedRoles: ["ADMIN", "PROJECT_MANAGER"],
  },
  { name: "Impact Analytics", href: "/analytics", icon: BarChart3 },
  {
    name: "Team Management",
    href: "/team",
    icon: Users,
    allowedRoles: ["ADMIN", "PROJECT_MANAGER"],
  },
  {
    name: "Audit History",
    href: "/audit",
    icon: History,
    allowedRoles: ["ADMIN"],
  },
];

export const Sidebar: React.FC<{ className?: string; onClose?: () => void }> = ({
  className,
  onClose,
}) => {
  const { user } = useAuth();

  const filteredNavigation = navigation.filter((item) => {
    if (!item.allowedRoles) return true;
    if (!user) return false;
    return item.allowedRoles.includes(user.role);
  });

  return (
    <aside
      className={cn(
        "flex flex-col w-64 border-r border-vana-charcoal/10 bg-white h-screen select-none",
        className
      )}
    >
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-6 h-16 border-b border-vana-charcoal/10 bg-white">
        <div className="h-9 w-9 rounded-lg bg-vana-forest text-white flex items-center justify-center shadow-subtle">
          <Trees className="h-5 w-5 text-vana-sage" />
        </div>
        <div>
          <span className="font-heading font-extrabold text-xl tracking-tight text-vana-forest leading-none block">
            VANA
          </span>
          <span className="text-[10px] text-vana-charcoal/60 font-medium tracking-wide block uppercase mt-0.5">
            Akshaya Vana Ventures
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {filteredNavigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-vana-forest text-white shadow-subtle"
                  : "text-vana-charcoal/80 hover:bg-vana-sage/15 hover:text-vana-forest"
              )
            }
          >
            <item.icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-vana-charcoal/10 bg-vana-ivory/30">
        <div className="text-xs text-vana-charcoal/60 space-y-1">
          <div className="font-semibold text-vana-forest">VANA Platform v0.1.0</div>
          <div>Ground Truth &amp; Operations</div>
        </div>
      </div>
    </aside>
  );
};

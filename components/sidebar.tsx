"use client"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  BarChart3,
  TrendingUp,
  Wallet,
  Settings,
  BookOpen,
  Target,
  AlertTriangle,
  Activity,
  Layout,
} from "lucide-react"

interface SidebarProps {
  activeView: string
  onViewChange: (view: string) => void
}

const navigation = [
  { id: "dashboard", label: "Dashboard", icon: BarChart3 },
  { id: "positions", label: "Positions", icon: Wallet },
  { id: "watchlist", label: "Watchlist", icon: TrendingUp },
  { id: "orders", label: "Orders", icon: Target },
  { id: "alerts", label: "Alerts", icon: AlertTriangle },
  { id: "analytics", label: "Analytics", icon: Activity },
  { id: "journal", label: "Journal", icon: BookOpen },
  { id: "config", label: "Layout", icon: Layout },
  { id: "settings", label: "Settings", icon: Settings },
]

export function Sidebar({ activeView, onViewChange }: SidebarProps) {
  return (
    <nav className="bg-sidebar border-r border-sidebar-border p-4 row-span-1">
      <div className="space-y-2">
        {navigation.map((item) => {
          const Icon = item.icon
          return (
            <Button
              key={item.id}
              variant={activeView === item.id ? "default" : "ghost"}
              className={cn(
                "w-full justify-start gap-3 text-sidebar-foreground",
                activeView === item.id && "bg-sidebar-primary text-sidebar-primary-foreground",
              )}
              onClick={() => onViewChange(item.id)}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Button>
          )
        })}
      </div>
    </nav>
  )
}

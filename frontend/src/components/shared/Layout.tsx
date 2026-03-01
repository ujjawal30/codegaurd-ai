import { Link, Outlet, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Shield, Upload, Clock } from "lucide-react";

export default function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-emerald-600 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="text-[15px] font-semibold text-foreground">CodeGuard AI</span>
          </Link>

          <nav className="flex items-center gap-1">
            <Button variant="ghost" size="sm" asChild className={location.pathname === "/history" ? "text-foreground" : "text-muted-foreground"}>
              <Link to="/history">
                <Clock className="w-4 h-4 mr-1.5" />
                History
              </Link>
            </Button>
            <Button size="sm" asChild className="bg-emerald-600 hover:bg-emerald-700 text-white">
              <Link to="/">
                <Upload className="w-4 h-4 mr-1.5" />
                New Audit
              </Link>
            </Button>
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-5 mt-auto">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-emerald-600" />
            <span>CodeGuard AI © 2026</span>
          </div>
          <div className="flex gap-6">
            <Link to="#" className="hover:text-foreground transition-colors">
              Docs
            </Link>
            <Link to="#" className="hover:text-foreground transition-colors">
              API
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

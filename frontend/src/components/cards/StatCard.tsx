import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  bg: string;
}

export default function StatCard({ label, value, icon, color, bg }: StatCardProps) {
  return (
    <Card className="py-4">
      <CardContent className="flex items-center gap-4 px-4">
        <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center shrink-0 ${color}`}>{icon}</div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold tracking-tight">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

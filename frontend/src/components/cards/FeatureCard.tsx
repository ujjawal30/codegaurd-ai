import { Card, CardContent } from "@/components/ui/card";

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  desc: string;
  color: string;
  bg: string;
}

export default function FeatureCard({ icon, title, desc, color, bg }: FeatureCardProps) {
  return (
    <Card className="bg-card">
      <CardContent className="px-5 flex items-start gap-3">
        <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center shrink-0 ${color}`}>{icon}</div>
        <div>
          <h3 className="text-sm font-medium mb-0.5">{title}</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Empty({ label }: { label: string }) {
  return <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">{label}</div>;
}

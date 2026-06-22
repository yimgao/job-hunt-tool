interface Props {
  score: number
}

const tiers = [
  { min: 0.6, label: 'High Match', className: 'bg-green-100 text-green-700' },
  { min: 0.3, label: 'Partial', className: 'bg-amber-100 text-amber-700' },
  { min: 0, label: 'Low', className: 'bg-gray-100 text-gray-500' },
]

export default function ScoreBadge({ score }: Props) {
  const tier = tiers.find(t => score >= t.min) ?? tiers[tiers.length - 1]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${tier.className}`}>
      <span className="font-bold">{(score * 100).toFixed(0)}%</span>
      <span>{tier.label}</span>
    </span>
  )
}

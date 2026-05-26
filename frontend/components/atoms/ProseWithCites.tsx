'use client'

import { Citation } from './Citation'

type Props = {
  text:          string
  onCiteClick?:  (n: number) => void
  onCiteHover?:  (n: number) => void
  onCiteLeave?:  () => void
}

export function ProseWithCites({ text, onCiteClick, onCiteHover, onCiteLeave }: Props) {
  const parts = text.split(/\[(\d+)\]/)

  return (
    <span>
      {parts.map((part, i) => {
        if (i % 2 === 1) {
          const n = parseInt(part, 10)
          return (
            <Citation
              key={i}
              n={n}
              onClick={onCiteClick}
              onHover={onCiteHover}
              onLeave={onCiteLeave}
            />
          )
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}

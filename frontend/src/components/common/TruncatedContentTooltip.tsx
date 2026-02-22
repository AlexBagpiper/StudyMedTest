import { useState, useEffect, useRef, useCallback } from 'react'
import { Box, Tooltip } from '@mui/material'

export function TruncatedContentTooltip({ content }: { content: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [truncated, setTruncated] = useState(false)

  const checkTruncated = useCallback(() => {
    const el = ref.current
    if (!el) return
    setTruncated(el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth)
  }, [])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    checkTruncated()
    const observer = new ResizeObserver(checkTruncated)
    observer.observe(el)
    return () => observer.disconnect()
  }, [content, checkTruncated])

  return (
    <Tooltip
      title={truncated ? content : ''}
      placement="top-start"
      disableHoverListener={!truncated}
      componentsProps={{
        tooltip: {
          sx: {
            maxWidth: 620,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontWeight: 300,
            fontSize: '0.9rem',
            lineHeight: 1.5
          }
        }
      }}
    >
      <Box
        ref={ref}
        sx={{
          display: '-webkit-box',
          WebkitLineClamp: 1,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          fontWeight: 500,
          fontSize: '0.875rem',
          lineHeight: 1.43
        }}
      >
        {content}
      </Box>
    </Tooltip>
  )
}

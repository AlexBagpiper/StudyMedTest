import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TruncatedContentTooltip } from '../TruncatedContentTooltip'

describe('TruncatedContentTooltip', () => {
  it('renders content text', () => {
    render(<TruncatedContentTooltip content="Short text" />)
    expect(screen.getByText('Short text')).toBeInTheDocument()
  })

  it('renders empty content without crashing', () => {
    render(<TruncatedContentTooltip content="" />)
    const wrapper = document.querySelector('.MuiBox-root')
    expect(wrapper).toBeInTheDocument()
  })

  it('renders long content', () => {
    const long = 'A'.repeat(500)
    render(<TruncatedContentTooltip content={long} />)
    expect(screen.getByText(long)).toBeInTheDocument()
  })
})

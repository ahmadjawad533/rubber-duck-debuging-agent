import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DuckMascot } from '../components/DuckMascot';

describe('DuckMascot component', () => {
  it('renders correctly in idle state with proper accessible label', () => {
    render(<DuckMascot state="idle" />);
    const duckElement = screen.getByRole('img', { name: /Rubber Duck mascot in idle state/i });
    expect(duckElement).toBeInTheDocument();
  });

  it('renders thinking state indicators', () => {
    render(<DuckMascot state="thinking" />);
    const duckElement = screen.getByRole('img', { name: /Rubber Duck mascot in thinking state/i });
    expect(duckElement).toBeInTheDocument();
  });

  it('renders celebrating state', () => {
    render(<DuckMascot state="celebrating" />);
    const duckElement = screen.getByRole('img', { name: /Rubber Duck mascot in celebrating state/i });
    expect(duckElement).toBeInTheDocument();
  });

  it('renders napping state with zZz indicator', () => {
    render(<DuckMascot state="napping" />);
    const duckElement = screen.getByRole('img', { name: /Rubber Duck mascot in napping state/i });
    expect(duckElement).toBeInTheDocument();
    expect(screen.getByText('zZz')).toBeInTheDocument();
  });
});

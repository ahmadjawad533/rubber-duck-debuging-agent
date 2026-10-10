import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Composer } from '../components/Composer';

describe('Composer component', () => {
  it('renders textarea and action chips', () => {
    render(<Composer />);
    expect(screen.getByRole('textbox', { name: /Debug message composer/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Ask for a hint/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Request the full explanation and fix/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mark bug as solved/i })).toBeInTheDocument();
  });

  it('updates text input and shows character counter', () => {
    render(<Composer />);
    const textarea = screen.getByRole('textbox', { name: /Debug message composer/i });
    fireEvent.change(textarea, { target: { value: 'TypeError: x is not a function' } });
    expect(textarea).toHaveValue('TypeError: x is not a function');
    expect(screen.getByText(/30\/4000/)).toBeInTheDocument();
  });

  it('toggles code mode on button click', () => {
    render(<Composer />);
    const codeModeBtn = screen.getByRole('button', { name: /Switch to code paste mode/i });
    fireEvent.click(codeModeBtn);
    expect(screen.getByRole('textbox')).toHaveClass('font-mono');
  });
});

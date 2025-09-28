import { render, screen } from '@testing-library/react';
import { Button } from './button';
import { describe, it, expect } from 'vitest';

describe('Button Component', () => {
  it('renders with default variant and size', () => {
    render(<Button>Default Button</Button>);
    const button = screen.getByRole('button', { name: 'Default Button' });
    
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary', 'text-primary-foreground');
    expect(button).toHaveClass('h-10', 'px-4', 'py-2');
  });

  it('renders with destructive variant', () => {
    render(<Button variant="destructive">Destructive Button</Button>);
    const button = screen.getByRole('button', { name: 'Destructive Button' });
    
    expect(button).toHaveClass('bg-destructive', 'text-destructive-foreground');
  });

  it('renders with outline variant', () => {
    render(<Button variant="outline">Outline Button</Button>);
    const button = screen.getByRole('button', { name: 'Outline Button' });
    
    expect(button).toHaveClass('border', 'border-input', 'bg-background');
  });

  it('renders with secondary variant', () => {
    render(<Button variant="secondary">Secondary Button</Button>);
    const button = screen.getByRole('button', { name: 'Secondary Button' });
    
    expect(button).toHaveClass('bg-secondary', 'text-secondary-foreground');
  });

  it('renders with ghost variant', () => {
    render(<Button variant="ghost">Ghost Button</Button>);
    const button = screen.getByRole('button', { name: 'Ghost Button' });
    
    expect(button).toHaveClass('hover:bg-accent', 'hover:text-accent-foreground');
  });

  it('renders with link variant', () => {
    render(<Button variant="link">Link Button</Button>);
    const button = screen.getByRole('button', { name: 'Link Button' });
    
    expect(button).toHaveClass('text-primary', 'underline-offset-4');
  });

  it('renders with small size', () => {
    render(<Button size="sm">Small Button</Button>);
    const button = screen.getByRole('button', { name: 'Small Button' });
    
    expect(button).toHaveClass('h-9', 'px-3');
  });

  it('renders with large size', () => {
    render(<Button size="lg">Large Button</Button>);
    const button = screen.getByRole('button', { name: 'Large Button' });
    
    expect(button).toHaveClass('h-11', 'px-8');
  });

  it('renders with icon size', () => {
    render(<Button size="icon">Icon</Button>);
    const button = screen.getByRole('button', { name: 'Icon' });
    
    expect(button).toHaveClass('h-10', 'w-10');
  });

  it('applies custom className', () => {
    render(<Button className="custom-class">Custom Button</Button>);
    const button = screen.getByRole('button', { name: 'Custom Button' });
    
    expect(button).toHaveClass('custom-class');
  });

  it('handles disabled state', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: 'Disabled Button' });
    
    expect(button).toBeDisabled();
    expect(button).toHaveClass('disabled:pointer-events-none', 'disabled:opacity-50');
  });

  it('renders as child component when asChild is true', () => {
    render(
      <Button asChild>
        <a href="#">Link as Button</a>
      </Button>
    );
    
    const link = screen.getByRole('link', { name: 'Link as Button' });
    expect(link).toBeInTheDocument();
    expect(link.tagName).toBe('A');
  });
});
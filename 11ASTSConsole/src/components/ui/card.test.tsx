import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './card';
import { describe, it, expect } from 'vitest';

describe('Card Components', () => {
  describe('Card', () => {
    it('renders with default classes', () => {
      render(<Card data-testid="card">Card Content</Card>);
      const card = screen.getByTestId('card');
      
      expect(card).toBeInTheDocument();
      expect(card).toHaveClass('rounded-lg', 'border', 'bg-card', 'text-card-foreground', 'shadow-sm');
    });

    it('applies custom className', () => {
      render(<Card className="custom-card" data-testid="card">Card Content</Card>);
      const card = screen.getByTestId('card');
      
      expect(card).toHaveClass('custom-card');
    });
  });

  describe('CardHeader', () => {
    it('renders with default classes', () => {
      render(<CardHeader data-testid="card-header">Header Content</CardHeader>);
      const header = screen.getByTestId('card-header');
      
      expect(header).toBeInTheDocument();
      expect(header).toHaveClass('flex', 'flex-col', 'space-y-1.5', 'p-6');
    });

    it('applies custom className', () => {
      render(<CardHeader className="custom-header" data-testid="card-header">Header Content</CardHeader>);
      const header = screen.getByTestId('card-header');
      
      expect(header).toHaveClass('custom-header');
    });
  });

  describe('CardTitle', () => {
    it('renders as h3 with default classes', () => {
      render(<CardTitle>Card Title</CardTitle>);
      const title = screen.getByRole('heading', { level: 3 });
      
      expect(title).toBeInTheDocument();
      expect(title).toHaveTextContent('Card Title');
      expect(title).toHaveClass('text-2xl', 'font-semibold', 'leading-none', 'tracking-tight');
    });

    it('applies custom className', () => {
      render(<CardTitle className="custom-title">Card Title</CardTitle>);
      const title = screen.getByRole('heading', { level: 3 });
      
      expect(title).toHaveClass('custom-title');
    });
  });

  describe('CardDescription', () => {
    it('renders with default classes', () => {
      render(<CardDescription data-testid="card-description">Card Description</CardDescription>);
      const description = screen.getByTestId('card-description');
      
      expect(description).toBeInTheDocument();
      expect(description).toHaveTextContent('Card Description');
      expect(description).toHaveClass('text-sm', 'text-muted-foreground');
    });

    it('applies custom className', () => {
      render(<CardDescription className="custom-description" data-testid="card-description">Card Description</CardDescription>);
      const description = screen.getByTestId('card-description');
      
      expect(description).toHaveClass('custom-description');
    });
  });

  describe('CardContent', () => {
    it('renders with default classes', () => {
      render(<CardContent data-testid="card-content">Card Content</CardContent>);
      const content = screen.getByTestId('card-content');
      
      expect(content).toBeInTheDocument();
      expect(content).toHaveTextContent('Card Content');
      expect(content).toHaveClass('p-6', 'pt-0');
    });

    it('applies custom className', () => {
      render(<CardContent className="custom-content" data-testid="card-content">Card Content</CardContent>);
      const content = screen.getByTestId('card-content');
      
      expect(content).toHaveClass('custom-content');
    });
  });

  describe('CardFooter', () => {
    it('renders with default classes', () => {
      render(<CardFooter data-testid="card-footer">Card Footer</CardFooter>);
      const footer = screen.getByTestId('card-footer');
      
      expect(footer).toBeInTheDocument();
      expect(footer).toHaveTextContent('Card Footer');
      expect(footer).toHaveClass('flex', 'items-center', 'p-6', 'pt-0');
    });

    it('applies custom className', () => {
      render(<CardFooter className="custom-footer" data-testid="card-footer">Card Footer</CardFooter>);
      const footer = screen.getByTestId('card-footer');
      
      expect(footer).toHaveClass('custom-footer');
    });
  });

  describe('Complete Card Structure', () => {
    it('renders a complete card with all components', () => {
      render(
        <Card data-testid="complete-card">
          <CardHeader>
            <CardTitle>Test Card Title</CardTitle>
            <CardDescription>Test card description</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Test card content</p>
          </CardContent>
          <CardFooter>
            <button>Action Button</button>
          </CardFooter>
        </Card>
      );

      const card = screen.getByTestId('complete-card');
      const title = screen.getByRole('heading', { level: 3 });
      const description = screen.getByText('Test card description');
      const content = screen.getByText('Test card content');
      const button = screen.getByRole('button', { name: 'Action Button' });

      expect(card).toBeInTheDocument();
      expect(title).toHaveTextContent('Test Card Title');
      expect(description).toBeInTheDocument();
      expect(content).toBeInTheDocument();
      expect(button).toBeInTheDocument();
    });
  });
});
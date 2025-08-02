/**
 * Tests for MarketIndicesDisplay component
 */

import { render, screen } from '@testing-library/react';
import { MarketIndex } from '../../types';
import MarketIndicesDisplay from '../MarketIndicesDisplay';

const mockIndices: MarketIndex[] = [
  {
    name: 'Nikkei 225',
    symbol: 'N225',
    value: 30000.50,
    change: 150.25,
    change_percent: 0.50,
    volume: 1500000000,
    updated_at: '2024-01-15T06:00:00Z',
  },
  {
    name: 'TOPIX',
    symbol: 'TOPIX',
    value: 2100.75,
    change: -25.50,
    change_percent: -1.20,
    volume: 2000000000,
    updated_at: '2024-01-15T06:00:00Z',
  },
  {
    name: 'Mothers',
    symbol: 'MOTHERS',
    value: 850.25,
    change: 10.75,
    change_percent: 1.28,
    updated_at: '2024-01-15T06:00:00Z',
  },
];

describe('MarketIndicesDisplay Component', () => {
  it('renders loading state correctly', () => {
    render(<MarketIndicesDisplay indices={[]} isLoading={true} />);

    // Should show skeleton loading cards
    const skeletonCards = screen.getAllByRole('generic');
    expect(skeletonCards.length).toBeGreaterThan(0);
    
    // Check for animate-pulse class
    const animatedElements = document.querySelectorAll('.animate-pulse');
    expect(animatedElements.length).toBeGreaterThan(0);
  });

  it('renders empty state when no indices available', () => {
    render(<MarketIndicesDisplay indices={[]} isLoading={false} />);

    expect(screen.getByText('Market indices data unavailable')).toBeInTheDocument();
    expect(screen.getByText('Please try refreshing the page')).toBeInTheDocument();
  });

  it('renders market indices correctly', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    // Check that all indices are displayed
    expect(screen.getByText('Nikkei 225')).toBeInTheDocument();
    expect(screen.getByText('TOPIX')).toBeInTheDocument();
    expect(screen.getByText('Mothers')).toBeInTheDocument();

    // Check symbols
    expect(screen.getByText('N225')).toBeInTheDocument();
    expect(screen.getByText('TOPIX')).toBeInTheDocument();
    expect(screen.getByText('MOTHERS')).toBeInTheDocument();
  });

  it('formats values correctly', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    // Check formatted values
    expect(screen.getByText('30,000.50')).toBeInTheDocument();
    expect(screen.getByText('2,100.75')).toBeInTheDocument();
    expect(screen.getByText('850.25')).toBeInTheDocument();
  });

  it('displays positive changes with correct styling', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    // Check positive change for Nikkei 225
    const positiveChange = screen.getByText('+150.25 (+0.50%)');
    expect(positiveChange).toBeInTheDocument();
    expect(positiveChange).toHaveClass('text-success-600');
    expect(positiveChange.parentElement).toHaveClass('bg-success-50');

    // Check positive change for Mothers
    const mothersChange = screen.getByText('+10.75 (+1.28%)');
    expect(mothersChange).toBeInTheDocument();
    expect(mothersChange).toHaveClass('text-success-600');
  });

  it('displays negative changes with correct styling', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    // Check negative change for TOPIX
    const negativeChange = screen.getByText('-25.50 (-1.20%)');
    expect(negativeChange).toBeInTheDocument();
    expect(negativeChange).toHaveClass('text-danger-600');
    expect(negativeChange.parentElement).toHaveClass('bg-danger-50');
  });

  it('displays volume information when available', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    // Check volume display (should be formatted compactly)
    expect(screen.getByText('1.5B')).toBeInTheDocument(); // 1.5 billion
    expect(screen.getByText('2B')).toBeInTheDocument(); // 2 billion
  });

  it('shows correct icons for different indices', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    // Icons are emojis, so we check for their presence in the document
    const container = screen.getByText('Nikkei 225').closest('div');
    expect(container).toHaveTextContent('📈');

    const topixContainer = screen.getByText('TOPIX').closest('div');
    expect(topixContainer).toHaveTextContent('📊');

    const mothersContainer = screen.getByText('Mothers').closest('div');
    expect(mothersContainer).toHaveTextContent('🚀');
  });

  it('displays update timestamps', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    // Should show formatted update times
    const updateTexts = screen.getAllByText(/Updated:/);
    expect(updateTexts.length).toBe(mockIndices.length);
  });

  it('shows index descriptions', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    expect(screen.getByText("Japan's premier stock index of 225 companies")).toBeInTheDocument();
    expect(screen.getByText('Tokyo Stock Price Index of all TSE companies')).toBeInTheDocument();
    expect(screen.getByText('Market for emerging and growth companies')).toBeInTheDocument();
  });

  it('handles indices without volume gracefully', () => {
    const indicesWithoutVolume: MarketIndex[] = [
      {
        name: 'Test Index',
        symbol: 'TEST',
        value: 1000,
        change: 10,
        change_percent: 1.0,
        updated_at: '2024-01-15T06:00:00Z',
      },
    ];

    render(<MarketIndicesDisplay indices={indicesWithoutVolume} isLoading={false} />);

    expect(screen.getByText('Test Index')).toBeInTheDocument();
    expect(screen.getByText('1,000.00')).toBeInTheDocument();
    
    // Should not show volume section
    expect(screen.queryByText('Volume')).not.toBeInTheDocument();
  });

  it('applies hover effects correctly', () => {
    render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    const indexCards = screen.getAllByText(/Nikkei 225|TOPIX|Mothers/);
    indexCards.forEach(card => {
      const cardContainer = card.closest('div');
      expect(cardContainer).toHaveClass('hover:shadow-md');
      expect(cardContainer).toHaveClass('transition-shadow');
    });
  });

  it('uses responsive grid layout', () => {
    const { container } = render(<MarketIndicesDisplay indices={mockIndices} isLoading={false} />);

    const gridContainer = container.querySelector('.grid');
    expect(gridContainer).toHaveClass('grid-cols-1');
    expect(gridContainer).toHaveClass('md:grid-cols-2');
    expect(gridContainer).toHaveClass('lg:grid-cols-3');
  });

  it('handles zero change values correctly', () => {
    const indicesWithZeroChange: MarketIndex[] = [
      {
        name: 'Flat Index',
        symbol: 'FLAT',
        value: 1000,
        change: 0,
        change_percent: 0,
        updated_at: '2024-01-15T06:00:00Z',
      },
    ];

    render(<MarketIndicesDisplay indices={indicesWithZeroChange} isLoading={false} />);

    const changeElement = screen.getByText('+0.00 (+0.00%)');
    expect(changeElement).toBeInTheDocument();
    expect(changeElement).toHaveClass('text-success-600'); // Zero is treated as positive
  });

  it('formats large numbers correctly', () => {
    const indicesWithLargeNumbers: MarketIndex[] = [
      {
        name: 'Large Index',
        symbol: 'LARGE',
        value: 123456.789,
        change: 1234.56,
        change_percent: 1.0,
        volume: 9876543210,
        updated_at: '2024-01-15T06:00:00Z',
      },
    ];

    render(<MarketIndicesDisplay indices={indicesWithLargeNumbers} isLoading={false} />);

    expect(screen.getByText('123,456.79')).toBeInTheDocument();
    expect(screen.getByText('+1,234.56 (+1.00%)')).toBeInTheDocument();
    expect(screen.getByText('9.9B')).toBeInTheDocument(); // Volume formatted compactly
  });
});
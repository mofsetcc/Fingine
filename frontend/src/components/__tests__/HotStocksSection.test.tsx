/**
 * Tests for HotStocksSection component
 */

import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { HotStock } from '../../types';
import HotStocksSection from '../HotStocksSection';

// Mock react-router-dom
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const mockHotStocks: HotStock[] = [
  // Gainers
  {
    ticker: '7203',
    company_name: 'トヨタ自動車',
    price: 2000,
    change: 100,
    change_percent: 5.26,
    volume: 15000000,
    category: 'gainer',
  },
  {
    ticker: '6758',
    company_name: 'ソニーグループ',
    price: 12000,
    change: 500,
    change_percent: 4.35,
    volume: 8000000,
    category: 'gainer',
  },
  {
    ticker: '9984',
    company_name: 'ソフトバンクグループ',
    price: 5500,
    change: 200,
    change_percent: 3.77,
    volume: 12000000,
    category: 'gainer',
  },
  // Losers
  {
    ticker: '8306',
    company_name: '三菱UFJフィナンシャル・グループ',
    price: 800,
    change: -50,
    change_percent: -5.88,
    volume: 20000000,
    category: 'loser',
  },
  {
    ticker: '9432',
    company_name: '日本電信電話',
    price: 3500,
    change: -150,
    change_percent: -4.11,
    volume: 6000000,
    category: 'loser',
  },
  // Most traded
  {
    ticker: '1301',
    company_name: '極洋',
    price: 1200,
    change: 25,
    change_percent: 2.13,
    volume: 50000000,
    category: 'most_traded',
  },
  {
    ticker: '2914',
    company_name: '日本たばこ産業',
    price: 2800,
    change: -10,
    change_percent: -0.36,
    volume: 45000000,
    category: 'most_traded',
  },
];

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('HotStocksSection Component', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders loading state correctly', () => {
    renderWithRouter(<HotStocksSection hotStocks={[]} isLoading={true} />);

    // Should show skeleton loading for tabs
    const skeletonElements = document.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('renders tabs correctly', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    expect(screen.getByText('Top Gainers')).toBeInTheDocument();
    expect(screen.getByText('Top Losers')).toBeInTheDocument();
    expect(screen.getByText('Most Traded')).toBeInTheDocument();
  });

  it('shows gainers by default', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    // Should show gainer stocks
    expect(screen.getByText('7203')).toBeInTheDocument();
    expect(screen.getByText('トヨタ自動車')).toBeInTheDocument();
    expect(screen.getByText('6758')).toBeInTheDocument();
    expect(screen.getByText('ソニーグループ')).toBeInTheDocument();
  });

  it('switches tabs correctly', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    // Click on losers tab
    fireEvent.click(screen.getByText('Top Losers'));

    // Should show loser stocks
    expect(screen.getByText('8306')).toBeInTheDocument();
    expect(screen.getByText('三菱UFJフィナンシャル・グループ')).toBeInTheDocument();
    expect(screen.getByText('9432')).toBeInTheDocument();

    // Click on most traded tab
    fireEvent.click(screen.getByText('Most Traded'));

    // Should show most traded stocks
    expect(screen.getByText('1301')).toBeInTheDocument();
    expect(screen.getByText('極洋')).toBeInTheDocument();
    expect(screen.getByText('2914')).toBeInTheDocument();
  });

  it('formats prices correctly', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    expect(screen.getByText('¥2,000')).toBeInTheDocument();
    expect(screen.getByText('¥12,000')).toBeInTheDocument();
    expect(screen.getByText('¥5,500')).toBeInTheDocument();
  });

  it('formats positive changes correctly', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    const positiveChanges = screen.getAllByText(/\+100\.00 \(\+5\.26%\)/);
    expect(positiveChanges.length).toBeGreaterThan(0);
    
    positiveChanges.forEach(change => {
      expect(change).toHaveClass('text-success-600');
    });
  });

  it('formats negative changes correctly', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    // Switch to losers tab to see negative changes
    fireEvent.click(screen.getByText('Top Losers'));

    const negativeChanges = screen.getAllByText(/-50\.00 \(-5\.88%\)/);
    expect(negativeChanges.length).toBeGreaterThan(0);
    
    negativeChanges.forEach(change => {
      expect(change).toHaveClass('text-danger-600');
    });
  });

  it('formats volume correctly', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    expect(screen.getByText('Vol: 15M')).toBeInTheDocument(); // 15 million
    expect(screen.getByText('Vol: 8M')).toBeInTheDocument(); // 8 million
  });

  it('shows ranking numbers and medals', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    // Check for ranking numbers
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();

    // Check for medal emojis (top 3)
    const container = screen.getByText('1').closest('div');
    expect(container).toHaveTextContent('🥇');
  });

  it('navigates to stock page when clicked', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    const toyotaStock = screen.getByText('トヨタ自動車').closest('div');
    fireEvent.click(toyotaStock!);

    expect(mockNavigate).toHaveBeenCalledWith('/stocks/7203');
  });

  it('shows hover effects on stock items', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    const stockItems = screen.getAllByText(/Vol: \d+/);
    stockItems.forEach(item => {
      const stockContainer = item.closest('div');
      expect(stockContainer).toHaveClass('hover:bg-gray-100');
      expect(stockContainer).toHaveClass('cursor-pointer');
    });
  });

  it('shows empty state when no stocks available', () => {
    renderWithRouter(<HotStocksSection hotStocks={[]} isLoading={false} />);

    expect(screen.getByText('No top gainers data available')).toBeInTheDocument();
    expect(screen.getByText('Data will be updated during market hours')).toBeInTheDocument();
  });

  it('shows correct tab icons', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    // Check for emoji icons in tabs
    expect(screen.getByText('📈')).toBeInTheDocument(); // Gainers
    expect(screen.getByText('📉')).toBeInTheDocument(); // Losers
    expect(screen.getByText('🔥')).toBeInTheDocument(); // Most traded
  });

  it('highlights active tab correctly', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    const gainersTab = screen.getByText('Top Gainers').closest('button');
    expect(gainersTab).toHaveClass('bg-white');
    expect(gainersTab).toHaveClass('text-primary-600');

    // Click losers tab
    const losersTab = screen.getByText('Top Losers').closest('button');
    fireEvent.click(losersTab!);

    expect(losersTab).toHaveClass('bg-white');
    expect(losersTab).toHaveClass('text-primary-600');
  });

  it('limits stocks to top 10', () => {
    // Create more than 10 stocks in one category
    const manyGainers: HotStock[] = Array.from({ length: 15 }, (_, i) => ({
      ticker: `${7000 + i}`,
      company_name: `Company ${i}`,
      price: 1000 + i * 100,
      change: 50 + i * 5,
      change_percent: 2.5 + i * 0.5,
      volume: 1000000 + i * 100000,
      category: 'gainer' as const,
    }));

    renderWithRouter(<HotStocksSection hotStocks={manyGainers} isLoading={false} />);

    // Should only show first 10
    expect(screen.getByText('7000')).toBeInTheDocument();
    expect(screen.getByText('7009')).toBeInTheDocument();
    expect(screen.queryByText('7010')).not.toBeInTheDocument(); // 11th item should not be visible
  });

  it('shows update frequency information', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    expect(screen.getByText('Data updates every 5 minutes during market hours (9:00-15:00 JST)')).toBeInTheDocument();
  });

  it('truncates long company names', () => {
    const stocksWithLongNames: HotStock[] = [
      {
        ticker: '1234',
        company_name: 'Very Long Company Name That Should Be Truncated Because It Is Too Long',
        price: 1000,
        change: 50,
        change_percent: 5.0,
        volume: 1000000,
        category: 'gainer',
      },
    ];

    renderWithRouter(<HotStocksSection hotStocks={stocksWithLongNames} isLoading={false} />);

    const companyNameElement = screen.getByText(/Very Long Company Name/);
    expect(companyNameElement).toHaveClass('truncate');
    expect(companyNameElement).toHaveClass('max-w-48');
  });

  it('applies correct styling for top 3 rankings', () => {
    renderWithRouter(<HotStocksSection hotStocks={mockHotStocks} isLoading={false} />);

    // Check top 3 have special styling
    const firstPlace = screen.getByText('1').closest('div');
    expect(firstPlace).toHaveClass('bg-primary-100');
    expect(firstPlace).toHaveClass('text-primary-600');

    const fourthPlace = screen.getByText('4');
    if (fourthPlace) {
      const fourthContainer = fourthPlace.closest('div');
      expect(fourthContainer).toHaveClass('bg-gray-200');
      expect(fourthContainer).toHaveClass('text-gray-600');
    }
  });
});
/**
 * Tests for NewsAndSentiment component
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { NewsArticle, SentimentSummary, SentimentTimelinePoint } from '../../types/news';
import NewsAndSentiment from '../NewsAndSentiment';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch as any;

// Mock data
// Create recent dates for testing
const now = new Date();
const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
const fourHoursAgo = new Date(now.getTime() - 4 * 60 * 60 * 1000);

const mockArticles: NewsArticle[] = [
  {
    id: '1',
    headline: 'Toyota Reports Strong Q3 Earnings',
    content_summary: 'Toyota Motor Corp reported better-than-expected quarterly earnings...',
    source: 'Nikkei',
    author: 'John Doe',
    published_at: twoHoursAgo.toISOString(),
    article_url: 'https://example.com/article1',
    sentiment_label: 'positive',
    sentiment_score: 0.7,
    language: 'ja',
    relevance_score: 0.9
  },
  {
    id: '2',
    headline: 'Market Volatility Affects Auto Sector',
    content_summary: 'Recent market volatility has impacted automotive stocks...',
    source: 'Reuters Japan',
    published_at: fourHoursAgo.toISOString(),
    article_url: 'https://example.com/article2',
    sentiment_label: 'negative',
    sentiment_score: -0.4,
    language: 'ja',
    relevance_score: 0.6
  }
];

const mockSentimentSummary: SentimentSummary = {
  overall_sentiment: 'positive',
  sentiment_score: 0.2,
  positive_count: 5,
  negative_count: 2,
  neutral_count: 3,
  total_articles: 10
};

const mockSentimentTimeline: SentimentTimelinePoint[] = [
  {
    timestamp: '2024-01-10T00:00:00Z',
    sentiment_score: 0.1,
    article_count: 3,
    positive_count: 2,
    negative_count: 1,
    neutral_count: 0
  },
  {
    timestamp: '2024-01-11T00:00:00Z',
    sentiment_score: 0.3,
    article_count: 5,
    positive_count: 3,
    negative_count: 1,
    neutral_count: 1
  }
];

const mockSuccessResponse = {
  articles: mockArticles,
  sentiment_summary: mockSentimentSummary,
  sentiment_timeline: mockSentimentTimeline,
  total_count: 10,
  has_more: true
};

describe('NewsAndSentiment', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(<NewsAndSentiment ticker="7203" />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('fetches and displays news articles', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Toyota Reports Strong Q3 Earnings')).toBeInTheDocument();
      expect(screen.getByText('Market Volatility Affects Auto Sector')).toBeInTheDocument();
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/stocks/7203/news')
    );
  });

  it('displays sentiment summary correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Market Sentiment Overview')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument(); // positive count
      expect(screen.getByText('2')).toBeInTheDocument(); // negative count
      expect(screen.getByText('3')).toBeInTheDocument(); // neutral count
    });
  });

  it('displays sentiment timeline', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Sentiment Timeline (7d)')).toBeInTheDocument();
    });
  });

  it('handles error state', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('displays empty state when no articles found', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        articles: [],
        sentiment_summary: null,
        sentiment_timeline: [],
        total_count: 0,
        has_more: false
      })
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('No News Found')).toBeInTheDocument();
    });
  });

  it('handles time range selection', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Toyota Reports Strong Q3 Earnings')).toBeInTheDocument();
    });

    // Click on 1d time range
    const oneDayButton = screen.getByText('1d');
    fireEvent.click(oneDayButton);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('time_range=1d')
      );
    });
  });

  it('handles filter changes', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Toyota Reports Strong Q3 Earnings')).toBeInTheDocument();
    });

    // Open filters
    const filterButton = screen.getByRole('button', { name: /toggle filters/i });
    fireEvent.click(filterButton);

    // Change sentiment filter
    const sentimentSelect = screen.getByDisplayValue('All Sentiments');
    fireEvent.change(sentimentSelect, { target: { value: 'positive' } });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('sentiment=positive')
      );
    });
  });

  it('handles sorting changes', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Toyota Reports Strong Q3 Earnings')).toBeInTheDocument();
    });

    // Open filters
    const filterButton = screen.getByRole('button', { name: /toggle filters/i });
    fireEvent.click(filterButton);

    // Change sort option
    const sortSelect = screen.getByDisplayValue('Newest First');
    fireEvent.change(sortSelect, { target: { value: 'relevance_score-desc' } });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('sort_by=relevance_score&sort_order=desc')
      );
    });
  });

  it('loads more articles when button is clicked', async () => {
    // Initial load
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    // Load more
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        articles: [
          {
            id: '3',
            headline: 'Additional Article',
            published_at: '2024-01-13T12:00:00Z',
            language: 'ja'
          }
        ],
        has_more: false
      })
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Toyota Reports Strong Q3 Earnings')).toBeInTheDocument();
    });

    // Click load more
    const loadMoreButton = screen.getByText('Load More Articles');
    fireEvent.click(loadMoreButton);

    await waitFor(() => {
      expect(screen.getByText('Additional Article')).toBeInTheDocument();
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('offset=2')
    );
  });

  it('displays article sentiment badges correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getAllByText('Positive')).toHaveLength(3); // One in timeline, one in summary, one in article badge
      expect(screen.getAllByText('Negative')).toHaveLength(3); // One in timeline, one in summary, one in article badge
    });
  });

  it('formats dates correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      // Should show relative time for recent articles
      expect(screen.getAllByText(/ago/)).toHaveLength(2); // Two articles with "ago" format
    });
  });

  it('displays relevance scores', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Relevance: 90%')).toBeInTheDocument();
      expect(screen.getByText('Relevance: 60%')).toBeInTheDocument();
    });
  });

  it('handles article links correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      const articleLink = screen.getByRole('link', { name: /Toyota Reports Strong Q3 Earnings/i });
      expect(articleLink).toHaveAttribute('href', 'https://example.com/article1');
      expect(articleLink).toHaveAttribute('target', '_blank');
      expect(articleLink).toHaveAttribute('rel', 'noopener noreferrer');
    });
  });

  it('clears filters when clear button is clicked', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Toyota Reports Strong Q3 Earnings')).toBeInTheDocument();
    });

    // Open filters
    const filterButton = screen.getByRole('button', { name: /toggle filters/i });
    fireEvent.click(filterButton);

    // Change a filter
    const sentimentSelect = screen.getByDisplayValue('All Sentiments');
    fireEvent.change(sentimentSelect, { target: { value: 'positive' } });

    // Clear filters
    const clearButton = screen.getByText('Clear Filters');
    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(sentimentSelect).toHaveValue('all');
    });
  });

  it('displays data attribution', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSuccessResponse
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText(/News data aggregated from Nikkei/)).toBeInTheDocument();
      expect(screen.getByText(/Sentiment analysis powered by Japanese NLP models/)).toBeInTheDocument();
    });
  });

  it('handles missing optional fields gracefully', async () => {
    const minimalArticle = {
      id: '1',
      headline: 'Minimal Article',
      published_at: '2024-01-15T10:00:00Z',
      language: 'ja'
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        articles: [minimalArticle],
        total_count: 1,
        has_more: false
      })
    });

    render(<NewsAndSentiment ticker="7203" />);

    await waitFor(() => {
      expect(screen.getByText('Minimal Article')).toBeInTheDocument();
      expect(screen.getByText('Neutral')).toBeInTheDocument(); // Default sentiment
    });
  });
});
/**
 * TradingView Chart Component
 * Integrates TradingView charting library for interactive stock price visualization
 */

import React, { useEffect, useRef, useState } from 'react';

interface TradingViewChartProps {
  ticker: string;
  period: '1d' | '1w' | '1m' | '3m' | '6m' | '1y';
  height?: number;
}

declare global {
  interface Window {
    TradingView: any;
  }
}

const TradingViewChart: React.FC<TradingViewChartProps> = ({
  ticker,
  period,
  height = 500
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Convert period to TradingView interval format
  const getInterval = (period: string) => {
    switch (period) {
      case '1d': return '5';
      case '1w': return '15';
      case '1m': return '60';
      case '3m': return '240';
      case '6m': return 'D';
      case '1y': return 'D';
      default: return 'D';
    }
  };

  // Convert period to TradingView range format
  const getRange = (period: string) => {
    switch (period) {
      case '1d': return '1D';
      case '1w': return '5D';
      case '1m': return '1M';
      case '3m': return '3M';
      case '6m': return '6M';
      case '1y': return '12M';
      default: return '12M';
    }
  };

  // Load TradingView script
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.async = true;
    script.onload = () => {
      setIsLoading(false);
    };
    script.onerror = () => {
      setError('Failed to load TradingView library');
      setIsLoading(false);
    };
    
    if (!document.querySelector('script[src="https://s3.tradingview.com/tv.js"]')) {
      document.head.appendChild(script);
    } else {
      setIsLoading(false);
    }

    return () => {
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, []);

  // Initialize TradingView widget
  useEffect(() => {
    if (!isLoading && !error && containerRef.current && window.TradingView) {
      // Clean up previous widget
      if (widgetRef.current) {
        widgetRef.current.remove();
      }

      try {
        // Format ticker for TradingView (Japanese stocks)
        const formattedTicker = `TSE:${ticker}`;

        widgetRef.current = new window.TradingView.widget({
          container_id: containerRef.current.id,
          width: '100%',
          height: height,
          symbol: formattedTicker,
          interval: getInterval(period),
          timezone: 'Asia/Tokyo',
          theme: 'light',
          style: '1', // Candlestick
          locale: 'en',
          toolbar_bg: '#f1f3f6',
          enable_publishing: false,
          hide_top_toolbar: false,
          hide_legend: false,
          save_image: false,
          hide_volume: false,
          studies: [
            'MASimple@tv-basicstudies', // Moving Average
            'RSI@tv-basicstudies', // RSI
            'MACD@tv-basicstudies' // MACD
          ],
          overrides: {
            'paneProperties.background': '#ffffff',
            'paneProperties.vertGridProperties.color': '#f0f0f0',
            'paneProperties.horzGridProperties.color': '#f0f0f0',
            'symbolWatermarkProperties.transparency': 90,
            'scalesProperties.textColor': '#666666',
            'mainSeriesProperties.candleStyle.upColor': '#22c55e',
            'mainSeriesProperties.candleStyle.downColor': '#ef4444',
            'mainSeriesProperties.candleStyle.drawWick': true,
            'mainSeriesProperties.candleStyle.drawBorder': true,
            'mainSeriesProperties.candleStyle.borderColor': '#378658',
            'mainSeriesProperties.candleStyle.borderUpColor': '#22c55e',
            'mainSeriesProperties.candleStyle.borderDownColor': '#ef4444',
            'mainSeriesProperties.candleStyle.wickUpColor': '#22c55e',
            'mainSeriesProperties.candleStyle.wickDownColor': '#ef4444',
            'volumePaneSize': 'medium'
          },
          studies_overrides: {
            'volume.volume.color.0': '#ef444480',
            'volume.volume.color.1': '#22c55e80',
            'MASimple.ma.color': '#2563eb',
            'RSI.RSI.color': '#7c3aed',
            'MACD.macd.color': '#059669',
            'MACD.signal.color': '#dc2626'
          },
          loading_screen: {
            backgroundColor: '#ffffff',
            foregroundColor: '#2563eb'
          },
          disabled_features: [
            'use_localstorage_for_settings',
            'volume_force_overlay',
            'create_volume_indicator_by_default_once',
            'header_compare',
            'header_undo_redo',
            'header_screenshot',
            'header_chart_type',
            'header_settings',
            'header_indicators',
            'header_symbol_search',
            'symbol_search_hot_key',
            'header_resolutions',
            'header_interval_dialog_button',
            'show_interval_dialog_on_key_press'
          ],
          enabled_features: [
            'study_templates',
            'side_toolbar_in_fullscreen_mode',
            'header_in_fullscreen_mode'
          ],
          custom_css_url: '/tradingview-custom.css',
          time_frames: [
            { text: '1d', resolution: '5', description: '1 Day' },
            { text: '1w', resolution: '15', description: '1 Week' },
            { text: '1m', resolution: '60', description: '1 Month' },
            { text: '3m', resolution: '240', description: '3 Months' },
            { text: '6m', resolution: 'D', description: '6 Months' },
            { text: '1y', resolution: 'D', description: '1 Year' }
          ]
        });

        // Widget event handlers
        widgetRef.current.onChartReady(() => {
          console.log('TradingView chart loaded successfully');
        });

      } catch (err) {
        console.error('Error initializing TradingView widget:', err);
        setError('Failed to initialize chart');
      }
    }

    return () => {
      if (widgetRef.current) {
        try {
          widgetRef.current.remove();
        } catch (err) {
          console.warn('Error removing TradingView widget:', err);
        }
      }
    };
  }, [ticker, period, height, isLoading, error]);

  // Generate unique container ID
  const containerId = `tradingview-chart-${ticker}-${Date.now()}`;

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-400 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Chart Loading Error</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={() => {
            setError(null);
            setIsLoading(true);
          }}
          className="btn-primary"
        >
          Retry
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center" style={{ height }}>
        <div className="loading-spinner mb-4"></div>
        <p className="text-gray-600">Loading interactive chart...</p>
        <p className="text-sm text-gray-500">Powered by TradingView</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Chart Container */}
      <div
        id={containerId}
        ref={containerRef}
        className="w-full"
        style={{ height }}
      />
      
      {/* Chart Info Overlay */}
      <div className="absolute top-4 left-4 bg-white bg-opacity-90 rounded-lg p-3 shadow-sm border border-gray-200">
        <div className="flex items-center space-x-2 text-sm">
          <span className="font-semibold text-gray-900">{ticker}</span>
          <span className="text-gray-500">•</span>
          <span className="text-gray-600">{period.toUpperCase()}</span>
          <span className="text-gray-500">•</span>
          <span className="text-gray-600">JST</span>
        </div>
      </div>

      {/* Technical Indicators Legend */}
      <div className="absolute top-4 right-4 bg-white bg-opacity-90 rounded-lg p-3 shadow-sm border border-gray-200">
        <div className="text-xs text-gray-600 space-y-1">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-0.5 bg-blue-600"></div>
            <span>SMA</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-0.5 bg-purple-600"></div>
            <span>RSI</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-0.5 bg-green-600"></div>
            <span>MACD</span>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mt-2 text-xs text-gray-500 text-center">
        Chart data provided by TradingView. Market data may be delayed.
      </div>
    </div>
  );
};

export default TradingViewChart;
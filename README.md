# TradeX Data Engine

Advanced market data engine with ICT analysis, correlation, AI predictions, and backtesting.

## Features

- 📊 6 Assets × 5 Timeframes × 15 Years Data
- 🧠 ICT Analysis (Market Structure, OBs, FVG, Liquidity)
- 🔗 Correlation Engine
- 🤖 AI Predictions (96-98% confidence)
- 📈 Backtesting Engine
- 🌐 REST API + WebSocket

## API Endpoints

- `/health` - Health check
- `/api/v1/data/candles/{asset}` - Get candles
- `/api/v1/insights/latest` - Get AI insights
- `/api/v1/ict/analyze/{asset}` - ICT analysis
- `/api/v1/correlation/matrix` - Correlation matrix
- `/api/v1/predictions/{asset}` - AI predictions

## Deployment

This project is deployed on Render.com with Neon PostgreSQL.

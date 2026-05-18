"""
Positions service for live portfolio tracking.

Combines holdings data with live prices to compute real-time P&L.
When market is closed, uses last known closing prices.
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Tuple
import logging
import pandas as pd
from pathlib import Path

import pytz

from app.config import get_settings, UNIVERSES, UniverseId
from app.models.database import get_session_local
from app.models.models import OpenPosition
from app.schemas.positions import (
    Position,
    PositionsResponse,
    PositionsSummary,
    OpenPositionInput,
    SyncResponse,
    HoldingsOnlyResponse,
    LiveQuote,
)
from app.services.quotes_service import get_cached_quotes, TokenExpiredError, QuotesFetchError
from app.services.market_service import get_market_status

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


class PositionsService:
    """Service for managing and fetching live portfolio positions."""

    @staticmethod
    def get_holdings(universe: UniverseId) -> List[OpenPosition]:
        """
        Get raw holdings from database.

        Args:
            universe: Universe ID

        Returns:
            List of OpenPosition models
        """
        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            holdings = db.query(OpenPosition).filter(
                OpenPosition.universe == universe
            ).order_by(OpenPosition.symbol).all()
            # Detach from session so we can use them after close
            for h in holdings:
                db.expunge(h)
            return holdings
        finally:
            db.close()

    @staticmethod
    def get_holdings_response(universe: UniverseId) -> HoldingsOnlyResponse:
        """
        Get holdings without live prices.

        Args:
            universe: Universe ID

        Returns:
            HoldingsOnlyResponse with holdings list
        """
        holdings = PositionsService.get_holdings(universe)
        return HoldingsOnlyResponse(
            universe=universe,
            holdings=[
                OpenPositionInput(
                    symbol=h.symbol,
                    qty=h.qty,
                    avg_price=float(h.avg_price),
                    entry_date=h.entry_date
                )
                for h in holdings
            ],
            count=len(holdings)
        )

    @staticmethod
    def _load_prices_from_csv(symbols: List[str], universe: UniverseId) -> Dict[str, Tuple[float, float]]:
        """
        Load latest prices from local CSV price data files.

        Returns dict of symbol -> (last_price, prev_close)
        """
        settings = get_settings()
        universe_config = UNIVERSES.get(universe, UNIVERSES["nse500"])
        data_dir = settings.data_dir / universe_config["data_dir"]

        prices = {}
        for symbol in symbols:
            csv_path = data_dir / f"{symbol}_day.csv"
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path)
                    if len(df) >= 2:
                        # Last row is today's close (or most recent)
                        last_price = float(df.iloc[-1]["close"])
                        # Second to last row is previous close
                        prev_close = float(df.iloc[-2]["close"])
                        prices[symbol] = (last_price, prev_close)
                    elif len(df) == 1:
                        last_price = float(df.iloc[-1]["close"])
                        prices[symbol] = (last_price, last_price)
                except Exception as e:
                    logger.warning(f"Failed to load price for {symbol}: {e}")

        return prices

    @staticmethod
    def _update_stored_prices(universe: UniverseId, quotes: Dict[str, LiveQuote]):
        """
        Update stored prices in database from live quotes.
        """
        if not quotes:
            return

        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            now = datetime.now(IST)
            for symbol, quote in quotes.items():
                db.query(OpenPosition).filter(
                    OpenPosition.universe == universe,
                    OpenPosition.symbol == symbol
                ).update({
                    OpenPosition.last_price: quote.ltp,
                    OpenPosition.prev_close: quote.close,
                    OpenPosition.price_updated_at: now,
                })
            db.commit()
        except Exception as e:
            logger.error(f"Failed to update stored prices: {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def get_positions(universe: UniverseId) -> PositionsResponse:
        """
        Get positions with prices and P&L calculations.

        During market hours: Uses live quotes from Zerodha
        Outside market hours: Uses last stored prices or loads from CSV

        Args:
            universe: Universe ID

        Returns:
            PositionsResponse with positions, summary, and market status
        """
        now = datetime.now(IST)
        market_status = get_market_status()

        # Get holdings from DB
        holdings = PositionsService.get_holdings(universe)

        if not holdings:
            return PositionsResponse(
                universe=universe,
                positions=[],
                summary=PositionsSummary(
                    total_invested=0,
                    total_current_value=0,
                    total_pnl=0,
                    total_pnl_pct=0,
                    day_pnl=0,
                    day_pnl_pct=0,
                    position_count=0,
                    winners=0,
                    losers=0
                ),
                market_status=market_status,
                last_updated=now
            )

        # Get symbols for quote fetching
        symbols = [h.symbol for h in holdings]

        # Try to fetch live quotes
        quotes: Dict[str, LiveQuote] = {}
        quotes_fetched = False

        if market_status.is_open:
            try:
                quotes = get_cached_quotes(symbols, universe)
                quotes_fetched = True
                # Update stored prices in DB
                PositionsService._update_stored_prices(universe, quotes)
            except (TokenExpiredError, QuotesFetchError) as e:
                logger.warning(f"Failed to fetch live quotes: {e}")

        # If no quotes, try to load from CSV files
        csv_prices: Dict[str, Tuple[float, float]] = {}
        if not quotes_fetched:
            csv_prices = PositionsService._load_prices_from_csv(symbols, universe)

        # Build positions with P&L
        positions = []
        total_invested = 0
        total_current_value = 0
        total_day_pnl = 0
        winners = 0
        losers = 0

        for holding in holdings:
            quote = quotes.get(holding.symbol)

            if quote:
                # Use live quote data
                ltp = quote.ltp
                prev_close = quote.close
                day_change = quote.change
                day_change_pct = quote.change_pct
            elif holding.last_price and holding.prev_close:
                # Use stored prices from DB
                ltp = float(holding.last_price)
                prev_close = float(holding.prev_close)
                day_change = ltp - prev_close
                day_change_pct = (day_change / prev_close * 100) if prev_close else 0
            elif holding.symbol in csv_prices:
                # Use prices from CSV files
                ltp, prev_close = csv_prices[holding.symbol]
                day_change = ltp - prev_close
                day_change_pct = (day_change / prev_close * 100) if prev_close else 0
            else:
                # Fallback to avg_price (no price data available)
                ltp = float(holding.avg_price)
                prev_close = ltp
                day_change = 0
                day_change_pct = 0

            # Compute values
            invested = holding.qty * float(holding.avg_price)
            current_value = holding.qty * ltp
            total_pnl = current_value - invested
            total_pnl_pct = (total_pnl / invested * 100) if invested else 0
            day_pnl = holding.qty * day_change

            # Track totals
            total_invested += invested
            total_current_value += current_value
            total_day_pnl += day_pnl

            if total_pnl > 0:
                winners += 1
            elif total_pnl < 0:
                losers += 1

            positions.append(Position(
                symbol=holding.symbol,
                qty=holding.qty,
                avg_price=float(holding.avg_price),
                entry_date=holding.entry_date,
                ltp=round(ltp, 2),
                day_change=round(day_change, 2),
                day_change_pct=round(day_change_pct, 2),
                invested=round(invested, 2),
                current_value=round(current_value, 2),
                total_pnl=round(total_pnl, 2),
                total_pnl_pct=round(total_pnl_pct, 2),
                day_pnl=round(day_pnl, 2),
                day_pnl_pct=round(day_change_pct, 2)
            ))

        # Calculate summary
        total_pnl = total_current_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0
        day_pnl_pct = (total_day_pnl / total_invested * 100) if total_invested else 0

        summary = PositionsSummary(
            total_invested=round(total_invested, 2),
            total_current_value=round(total_current_value, 2),
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=round(total_pnl_pct, 2),
            day_pnl=round(total_day_pnl, 2),
            day_pnl_pct=round(day_pnl_pct, 2),
            position_count=len(positions),
            winners=winners,
            losers=losers
        )

        return PositionsResponse(
            universe=universe,
            positions=positions,
            summary=summary,
            market_status=market_status,
            last_updated=now
        )

    @staticmethod
    def sync_positions(universe: UniverseId, positions: List[OpenPositionInput]) -> SyncResponse:
        """
        Sync positions from input data (replaces all existing positions for universe).

        Args:
            universe: Universe ID
            positions: List of position inputs

        Returns:
            SyncResponse with sync result
        """
        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            # Delete existing positions for this universe
            db.query(OpenPosition).filter(OpenPosition.universe == universe).delete()

            # Load prices from CSV for initial population
            symbols = [p.symbol for p in positions]
            csv_prices = PositionsService._load_prices_from_csv(symbols, universe)

            # Insert new positions
            for pos in positions:
                last_price = None
                prev_close = None
                if pos.symbol in csv_prices:
                    last_price, prev_close = csv_prices[pos.symbol]

                db_pos = OpenPosition(
                    universe=universe,
                    symbol=pos.symbol,
                    qty=pos.qty,
                    avg_price=pos.avg_price,
                    entry_date=pos.entry_date,
                    last_price=last_price,
                    prev_close=prev_close,
                    price_updated_at=datetime.now(IST) if last_price else None,
                )
                db.add(db_pos)

            db.commit()

            return SyncResponse(
                success=True,
                synced_count=len(positions),
                universe=universe,
                message=f"Successfully synced {len(positions)} positions for {universe}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync positions: {e}")
            return SyncResponse(
                success=False,
                synced_count=0,
                universe=universe,
                message=f"Failed to sync: {str(e)}"
            )
        finally:
            db.close()

    @staticmethod
    def sync_from_csv(universe: UniverseId) -> SyncResponse:
        """
        Sync positions from the portfolio CSV file.

        Reads from data/final_portfolio/final_portfolio_24.csv or equivalent.

        Args:
            universe: Universe ID

        Returns:
            SyncResponse with sync result
        """
        settings = get_settings()
        universe_config = UNIVERSES.get(universe)

        if not universe_config:
            return SyncResponse(
                success=False,
                synced_count=0,
                universe=universe,
                message=f"Unknown universe: {universe}"
            )

        # Phase 3.3 — share the latest.json pointer cache with sync_service
        # so all three services agree on which run dir is "latest" for a
        # universe.
        from app.services.sync_service import get_latest_experiment_dir

        portfolio_dir = settings.data_dir / universe_config["portfolio_dir"]
        latest_run = get_latest_experiment_dir(universe)

        csv_patterns = []
        if latest_run is not None:
            csv_patterns.append(latest_run / "backtests" / "baseline" / "momentum_holdings.csv")
            csv_patterns.append(latest_run / "momentum_holdings.csv")
            csv_patterns.append(latest_run / "holdings.csv")
        # Legacy fallback — flat holdings file in the universe's portfolio_dir
        # (used when no timestamped run dir exists).
        csv_patterns.append(portfolio_dir / "momentum_holdings.csv")
        csv_patterns.append(portfolio_dir / "holdings.csv")

        csv_path = None
        for pattern in csv_patterns:
            if pattern.exists():
                csv_path = pattern
                break

        if not csv_path:
            return SyncResponse(
                success=False,
                synced_count=0,
                universe=universe,
                message=f"Portfolio CSV not found for {universe}"
            )

        try:
            df = pd.read_csv(csv_path)

            # Map common column names
            col_mapping = {
                "symbol": "symbol",
                "Symbol": "symbol",
                "shares": "qty",
                "Shares": "qty",
                "qty": "qty",
                "Qty": "qty",
                "avg_cost": "avg_price",
                "Avg_Cost": "avg_price",
                "avg_price": "avg_price",
                "entry_price": "avg_price",
                "entry_date": "entry_date",
                "Entry_Date": "entry_date",
                "last_price": "last_price",
                "Last_Price": "last_price",
            }

            df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})

            if "symbol" not in df.columns or "qty" not in df.columns:
                return SyncResponse(
                    success=False,
                    synced_count=0,
                    universe=universe,
                    message=f"CSV missing required columns (symbol, qty/shares)"
                )

            # Build positions list
            positions = []
            for _, row in df.iterrows():
                avg_price = float(row.get("avg_price", 0))
                if avg_price == 0 and "last_price" in row:
                    avg_price = float(row["last_price"])

                pos = OpenPositionInput(
                    symbol=str(row["symbol"]).strip(),
                    qty=int(row["qty"]),
                    avg_price=avg_price,
                    entry_date=pd.to_datetime(row["entry_date"]).date() if "entry_date" in row and pd.notna(row["entry_date"]) else None
                )
                positions.append(pos)

            return PositionsService.sync_positions(universe, positions)

        except Exception as e:
            logger.error(f"Failed to read portfolio CSV: {e}")
            return SyncResponse(
                success=False,
                synced_count=0,
                universe=universe,
                message=f"Failed to read CSV: {str(e)}"
            )

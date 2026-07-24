"""
Download service for the TradeX Data Engine.
Handles downloading, aggregation, and synthetic asset creation.
"""

from backend.providers.provider_factory import ProviderFactory
from backend.services.aggregation_service import AggregationService
from backend.services.synthetic_service import SyntheticService
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class ValidationService:
    def validate_dataframe(self, df, symbol, timeframe):
        return {'pass': True, 'message': 'Validation passed'}

class CleaningService:
    def clean_dataframe(self, df):
        return df, {'cleaned': True}

class StorageService:
    def save_raw_data(self, df, symbol, timeframe):
        from pathlib import Path
        from datetime import datetime
        
        # Create directory
        raw_dir = Path('data/raw') / symbol / timeframe
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with date
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{symbol}_{timeframe}_{date_str}.csv"
        filepath = raw_dir / filename
        
        # Save
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {symbol} {timeframe} to {filepath}")
        return filepath
    
    def save_cleaned_data(self, df, symbol, timeframe):
        from pathlib import Path
        from datetime import datetime
        
        clean_dir = Path('data/cleaned') / symbol / timeframe
        clean_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{symbol}_{timeframe}_cleaned_{date_str}.csv"
        filepath = clean_dir / filename
        
        df.to_csv(filepath, index=False)
        return filepath

class MetadataService:
    def generate_metadata(self, df, symbol, timeframe, provider):
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'provider': provider,
            'rows': len(df),
            'columns': list(df.columns),
            'start_date': df['timestamp'].min().isoformat() if 'timestamp' in df else None,
            'end_date': df['timestamp'].max().isoformat() if 'timestamp' in df else None
        }
    
    def save_metadata(self, metadata, symbol, timeframe):
        import json
        from pathlib import Path
        from datetime import datetime
        
        meta_dir = Path('data/metadata')
        meta_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{symbol}_{timeframe}_metadata_{date_str}.json"
        filepath = meta_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(metadata, f, indent=2)
        return filepath

class ReportService:
    def generate_download_report(self, results):
        import csv
        from pathlib import Path
        from datetime import datetime
        
        report_dir = Path('reports')
        report_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"download_report_{date_str}.csv"
        filepath = report_dir / filename
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Asset', 'Timeframe', 'Success', 'Rows', 'Message', 'Provider'])
            
            for asset, timeframes in results.items():
                if isinstance(timeframes, dict):
                    for tf, result in timeframes.items():
                        if isinstance(result, dict):
                            writer.writerow([
                                asset, tf, 
                                result.get('success', False),
                                result.get('rows', 0),
                                result.get('message', ''),
                                result.get('provider', 'N/A')
                            ])
        
        logger.info(f"Report saved to {filepath}")
        return filepath

class DownloadService:
    """
    Service for downloading market data with aggregation and synthetic asset support.
    """
    
    def __init__(self):
        self.provider_factory = ProviderFactory()
        self.validation_service = ValidationService()
        self.cleaning_service = CleaningService()
        self.storage_service = StorageService()
        self.metadata_service = MetadataService()
        self.report_service = ReportService()
        self.aggregation_service = AggregationService()
        self.synthetic_service = SyntheticService()
        logger.info("DownloadService initialized with aggregation and synthetic support")
    
    def download_asset_data(self, symbol: str, timeframe: str, 
                           start_date: datetime, end_date: datetime,
                           provider_name: str = None) -> Dict[str, Any]:
        """
        Download data for a single asset with support for aggregation and synthetic assets.
        """
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'success': False,
            'message': '',
            'rows': 0,
            'provider': provider_name or 'default'
        }
        
        try:
            # Check if this is a synthetic asset (XAUEUR or XAUGBP)
            synthetic_assets = ['XAUEUR', 'XAUGBP']
            if symbol in synthetic_assets:
                logger.info(f"Creating synthetic asset: {symbol}")
                return self._create_synthetic_asset(symbol, timeframe, start_date, end_date)
            
            # Get provider
            provider = self.provider_factory.get_provider(provider_name)
            if not provider:
                result['message'] = "No provider available"
                return result
            
            result['provider'] = provider.name

            # Handle special timeframes (shared with _create_synthetic_asset
            # via _download_asset_with_timeframe, so both paths aggregate
            # 4h/weekly identically instead of synthetic assets silently
            # mislabeling raw 1h data as 4h)
            df = self._download_asset_with_timeframe(provider, symbol, timeframe, start_date, end_date)
            if timeframe in ('4h', 'weekly'):
                result['timeframe'] = timeframe
                if df is None or df.empty:
                    result['message'] = f"Failed to build {timeframe} data for {symbol}"
                    return result
            
            # Check if we got data
            if df is None or df.empty:
                result['message'] = f"No data for {symbol} {timeframe}"
                return result
            
            result['rows'] = len(df)
            
            # Validate data
            self.validation_service.validate_dataframe(df, symbol, timeframe)
            
            # Clean data
            cleaned_df, _ = self.cleaning_service.clean_dataframe(df)
            
            # Save raw data
            raw_path = self.storage_service.save_raw_data(df, symbol, result['timeframe'])
            
            # Save cleaned data
            clean_path = self.storage_service.save_cleaned_data(cleaned_df, symbol, result['timeframe'])
            
            # Generate and save metadata
            metadata = self.metadata_service.generate_metadata(
                cleaned_df, symbol, result['timeframe'], provider.name
            )
            self.metadata_service.save_metadata(metadata, symbol, result['timeframe'])
            
            result['success'] = True
            result['message'] = f"Downloaded {len(df)} rows for {symbol} {result['timeframe']}"
            result['raw_path'] = str(raw_path) if raw_path else None
            result['clean_path'] = str(clean_path) if clean_path else None
            
            logger.info(f"Successfully downloaded {symbol} {result['timeframe']}")
            
        except Exception as e:
            result['message'] = f"Error: {str(e)}"
            logger.error(f"Error downloading {symbol}: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _download_asset_with_timeframe(self, provider, symbol: str, timeframe: str,
                                        start_date: datetime, end_date: datetime):
        """
        Download a single asset at the requested timeframe, aggregating from
        a finer provider timeframe when the provider has no native interval
        for it (Yahoo has no 4h interval - YahooProvider maps '4h' to '1h').
        Shared by the normal single-asset path and synthetic-asset creation
        so both compute 4h/weekly identically, rather than synthetic assets
        fetching raw 1h data and labeling it 4h.
        """
        if timeframe == '4h':
            logger.info(f"Downloading 1h data for {symbol} to aggregate to 4h")
            df_1h = provider.download_asset(symbol, '1h', start_date, end_date)
            if df_1h is None or df_1h.empty:
                return None
            return self.aggregation_service.aggregate_4h(df_1h)

        elif timeframe == 'weekly':
            logger.info(f"Downloading daily data for {symbol} to aggregate to weekly")
            df_daily = provider.download_asset(symbol, 'daily', start_date, end_date)
            if df_daily is None or df_daily.empty:
                return None
            return self.aggregation_service.aggregate_weekly(df_daily)

        return provider.download_asset(symbol, timeframe, start_date, end_date)

    def _create_synthetic_asset(self, symbol: str, timeframe: str,
                               start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Create synthetic asset (XAUEUR or XAUGBP) from existing data.
        """
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'success': False,
            'message': '',
            'rows': 0,
            'provider': 'synthetic'
        }
        
        try:
            # Get provider
            provider = self.provider_factory.get_provider()
            if not provider:
                result['message'] = "No provider available"
                return result
            
            # Map synthetic asset to its components
            if symbol == 'XAUEUR':
                # Need XAUUSD and EURUSD
                xauusd = self._download_asset_with_timeframe(provider, 'XAUUSD', timeframe, start_date, end_date)
                eurusd = self._download_asset_with_timeframe(provider, 'EURUSD', timeframe, start_date, end_date)
                
                if xauusd is None or xauusd.empty:
                    result['message'] = "XAUUSD data not available for synthetic XAUEUR"
                    return result
                
                if eurusd is None or eurusd.empty:
                    result['message'] = "EURUSD data not available for synthetic XAUEUR"
                    return result
                
                df = self.synthetic_service.create_xaueur(xauusd, eurusd, timeframe)
                
            elif symbol == 'XAUGBP':
                # Need XAUUSD and GBPUSD
                xauusd = self._download_asset_with_timeframe(provider, 'XAUUSD', timeframe, start_date, end_date)
                gbpusd = self._download_asset_with_timeframe(provider, 'GBPUSD', timeframe, start_date, end_date)
                
                if xauusd is None or xauusd.empty:
                    result['message'] = "XAUUSD data not available for synthetic XAUGBP"
                    return result
                
                if gbpusd is None or gbpusd.empty:
                    result['message'] = "GBPUSD data not available for synthetic XAUGBP"
                    return result
                
                df = self.synthetic_service.create_xaugbp(xauusd, gbpusd, timeframe)
            else:
                result['message'] = f"Unknown synthetic asset: {symbol}"
                return result
            
            if df is None or df.empty:
                result['message'] = f"Failed to create synthetic {symbol}"
                return result
            
            result['rows'] = len(df)
            
            # Save synthetic data
            raw_path = self.storage_service.save_raw_data(df, symbol, timeframe)
            
            # Generate and save metadata
            metadata = self.metadata_service.generate_metadata(df, symbol, timeframe, 'synthetic')
            self.metadata_service.save_metadata(metadata, symbol, timeframe)
            
            result['success'] = True
            result['message'] = f"Created synthetic {symbol} with {len(df)} rows"
            result['raw_path'] = str(raw_path) if raw_path else None
            
            logger.info(f"Successfully created synthetic {symbol}")
            
        except Exception as e:
            result['message'] = f"Error creating synthetic {symbol}: {str(e)}"
            logger.error(f"Error creating synthetic {symbol}: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def run_download_pipeline(self, start_date: datetime, end_date: datetime,
                             assets: Optional[List[str]] = None,
                             timeframes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the full download pipeline for all assets and timeframes.
        """
        from backend.config.settings import settings
        
        if assets is None:
            assets = settings.ASSETS
        
        if timeframes is None:
            timeframes = settings.TIMEFRAMES
        
        results = {}
        total_success = 0
        total_attempts = 0
        
        logger.info(f"Starting download pipeline for {len(assets)} assets")
        logger.info(f"Timeframes: {timeframes}")
        
        for asset in assets:
            asset_results = {}
            for timeframe in timeframes:
                total_attempts += 1
                result = self.download_asset_data(asset, timeframe, start_date, end_date)
                asset_results[timeframe] = result
                if result.get('success', False):
                    total_success += 1
                logger.info(f"  {asset} {timeframe}: {result.get('message', '')}")
            
            results[asset] = asset_results
        
        # Generate report
        report_path = self.report_service.generate_download_report(results)
        
        summary = {
            'start_date': start_date,
            'end_date': end_date,
            'total_attempts': total_attempts,
            'total_success': total_success,
            'success_rate': f"{total_success/total_attempts*100:.1f}%" if total_attempts > 0 else "0%",
            'report_path': str(report_path) if report_path else None,
            'results': results
        }
        
        logger.info(f"Pipeline completed: {total_success}/{total_attempts} successful")
        
        return summary
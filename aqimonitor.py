import os
import requests
import json
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram Notifier
        
        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not found. Notifications disabled.")
            self.enabled = False
        else:
            self.enabled = True
            
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Message templates
        self.templates = {
            'alert': """
🚨 *AIR QUALITY ALERT* 🚨

📍 *Location:* {location}
🌡️ *AQI:* {aqi} ({category})
📅 *Time:* {timestamp}

⚠️ *Health Advisory:*
{recommendation}

🔗 View details: {app_url}
            """,
            
            'daily_report': """
📊 *Daily Air Quality Report* 📊

📍 *Location:* {location}
📅 *Date:* {date}

🌅 *Morning AQI:* {morning_aqi} ({morning_category})
🌆 *Evening AQI:* {evening_aqi} ({evening_category})
📈 *Average AQI:* {avg_aqi}

📋 *Summary:*
{summary}

🔗 View full report: {app_url}
            """,
            
            'forecast': """
🔮 *Air Quality Forecast* 🔮

📍 *Location:* {location}
📅 *Tomorrow ({date}):*

🌅 *Morning:* {morning_forecast} AQI
🌇 *Afternoon:* {afternoon_forecast} AQI  
🌃 *Evening:* {evening_forecast} AQI

💡 *Recommendation:* {forecast_advice}

🔗 View forecast: {app_url}
            """
        }
        
        # Emoji mappings for AQI categories
        self.aqi_emojis = {
            "Good": "🟢",
            "Moderate": "🟡", 
            "Unhealthy for Sensitive": "🟠",
            "Unhealthy": "🔴",
            "Very Unhealthy": "🟣",
            "Hazardous": "⚫"
        }

    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Send message to Telegram chat
        
        Args:
            message: Message text to send
            parse_mode: Message parsing mode (Markdown/HTML)
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.enabled:
            logger.warning("Telegram notifications disabled")
            return False
            
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info("Message sent successfully to Telegram")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_aqi_alert(self, location: str, aqi: float, category: str, 
                       recommendation: str, app_url: str = "") -> bool:
        """
        Send AQI alert notification
        
        Args:
            location: Location name
            aqi: Current AQI value
            category: AQI category
            recommendation: Health recommendation
            app_url: URL to app for more details
            
        Returns:
            bool: True if alert sent successfully
        """
        emoji = self.aqi_emojis.get(category, "❓")
        
        message = self.templates['alert'].format(
            location=location,
            aqi=int(aqi),
            category=f"{emoji} {category}",
            timestamp=datetime.now().strftime('%H:%M, %d/%m/%Y'),
            recommendation=recommendation,
            app_url=app_url or "Check your app"
        )
        
        return self.send_message(message)

    def send_daily_report(self, location: str, date: str, morning_aqi: float,
                         morning_category: str, evening_aqi: float, 
                         evening_category: str, avg_aqi: float,
                         summary: str, app_url: str = "") -> bool:
        """
        Send daily air quality report
        
        Args:
            location: Location name
            date: Report date
            morning_aqi: Morning AQI value
            morning_category: Morning AQI category
            evening_aqi: Evening AQI value  
            evening_category: Evening AQI category
            avg_aqi: Average AQI for the day
            summary: Daily summary text
            app_url: URL to app
            
        Returns:
            bool: True if report sent successfully
        """
        morning_emoji = self.aqi_emojis.get(morning_category, "❓")
        evening_emoji = self.aqi_emojis.get(evening_category, "❓")
        
        message = self.templates['daily_report'].format(
            location=location,
            date=date,
            morning_aqi=int(morning_aqi),
            morning_category=f"{morning_emoji} {morning_category}",
            evening_aqi=int(evening_aqi),
            evening_category=f"{evening_emoji} {evening_category}",
            avg_aqi=int(avg_aqi),
            summary=summary,
            app_url=app_url or "Check your app"
        )
        
        return self.send_message(message)

    def send_forecast(self, location: str, date: str, morning_forecast: int,
                     afternoon_forecast: int, evening_forecast: int,
                     forecast_advice: str, app_url: str = "") -> bool:
        """
        Send air quality forecast
        
        Args:
            location: Location name
            date: Forecast date
            morning_forecast: Morning AQI forecast
            afternoon_forecast: Afternoon AQI forecast
            evening_forecast: Evening AQI forecast
            forecast_advice: Forecast recommendation
            app_url: URL to app
            
        Returns:
            bool: True if forecast sent successfully
        """
        message = self.templates['forecast'].format(
            location=location,
            date=date,
            morning_forecast=morning_forecast,
            afternoon_forecast=afternoon_forecast,
            evening_forecast=evening_forecast,
            forecast_advice=forecast_advice,
            app_url=app_url or "Check your app"
        )
        
        return self.send_message(message)

    def test_connection(self) -> bool:
        """
        Test Telegram bot connection
        
        Returns:
            bool: True if connection successful
        """
        if not self.enabled:
            return False
            
        url = f"{self.base_url}/getMe"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                bot_info = result.get('result', {})
                logger.info(f"Connected to bot: {bot_info.get('username', 'Unknown')}")
                return True
            else:
                logger.error(f"Bot connection failed: {result.get('description')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to bot: {e}")
            return False


class AQIMonitor:
    def __init__(self, notifier: TelegramNotifier, api_key: str = None):
        """
        Initialize AQI Monitor
        
        Args:
            notifier: TelegramNotifier instance
            api_key: Air quality API key
        """
        self.notifier = notifier
        self.api_key = api_key or os.getenv('AQI_API_KEY')
        self.locations = {}  # Format: {location_name: {lat, lon, alert_threshold}}
        self.last_alerts = {}  # Track last alert time for each location
        self.running = False
        
        # AQI categories and thresholds
        self.aqi_categories = {
            (0, 50): ("Good", "Air quality is satisfactory. Outdoor activities are safe."),
            (51, 100): ("Moderate", "Air quality is acceptable for most people."),
            (101, 150): ("Unhealthy for Sensitive", "Sensitive individuals should limit outdoor activities."),
            (151, 200): ("Unhealthy", "Everyone should limit prolonged outdoor activities."),
            (201, 300): ("Very Unhealthy", "Avoid outdoor activities. Stay indoors."),
            (301, 500): ("Hazardous", "Emergency conditions. Everyone should stay indoors.")
        }

    def add_location(self, name: str, lat: float, lon: float, alert_threshold: int = 100):
        """
        Add location to monitor
        
        Args:
            name: Location name
            lat: Latitude
            lon: Longitude
            alert_threshold: AQI threshold for alerts
        """
        self.locations[name] = {
            'lat': lat,
            'lon': lon,
            'alert_threshold': alert_threshold
        }
        logger.info(f"Added location: {name} (Alert threshold: {alert_threshold})")

    def get_aqi_category(self, aqi: float) -> tuple:
        """
        Get AQI category and recommendation
        
        Args:
            aqi: AQI value
            
        Returns:
            tuple: (category, recommendation)
        """
        for (min_aqi, max_aqi), (category, recommendation) in self.aqi_categories.items():
            if min_aqi <= aqi <= max_aqi:
                return category, recommendation
        
        return "Unknown", "Unable to determine air quality status."

    def fetch_aqi_data(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Fetch AQI data from API (placeholder implementation)
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dict: AQI data or None if failed
        """
        # This is a placeholder - replace with actual API implementation
        # Example APIs: OpenWeatherMap, AirVisual, EPA AirNow
        
        try:
            # Simulated API call - replace with real implementation
            import random
            aqi = random.randint(50, 200)  # Simulated AQI value
            
            return {
                'aqi': aqi,
                'timestamp': datetime.now().isoformat(),
                'pollutants': {
                    'pm25': random.randint(10, 100),
                    'pm10': random.randint(20, 150),
                    'o3': random.randint(30, 120),
                    'no2': random.randint(10, 80),
                    'so2': random.randint(5, 50),
                    'co': random.randint(100, 1000)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch AQI data: {e}")
            return None

    def check_locations(self):
        """Check AQI for all monitored locations"""
        for location_name, location_data in self.locations.items():
            try:
                aqi_data = self.fetch_aqi_data(location_data['lat'], location_data['lon'])
                
                if not aqi_data:
                    continue
                
                aqi = aqi_data['aqi']
                category, recommendation = self.get_aqi_category(aqi)
                
                # Check if alert should be sent
                if aqi >= location_data['alert_threshold']:
                    last_alert = self.last_alerts.get(location_name)
                    
                    # Send alert if no previous alert or last alert was > 1 hour ago
                    if not last_alert or (datetime.now() - last_alert).seconds > 3600:
                        success = self.notifier.send_aqi_alert(
                            location=location_name,
                            aqi=aqi,
                            category=category,
                            recommendation=recommendation
                        )
                        
                        if success:
                            self.last_alerts[location_name] = datetime.now()
                
                logger.info(f"{location_name}: AQI {aqi} ({category})")
                
            except Exception as e:
                logger.error(f"Error checking {location_name}: {e}")

    def send_daily_reports(self):
        """Send daily reports for all locations"""
        for location_name, location_data in self.locations.items():
            try:
                # Fetch current and historical data (placeholder)
                morning_data = self.fetch_aqi_data(location_data['lat'], location_data['lon'])
                evening_data = self.fetch_aqi_data(location_data['lat'], location_data['lon'])
                
                if not morning_data or not evening_data:
                    continue
                
                morning_aqi = morning_data['aqi']
                evening_aqi = evening_data['aqi']
                avg_aqi = (morning_aqi + evening_aqi) / 2
                
                morning_category, _ = self.get_aqi_category(morning_aqi)
                evening_category, _ = self.get_aqi_category(evening_aqi)
                
                # Generate summary
                if avg_aqi <= 50:
                    summary = "Good air quality throughout the day. Safe for all outdoor activities."
                elif avg_aqi <= 100:
                    summary = "Moderate air quality. Most people can enjoy outdoor activities."
                elif avg_aqi <= 150:
                    summary = "Unhealthy for sensitive groups. Consider limiting outdoor exposure."
                else:
                    summary = "Poor air quality. Limit outdoor activities and consider wearing masks."
                
                self.notifier.send_daily_report(
                    location=location_name,
                    date=datetime.now().strftime('%d/%m/%Y'),
                    morning_aqi=morning_aqi,
                    morning_category=morning_category,
                    evening_aqi=evening_aqi,
                    evening_category=evening_category,
                    avg_aqi=avg_aqi,
                    summary=summary
                )
                
            except Exception as e:
                logger.error(f"Error sending daily report for {location_name}: {e}")

    def start_monitoring(self):
        """Start monitoring with scheduled checks"""
        if not self.locations:
            logger.error("No locations configured for monitoring")
            return
        
        self.running = True
        
        # Schedule regular checks every 30 minutes
        schedule.every(30).minutes.do(self.check_locations)
        
        # Schedule daily reports at 8 AM and 8 PM
        schedule.every().day.at("08:00").do(self.send_daily_reports)
        schedule.every().day.at("20:00").do(self.send_daily_reports)
        
        logger.info("AQI monitoring started")
        
        # Run scheduler in separate thread
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Initial check
        self.check_locations()

    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        schedule.clear()
        logger.info("AQI monitoring stopped")


# Example usage
if __name__ == "__main__":
    # Initialize notifier
    notifier = TelegramNotifier()
    
    # Test connection
    if notifier.test_connection():
        print("✅ Telegram bot connected successfully")
    else:
        print("❌ Failed to connect to Telegram bot")
        exit(1)
    
    # Initialize monitor
    monitor = AQIMonitor(notifier)
    
    # Add locations to monitor
    monitor.add_location("Semarang", -6.9667, 110.4167, alert_threshold=100)
    monitor.add_location("Jakarta", -6.2088, 106.8456, alert_threshold=100)
    monitor.add_location("Surabaya", -7.2575, 112.7521, alert_threshold=100)
    
    try:
        # Start monitoring
        monitor.start_monitoring()
        
        # Keep the program running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping AQI monitor...")
        monitor.stop_monitoring()
        print("AQI monitor stopped")

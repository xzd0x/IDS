import asyncio
import json
import aiohttp
from aiohttp import web
import logging

# Configuration
import os
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8457330498:AAEIA1VsEi3T51JrOhO0STAoBcQMUUKZbf0')
VEHICLES_JSON_URL = os.environ.get('VEHICLES_JSON_URL', 'https://raw.githubusercontent.com/xzd0x/IDS/refs/heads/main/data/vehicles.json')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramVehicleBot:
    def __init__(self):
        self.session = None
    
    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def send_message(self, chat_id, text, parse_mode=None):
        """Send message to Telegram chat"""
        await self.init_session()
        
        url = f'{TELEGRAM_API_URL}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': text
        }
        
        if parse_mode:
            payload['parse_mode'] = parse_mode
        
        try:
            async with self.session.post(url, json=payload) as response:
                if not response.ok:
                    error_text = await response.text()
                    logger.error(f'Failed to send message: {error_text}')
        except Exception as e:
            logger.error(f'Error sending message: {e}')
    
    async def fetch_vehicles_data(self):
        """Fetch vehicle data from GitHub"""
        await self.init_session()
        
        try:
            async with self.session.get(VEHICLES_JSON_URL) as response:
                if response.ok:
                    return await response.json()
                else:
                    logger.error(f'Failed to fetch vehicles data: {response.status}')
                    return None
        except Exception as e:
            logger.error(f'Error fetching vehicles data: {e}')
            return None
    
    def search_vehicle(self, vehicles, query):
        """Search for vehicle by ID, hex, name, model, or GXT"""
        search_term = query.lower()
        
        for vehicle in vehicles:
            # Search by ID (exact match)
            if vehicle.get('id') == query:
                return vehicle
            
            # Search by hex (exact match)
            if vehicle.get('hex') == query:
                return vehicle
            
            # Search by name (case-insensitive partial match)
            if vehicle.get('name') and search_term in vehicle['name'].lower():
                return vehicle
            
            # Search by model (case-insensitive partial match)
            if vehicle.get('model') and search_term in vehicle['model'].lower():
                return vehicle
            
            # Search by GXT (case-insensitive partial match)
            if vehicle.get('gxt') and search_term in vehicle['gxt'].lower():
                return vehicle
        
        return None
    
    def format_vehicle_info(self, vehicle):
        """Format vehicle information for display"""
        info = "🚗 *Vehicle Information*\n\n"
        info += f"*ID:* `{vehicle.get('id', 'N/A')}`\n"
        info += f"*Hex:* `{vehicle.get('hex', 'N/A')}`\n"
        info += f"*Name:* {vehicle.get('name', 'N/A')}\n"
        info += f"*Model:* `{vehicle.get('model', 'N/A')}`\n"
        info += f"*GXT:* `{vehicle.get('gxt', 'N/A')}`"
        
        if vehicle.get('notes'):
            info += f"\n*Notes:* {vehicle['notes']}"
        
        return info
    
    async def handle_vehicle_search(self, chat_id, query):
        """Handle vehicle search request"""
        vehicles = await self.fetch_vehicles_data()
        
        if not vehicles:
            await self.send_message(chat_id, '⚠️ Error occurred while fetching vehicle data. Please try again later.')
            return
        
        result = self.search_vehicle(vehicles, query.strip())
        
        if result:
            vehicle_info = self.format_vehicle_info(result)
            await self.send_message(chat_id, vehicle_info, 'Markdown')
        else:
            await self.send_message(chat_id, f'❌ No vehicle found for: "{query}"\n\nTry searching by ID, name, or hex value.')
    
    async def handle_update(self, update):
        """Handle incoming Telegram update"""
        if 'message' not in update:
            return
        
        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        
        if not text:
            return
        
        if text == '/start':
            await self.send_message(chat_id, '🚗 Welcome to Vehicle Info Bot!\n\nUse /info to learn how to search for vehicles.')
        
        elif text == '/info':
            help_text = """🚗 *Vehicle Info Bot*

*Usage:*
• Send a vehicle ID (e.g. 400)
• Send a vehicle name (e.g. Landstalker) 
• Send a hex value (e.g. 190)

*Examples:*
`400` - Search by ID
`Landstalker` - Search by name
`190` - Search by hex

The bot will return vehicle information including ID, hex, name, model, and GXT."""
            
            await self.send_message(chat_id, help_text, 'Markdown')
        
        else:
            # Handle vehicle search
            await self.handle_vehicle_search(chat_id, text)

# Create bot instance
bot = TelegramVehicleBot()

async def webhook_handler(request):
    """Handle webhook requests from Telegram"""
    try:
        update = await request.json()
        await bot.handle_update(update)
        return web.Response(text='OK')
    except Exception as e:
        logger.error(f'Error handling webhook: {e}')
        return web.Response(text='Error', status=500)

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text='Bot is running!')

async def init_app():
    """Initialize the web application"""
    app = web.Application()
    app.router.add_post('/', webhook_handler)
    app.router.add_get('/health', health_check)
    return app

async def cleanup(app):
    """Cleanup resources"""
    await bot.close_session()

if __name__ == '__main__':
    app = init_app()
    
    # Add cleanup handler
    app.on_cleanup.append(cleanup)
    
    # Run the web server
    web.run_app(app, host='0.0.0.0', port=8000)

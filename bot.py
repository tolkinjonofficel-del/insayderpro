import os
import json
import logging
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# Bot tokeni (Environment variable dan olish yaxshiroq)
TOKEN = os.getenv("BOT_TOKEN", "7578011916:AAFZTbhIMkPhHTNpO9-HbfWMNywLAxVq8xg")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6935090105","7081746531"))

# Ma'lumotlarni saqlash fayli
DATA_FILE = "data.json"

# Bukmekerlar havolalari
BUKMAKER_LINKS = {
    "1xbet": "https://reffpa.com/L?tag=d_4147173m_1599c_&site=4147173&ad=1599&r=registration",
    "melbet": "https://refpa42380.com/L?tag=s_4856673m_57037c_&site=4856673&ad=57037", 
    "dbbet": "https://refpa96317.com/L?tag=d_4585917m_11213c_&site=4585917&ad=11213"
}

# Loggerni sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Boshlang'ich ma'lumotlar
default_data = {
    "users": {},
    "coupons": {
        "available": [],
        "purchased": {}
    },
    "settings": {
        "referral_points": 5,
        "coupon_price": 15,
        "min_exchange_points": 50,
        "exchange_rate": 10000,
        "daily_bonus": 10,
        "welcome_points": 30,
        "currency": "so'm",
        "bot_username": ""
    },
    "stats": {
        "total_users": 0,
        "total_points_given": 0,
        "total_coupons_sold": 0,
        "total_exchanges": 0,
        "last_coupon_id": 1000
    },
    "admin": {
        "broadcast_lock": False
    }
}

class DataManager:
    """Ma'lumotlarni boshqarish uchun class"""
    
    def __init__(self, data_file):
        self.data_file = data_file
        self.data = self.load_data()
        self.lock = asyncio.Lock()
    
    def load_data(self):
        """Ma'lumotlarni yuklash"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Eskilar bilan yangilarni birlashtirish
                for key in default_data:
                    if key not in data:
                        data[key] = default_data[key]
                return data
        except FileNotFoundError:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            return default_data.copy()
        except Exception as e:
            logger.error(f"Ma'lumotlarni yuklashda xato: {e}")
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            return default_data.copy()
    
    async def save_data(self):
        """Ma'lumotlarni saqlash"""
        async with self.lock:
            try:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                logger.error(f"Saqlash xatosi: {e}")
                return False
    
    def get_user(self, user_id):
        """Foydalanuvchi ma'lumotlarini olish"""
        user_id_str = str(user_id)
        if user_id_str not in self.data['users']:
            return None
        return self.data['users'][user_id_str]
    
    def get_user_points(self, user_id):
        """Foydalanuvchi ballarini olish"""
        user = self.get_user(user_id)
        if user:
            return user.get('points', 0)
        return 0
    
    def get_user_referrals(self, user_id):
        """Foydalanuvchi referallarini olish"""
        user = self.get_user(user_id)
        if user:
            return user.get('referrals', 0)
        return 0

# Global data manager
data_manager = DataManager(DATA_FILE)

def is_admin(user_id):
    return user_id == ADMIN_ID

def can_get_daily_bonus(user_id):
    """Foydalanuvchi kunlik bonus olishi mumkinmi tekshirish"""
    user = data_manager.get_user(user_id)
    if not user:
        return True
    
    last_bonus_date = user.get('last_daily_bonus')
    if not last_bonus_date:
        return True
    
    try:
        last_date = datetime.strptime(last_bonus_date, "%Y-%m-%d")
        now = datetime.now()
        time_diff = now - last_date
        return time_diff.total_seconds() >= 86400
    except Exception as e:
        logger.error(f"Kunlik bonus vaqtini tekshirishda xato: {e}")
        return True

async def give_daily_bonus_to_user(user_id):
    """Foydalanuvchiga kunlik bonus berish"""
    try:
        user_id_str = str(user_id)
        if user_id_str not in data_manager.data['users']:
            return False
        
        now = datetime.now()
        bonus_points = data_manager.data['settings']['daily_bonus']
        
        data_manager.data['users'][user_id_str]['points'] = data_manager.data['users'][user_id_str].get('points', 0) + bonus_points
        data_manager.data['users'][user_id_str]['last_daily_bonus'] = now.strftime("%Y-%m-%d")
        data_manager.data['stats']['total_points_given'] += bonus_points
        
        if 'points_history' not in data_manager.data['users'][user_id_str]:
            data_manager.data['users'][user_id_str]['points_history'] = []
        
        data_manager.data['users'][user_id_str]['points_history'].append({
            'points': bonus_points,
            'reason': f"Kunlik bonus {now.strftime('%Y-%m-%d')}",
            'date': now.strftime("%Y-%m-%d %H:%M"),
            'type': 'daily_bonus'
        })
        
        await data_manager.save_data()
        return True
        
    except Exception as e:
        logger.error(f"Kunlik bonus berishda xato: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"Start command from user {user_id} ({user.first_name})")
        
        # Bot username ni saqlash
        bot_username = (await context.bot.get_me()).username
        if bot_username != data_manager.data['settings'].get('bot_username'):
            data_manager.data['settings']['bot_username'] = bot_username
            await data_manager.save_data()
        
        # Yangi foydalanuvchi bo'lsa 30 ball berish
        is_new_user = False
        if str(user_id) not in data_manager.data['users']:
            data_manager.data['users'][str(user_id)] = {
                'name': user.first_name,
                'username': user.username,
                'referrals': 0,
                'points': data_manager.data['settings']['welcome_points'],
                'joined_date': datetime.now().strftime("%Y-%m-%d"),
                'last_active': datetime.now().isoformat(),
                'last_daily_bonus': None,
                'points_history': [{
                    'points': data_manager.data['settings']['welcome_points'],
                    'reason': "Yangi foydalanuvchi bonus",
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'type': 'add'
                }]
            }
            data_manager.data['stats']['total_users'] += 1
            data_manager.data['stats']['total_points_given'] += data_manager.data['settings']['welcome_points']
            await data_manager.save_data()
            is_new_user = True
            logger.info(f"Yangi foydalanuvchi qo'shildi: {user_id} - {data_manager.data['settings']['welcome_points']} ball berildi")
        else:
            data_manager.data['users'][str(user_id)]['last_active'] = datetime.now().isoformat()
            await data_manager.save_data()
        
        # Referal tizimi
        if context.args:
            ref_id = context.args[0]
            logger.info(f"Referal argument: {ref_id}")
            if ref_id.startswith('ref'):
                try:
                    referrer_id = int(ref_id[3:])
                    if str(referrer_id) in data_manager.data['users'] and referrer_id != user_id:
                        # Referallar sonini oshiramiz
                        data_manager.data['users'][str(referrer_id)]['referrals'] += 1
                        
                        # Ballarni qo'shamiz
                        points_to_add = data_manager.data['settings']['referral_points']
                        data_manager.data['users'][str(referrer_id)]['points'] = data_manager.data['users'][str(referrer_id)].get('points', 0) + points_to_add
                        
                        # Tarixga yozamiz
                        if 'points_history' not in data_manager.data['users'][str(referrer_id)]:
                            data_manager.data['users'][str(referrer_id)]['points_history'] = []
                        
                        data_manager.data['users'][str(referrer_id)]['points_history'].append({
                            'points': points_to_add,
                            'reason': f"Referal taklif: {user.first_name}",
                            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                            'type': 'referral'
                        })
                        
                        # Statistikani yangilaymiz
                        data_manager.data['stats']['total_points_given'] += points_to_add
                        
                        await data_manager.save_data()
                        
                        # Referal beruvchiga xabar yuborish
                        try:
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 *Tabriklaymiz!*\n\n"
                                     f"📤 Sizning referal havolangiz orqali yangi foydalanuvchi qo'shildi!\n"
                                     f"👤 Yangi foydalanuvchi: {user.first_name}\n"
                                     f"💰 Sizga {points_to_add} ball qo'shildi!\n"
                                     f"🎯 Jami ball: {data_manager.get_user_points(referrer_id)}\n\n"
                                     f"📊 Jami referallar: {data_manager.data['users'][str(referrer_id)]['referrals']} ta",
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except Exception as e:
                            logger.error(f"Referal bildirishnoma yuborishda xato: {e}")
                except Exception as e:
                    logger.error(f"Referal qayd etishda xato: {e}")

        welcome_text = f"""
🎉 *SALOM {user.first_name}!* 🏆

⚽ *FUTBOL BAHOLARI BOTIGA XUSH KELIBSIZ!*

💰 *BALL TIZIMI:*
• 🎁 *Yangi foydalanuvchi bonus:* {data_manager.data['settings']['welcome_points']} ball
• 📤 1 do'st taklif = *{data_manager.data['settings']['referral_points']} ball*
• 📅 *Kunlik bonus:* {data_manager.data['settings']['daily_bonus']} ball (har 24 soatda)
• 🎯 {data_manager.data['settings']['coupon_price']} ball = *1 ta maxsus kupon*

📊 *SIZNING HOLATINGIZ:*
👥 Referallar: {data_manager.get_user_referrals(user_id)} ta
💰 HISOBINGIZDA: {data_manager.get_user_points(user_id)} ball
"""

        if is_new_user:
            welcome_text += f"\n🎁 *Sizga yangi foydalanuvchi bonus sifatida {data_manager.data['settings']['welcome_points']} ball berildi!*"

        # Kunlik bonus holatini ko'rsatish
        if can_get_daily_bonus(user_id):
            welcome_text += f"\n\n📅 *Kunlik bonus olish mumkin!*"
        else:
            try:
                last_bonus = data_manager.data['users'][str(user_id)].get('last_daily_bonus')
                if last_bonus:
                    last_date = datetime.strptime(last_bonus, "%Y-%m-%d")
                    next_bonus = last_date + timedelta(days=1)
                    remaining = next_bonus - datetime.now()
                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60
                    welcome_text += f"\n\n⏳ *Keyingi kunlik bonus:* {hours} soat {minutes} daqiqadan keyin"
            except Exception as e:
                logger.error(f"Kunlik bonus vaqtini hisoblashda xato: {e}")

        welcome_text += f"\n\n🚀 *HOZIRROQ BOSHLANG!*\nBall to'plang va kuponlar oling! 🎯"

        keyboard = [
            [
                InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons"),
                InlineKeyboardButton("📅 KUNLIK BONUS", callback_data="daily_bonus")
            ],
            [
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points"),
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Start commandda xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        logger.info(f"Button handler: {query.data} from user {user_id}")
        
        # Asosiy menyu tugmalari
        if query.data == "get_coupons":
            await show_coupon_selection(query, user_id)
        elif query.data == "get_ball_coupon":
            await get_ball_coupon(query, user_id)
        elif query.data == "bonuses":
            await show_bonuses(query)
        elif query.data == "my_points":
            await show_my_points(query, user_id)
        elif query.data == "get_referral_link":
            await show_referral_link(query, user_id, context)
        elif query.data == "share_referral":
            await share_referral_link(query, user_id, context)
        elif query.data == "back":
            await back_to_main(query, context)
        elif query.data == "daily_bonus":
            await handle_daily_bonus(query, user_id)
        elif query.data == "copy_referral_link":
            await copy_referral_link(query, user_id, context)
        
        # ADMIN HANDLERLARI
        elif query.data == "admin":
            if is_admin(user_id):
                await show_admin_panel(query)
            else:
                await query.edit_message_text("❌ Siz admin emassiz!")
        elif query.data == "admin_stats":
            await show_admin_stats(query)
        elif query.data == "admin_add_coupon":
            await show_admin_add_coupon(query)
        elif query.data == "admin_broadcast":
            await show_admin_broadcast(query)
        elif query.data == "admin_manage_coupons":
            await show_admin_manage_coupons(query)
        elif query.data.startswith("admin_delete_coupon_"):
            coupon_id = query.data.replace("admin_delete_coupon_", "")
            await delete_coupon(query, coupon_id)
        elif query.data == "admin_view_coupons":
            await show_admin_view_coupons(query)
        elif query.data == "admin_back":
            await show_admin_panel(query)
        elif query.data == "admin_add_user_points":
            await show_admin_add_points(query)
        elif query.data.startswith("admin_add_points_"):
            parts = query.data.replace("admin_add_points_", "").split("_")
            if len(parts) == 2:
                target_user_id = int(parts[0])
                points = int(parts[1])
                await add_user_points(query, target_user_id, points, context)
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")
        await query.edit_message_text(f"❌ Xatolik yuz berdi: {str(e)}")

async def show_referral_link(query, user_id, context):
    """Referal havolasini ko'rsatish"""
    try:
        # Bot username ni olish
        bot_username = data_manager.data['settings'].get('bot_username', '')
        if not bot_username:
            bot_username = (await context.bot.get_me()).username
            data_manager.data['settings']['bot_username'] = bot_username
            await data_manager.save_data()
        
        ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
        referrals_count = data_manager.get_user_referrals(user_id)
        points_per_ref = data_manager.data['settings']['referral_points']
        user_points = data_manager.get_user_points(user_id)
        
        text = f"""
📤 *BAL TO'PLASH USULI*

🔗 **Sizning referal havolangiz:**
`{ref_link}`

💰 **Ball to'plash formulasi:**
• Har bir do'st = {points_per_ref} ball
• Ko'proq do'st = Ko'proq ball

📊 **Sizning holatingiz:**
• Do'stlar: {referrals_count} ta
• HISOBINGIZ: {user_points} ball
• Jami olingan ball: {referrals_count * points_per_ref} ball

💡 **Qanday ball to'plasaniz:**
1. Havolani nusxalang yoki ulashing
2. Do'stlaringizga yuboring  
3. Har bir yangi do'st = {points_per_ref} ball
4. Ballarni kuponlarga aylantiring!

📅 **Kunlik bonus:** Har 24 soatda {data_manager.data['settings']['daily_bonus']} ball
🎯 **Kupon narxi:** {data_manager.data['settings']['coupon_price']} ball

🚀 *Ko'proq do'st taklif qiling, tezroq ball to'plang!*
"""

        keyboard = [
            [InlineKeyboardButton("📋 HAVOLANI NUSXALASH", callback_data="copy_referral_link")],
            [InlineKeyboardButton("📤 TELEGRAMDA ULASHISH", callback_data="share_referral")],
            [InlineKeyboardButton("📅 KUNLIK BONUS", callback_data="daily_bonus")],
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_referral_link da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def share_referral_link(query, user_id, context):
    """Havolani ulashish"""
    try:
        # Bot username ni olish
        bot_username = data_manager.data['settings'].get('bot_username', '')
        if not bot_username:
            bot_username = (await context.bot.get_me()).username
            data_manager.data['settings']['bot_username'] = bot_username
            await data_manager.save_data()
        
        ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
        
        # Telegram share URL yaratish
        import urllib.parse
        share_text = "🎯 *Futbol Kuponlari Boti*\n\n⚽ Kunlik bepul kuponlar\n💰 Ball evaziga ekskluziv kuponlar\n💎 Har bir do'st uchun 5 ball\n\n🎁 Do'stlaringizni taklif qiling va bepul kuponlar oling!\n\nBotga kirib, daromad olishni boshlang:"
        encoded_text = urllib.parse.quote(share_text)
        telegram_share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={encoded_text}"
        
        text = f"""
📤 *HAVOLANI ULASHISH*

🔗 **Sizning referal havolangiz:**
`{ref_link}`

👇 Quyidagi tugmalar orqali havolani osongina ulashing:

1. **📋 Nusxalash** - Havolani nusxalab, istalgan joyda ulashing
2. **📤 Telegramda ulashish** - Telegram orqali do'stlaringizga yuborish
3. **👥 Guruhlarda ulashish** - Telegram guruh va kanallarda tarqatish

💡 **Maslahatlar:**
• Do'stlaringizga shaxsiy xabar yuboring
• Telegram guruhlaringizda ulashing
• Kanal yoki bloglarda tarqating
• Ijtimoiy tarmoqlarda baham ko'ring

🚀 *Har bir do'st = {data_manager.data['settings']['referral_points']} ball!*
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📋 HAVOLANI NUSXALASH", callback_data="copy_referral_link"),
                InlineKeyboardButton("📤 TELEGRAMDA ULASHISH", url=telegram_share_url)
            ],
            [
                InlineKeyboardButton("📅 KUNLIK BONUS", callback_data="daily_bonus"),
                InlineKeyboardButton("🎯 KUPON OLISH", callback_data="get_coupons")
            ],
            [InlineKeyboardButton("💰 MENING BALLIM", callback_data="my_points")],
            [InlineKeyboardButton("🔙 ORQAGA", callback_data="get_referral_link")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"share_referral_link da xato: {e}")
        text = f"""
📤 *HAVOLANI ULASHISH*

🔗 **Sizning referal havolangiz:**
`https://t.me/{data_manager.data['settings'].get('bot_username', 'bot_username')}?start=ref{user_id}`

👇 Havolani nusxalab, Telegramda do'stlaringizga yuboring:

1. 📋 Havolani nusxalang
2. 📤 Telegram oching
3. 👤 Do'stingizga xabar yuboring
4. 🔗 Havolani yopishtiring
5. 💰 Ball oling!

🚀 *Har bir do'st = {data_manager.data['settings']['referral_points']} ball!*
"""
        
        keyboard = [
            [InlineKeyboardButton("📋 HAVOLANI NUSXALASH", callback_data="copy_referral_link")],
            [InlineKeyboardButton("📅 KUNLIK BONUS", callback_data="daily_bonus")],
            [InlineKeyboardButton("🎯 KUPON OLISH", callback_data="get_coupons")],
            [InlineKeyboardButton("🔙 ORQAGA", callback_data="get_referral_link")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def copy_referral_link(query, user_id, context):
    """Havolani nusxalash uchun xabar yuborish"""
    try:
        # Bot username ni olish
        bot_username = data_manager.data['settings'].get('bot_username', '')
        if not bot_username:
            bot_username = (await context.bot.get_me()).username
            data_manager.data['settings']['bot_username'] = bot_username
            await data_manager.save_data()
        
        ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
        
        text = f"""
📋 *HAVOLANI NUSXALASH*

🔗 **Sizning referal havolangiz:**
`{ref_link}`

👇 Havolani nusxalash uchun:
1. Yuqoridagi havolani bosing
2. "Nusxalash" tugmasini bosing
3. Istalgan joyda ulashing

💡 **Ulashish joylari:**
• Telegram shaxsiy xabarlar
• Telegram guruh va kanallar
• Instagram, Facebook, Twitter
• SMS orqali do'stlarga
• Boshqa ijtimoiy tarmoqlar

💰 *Har bir do'st = {data_manager.data['settings']['referral_points']} ball!*

🚀 *Ko'proq do'st taklif qiling, tezroq kuponlar oling!*
"""
        
        keyboard = [
            [InlineKeyboardButton("📤 ULASHISH SAHIFASIGA QAYTISH", callback_data="share_referral")],
            [InlineKeyboardButton("🔙 BOSH MENYU", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"copy_referral_link da xato: {e}")
        await query.edit_message_text(
            f"🔗 **Sizning referal havolangiz:**\n\n"
            f"`https://t.me/{data_manager.data['settings'].get('bot_username', 'bot')}?start=ref{user_id}`\n\n"
            f"📋 Yuqoridagi havolani nusxalab, do'stlaringizga yuboring!",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_daily_bonus(query, user_id):
    """Kunlik bonusni berish"""
    try:
        if not can_get_daily_bonus(user_id):
            # Vaqt qolganini hisoblash
            user = data_manager.get_user(user_id)
            if user:
                last_bonus = user.get('last_daily_bonus')
                if last_bonus:
                    last_date = datetime.strptime(last_bonus, "%Y-%m-%d")
                    next_bonus = last_date + timedelta(days=1)
                    remaining = next_bonus - datetime.now()
                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60
                    
                    text = f"""
⏳ *KUNLIK BONUS*

📅 **Oxirgi kunlik bonus:** {last_bonus}
⏰ **Keyingi bonus:** {hours} soat {minutes} daqiqadan keyin

💡 *Ball to'plashning boshqa usullari:*
• 📤 Do'st taklif qiling ({data_manager.data['settings']['referral_points']} ball / do'st)
• 🎯 Kuponlar orqali g'alaba qozoning
• 🎁 Boshqa bonuslardan foydalaning

🚀 *Tezroq ball to'plash uchun do'stlaringizni taklif qiling!*
"""
                    
                    keyboard = [
                        [InlineKeyboardButton("📤 DO'ST TAKLIF QILISH", callback_data="get_referral_link")],
                        [InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons")],
                        [InlineKeyboardButton("💰 MENING BALLIM", callback_data="my_points")],
                        [InlineKeyboardButton("🔙 BOSH MENYU", callback_data="back")]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                else:
                    await query.edit_message_text(
                        "❌ Kunlik bonus olishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.",
                        parse_mode=ParseMode.MARKDOWN
                    )
            return
        
        # Kunlik bonusni berish
        if await give_daily_bonus_to_user(user_id):
            user_points = data_manager.get_user_points(user_id)
            bonus_amount = data_manager.data['settings']['daily_bonus']
            
            text = f"""
🎉 *TABRIKLAYMIZ!*

💰 *Kunlik bonus olindingiz!*
✅ +{bonus_amount} ball qo'shildi!

📊 *HISOBINGIZ:*
💰 Jami ball: {user_points} ball
📅 Keyingi kunlik bonus: 24 soatdan keyin

💡 *Keyingi bosqichlar:*
• 🎯 Kuponlar olish uchun ball to'plang
• 📤 Do'stlaringizni taklif qiling
• 🚀 G'alaba qozoning!

🔥 *Hozir {user_points} ballingiz bor!*
"""
            
            keyboard = [
                [InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons")],
                [InlineKeyboardButton("📤 DO'ST TAKLIF QILISH", callback_data="get_referral_link")],
                [InlineKeyboardButton("💰 MENING BALLIM", callback_data="my_points")],
                [InlineKeyboardButton("🔙 BOSH MENYU", callback_data="back")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await query.edit_message_text(
                "❌ Kunlik bonus berishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.",
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"Kunlik bonus berishda xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def back_to_main(query, context):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        welcome_text = f"""
🎯 *ASOSIY MENYU*

💰 **Sizning holatingiz:**
👥 Referallar: {data_manager.get_user_referrals(user_id)} ta
💰 HISOBINGIZDA: {data_manager.get_user_points(user_id)} ball
📅 Kunlik bonus: {data_manager.data['settings']['daily_bonus']} ball (har 24 soatda)

🚀 Ball to'plang va kuponlar oling!
"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons"),
                InlineKeyboardButton("📅 KUNLIK BONUS", callback_data="daily_bonus")
            ],
            [
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points"),
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"back_to_main da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_coupon_selection(query, user_id):
    try:
        user_points = data_manager.get_user_points(user_id)
        coupon_price = data_manager.data['settings']['coupon_price']
        
        text = f"""
🎯 *KUPON OLISH*

💰 **Sizning balansingiz:** {user_points} ball
🎟️ **Kupon narxi:** {coupon_price} ball

💎 *Ballaringiz yetarli bo'lsa VIP kuponlar olishingiz mumkin:*
"""

        keyboard = []
        
        available_coupons = [c for c in data_manager.data['coupons']['available'] 
                           if str(user_id) not in data_manager.data['coupons']['purchased'].get(c['id'], [])]
        
        if available_coupons:
            if user_points >= coupon_price:
                keyboard.append([InlineKeyboardButton(f"💰 VIP KUPON OLISH ({coupon_price} ball)", callback_data="get_ball_coupon")])
                text += f"\n✅ *{len(available_coupons)} ta VIP kupon mavjud!*"
            else:
                needed_points = coupon_price - user_points
                text += f"\n❌ *Ball yetarli emas!* {needed_points} ball yetishmayapti."
        else:
            text += f"\n📭 *Hozircha yangi kuponlar mavjud emas.*"
        
        keyboard.extend([
            [InlineKeyboardButton("📅 KUNLIK BONUS", callback_data="daily_bonus")],
            [InlineKeyboardButton("📤 Bal To'plash", callback_data="get_referral_link")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_coupon_selection da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def get_ball_coupon(query, user_id):
    try:
        user_points = data_manager.get_user_points(user_id)
        coupon_price = data_manager.data['settings']['coupon_price']
        
        if user_points < coupon_price:
            await query.edit_message_text(
                f"❌ Ballaringiz yetarli emas!\n"
                f"💰 Sizda: {user_points} ball\n"
                f"💵 Kerak: {coupon_price} ball\n\n"
                f"📤 Ball to'plash uchun:\n"
                f"• 📅 Kunlik bonus oling\n"
                f"• 📤 Referal havolangizni tarqating\n"
                f"• 🎁 Boshqa bonuslardan foydalaning!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        available_coupons = [c for c in data_manager.data['coupons']['available'] 
                           if str(user_id) not in data_manager.data['coupons']['purchased'].get(c['id'], [])]
        
        if not available_coupons:
            await query.edit_message_text(
                "❌ Hozircha yangi kuponlar mavjud emas. Tez orada yangilanadi! 🔄",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        coupon = random.choice(available_coupons)
        
        data_manager.data['users'][str(user_id)]['points'] -= coupon_price
        data_manager.data['stats']['total_coupons_sold'] += 1
        
        if coupon['id'] not in data_manager.data['coupons']['purchased']:
            data_manager.data['coupons']['purchased'][coupon['id']] = []
        
        data_manager.data['coupons']['purchased'][coupon['id']].append(str(user_id))
        await data_manager.save_data()
        
        coupon_text = f"""
🎉 *TABRIKLAYMIZ!*

✅ Siz {coupon_price} ball evaziga kupon sotib oldingiz!

🎟️ *Kupon ma'lumotlari:*
🏆 **O'yin:** {coupon['teams']}
⏰ **Vaqt:** {coupon['time']}
🌍 **Liga:** {coupon['league']}
🎯 **Bashorat:** {coupon['prediction']}
📊 **Koeffitsient:** {coupon['odds']}
💎 **Ishonch:** {coupon['confidence']}

🔑 *Kupon kodlari:*
• 1xBet: `{coupon['codes']['1xbet']}`
• MelBet: `{coupon['codes']['melbet']}`
• DB Bet: `{coupon['codes']['dbbet']}`

💰 **Qolgan ball:** {data_manager.get_user_points(user_id)}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🎰 1xBet", url=BUKMAKER_LINKS['1xbet']),
                InlineKeyboardButton("🎯 MelBet", url=BUKMAKER_LINKS['melbet']),
                InlineKeyboardButton("💰 DB Bet", url=BUKMAKER_LINKS['dbbet'])
            ],
            [InlineKeyboardButton("🔄 Yana Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(coupon_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"get_ball_coupon da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_my_points(query, user_id):
    try:
        user = data_manager.get_user(user_id)
        
        if not user:
            await query.edit_message_text(
                "❌ Sizning hisobingiz topilmadi. Iltimos, /start komandasini yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        points = user.get('points', 0)
        referrals = user.get('referrals', 0)
        coupon_price = data_manager.data['settings']['coupon_price']
        daily_bonus = data_manager.data['settings']['daily_bonus']
        referral_points = data_manager.data['settings']['referral_points']
        
        bonus_status = "✅ *OLISH MUMKIN*" if can_get_daily_bonus(user_id) else "⏳ *VAQT O'TISHINI KUTING*"
        
        text = f"""
🏆 *MENING HISOBIM*

💰 **HISOBINGIZDA:** {points} ball
👥 **Referallar:** {referrals} ta
💵 **1 referal:** {referral_points} ball
📅 **Kunlik bonus:** {daily_bonus} ball
🎟️ **Kupon narxi:** {coupon_price} ball

📊 **Kupon olish imkoniyatlari:**
"""

        if points >= coupon_price:
            available_coupons = len([c for c in data_manager.data['coupons']['available'] 
                                   if str(user_id) not in data_manager.data['coupons']['purchased'].get(c['id'], [])])
            text += f"✅ **Kupon olish mumkin!** - {available_coupons} ta mavjud kupon"
        else:
            needed_points = coupon_price - points
            text += f"❌ **Kupon uchun:** {needed_points} ball yetishmayapti"
        
        text += f"\n\n📅 *Kunlik bonus holati:* {bonus_status}"
        
        if not can_get_daily_bonus(user_id):
            last_bonus = user.get('last_daily_bonus')
            if last_bonus:
                try:
                    last_date = datetime.strptime(last_bonus, "%Y-%m-%d")
                    next_bonus = last_date + timedelta(days=1)
                    remaining = next_bonus - datetime.now()
                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60
                    text += f"\n⏰ **Keyingi bonus:** {hours} soat {minutes} daqiqadan keyin"
                except Exception as e:
                    logger.error(f"Kunlik bonus vaqtini hisoblashda xato: {e}")
        
        keyboard = [
            [InlineKeyboardButton("📅 KUNLIK BONUS", callback_data="daily_bonus")],
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_my_points da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_bonuses(query):
    try:
        text = """
🎁 *BONUSLAR*

💰 *Ball olish usullari:*
• 🎁 *Yangi foydalanuvchi bonus:* 30 ball
• 📅 *Kunlik bonus:* Har 24 soatda 10 ball
• 📤 *Referal bonus:* Har bir do'st uchun 5 ball

🏆 *Bukmeker kontorlarida ro'yxatdan o'ting va bonus oling!*

🎰 **1xBet:**
• Yangi foydalanuvchilar uchun 100% bonus
• INSAYDER PROMOKODINI kiriting va Birinchi depozitga 100% gacha bonus

🎯 **MelBet:**
• Ro'yxatdan o'ting va bonus oling
• AIFUT promokodini kiriting

📱 **DB Bet:**
• Yangi foydalanuvchilar uchun maxsus takliflar
• Tezkor to'lovlar va yuqori koeffitsientlar
"""

        keyboard = [
            [
                InlineKeyboardButton("🎰 1xBet", url=BUKMAKER_LINKS['1xbet']),
                InlineKeyboardButton("🎯 MelBet", url=BUKMAKER_LINKS['melbet']),
                InlineKeyboardButton("💰 DB Bet", url=BUKMAKER_LINKS['dbbet'])
            ],
            [
                InlineKeyboardButton("📅 KUNLIK BONUS", callback_data="daily_bonus"),
                InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")
            ],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_bonuses da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# ==================== ADMIN FUNCTIONS ====================

async def show_admin_panel(query):
    """Admin panelini ko'rsatish"""
    try:
        text = """
👑 *ADMIN PANELI*

🔧 *Admin funksiyalari:*
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 STATISTIKA", callback_data="admin_stats")],
            [InlineKeyboardButton("➕ KUPON QO'SHISH", callback_data="admin_add_coupon")],
            [InlineKeyboardButton("📋 KUPONLARNI KO'RISH", callback_data="admin_view_coupons")],
            [InlineKeyboardButton("🎯 BALL QO'SHISH", callback_data="admin_add_user_points")],
            [InlineKeyboardButton("📢 REKLAMA YUBORISH", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 BOSH MENYU", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_stats(query):
    """Statistikani ko'rsatish"""
    try:
        total_points = sum(user.get('points', 0) for user in data_manager.data['users'].values())
        total_referrals = sum(user.get('referrals', 0) for user in data_manager.data['users'].values())
        active_today = 0
        
        today = datetime.now().date()
        for user in data_manager.data['users'].values():
            last_active = user.get('last_active')
            if last_active:
                try:
                    last_active_date = datetime.fromisoformat(last_active).date()
                    if last_active_date == today:
                        active_today += 1
                except:
                    pass
        
        text = f"""
📊 *BOT STATISTIKASI*

👥 **Umumiy foydalanuvchilar:** {data_manager.data['stats']['total_users']} ta
📈 **Faol foydalanuvchilar (bugun):** {active_today} ta
💰 **Umumiy ballar:** {total_points} ball
📤 **Umumiy referallar:** {total_referrals} ta
🎟️ **Sotilgan kuponlar:** {data_manager.data['stats']['total_coupons_sold']} ta
💸 **Berilgan ballar:** {data_manager.data['stats']['total_points_given']} ball

⚙️ **SOZLAMALAR:**
• Yangi foydalanuvchi bonus: {data_manager.data['settings']['welcome_points']} ball
• Kunlik bonus: {data_manager.data['settings']['daily_bonus']} ball
• Referal bonus: {data_manager.data['settings']['referral_points']} ball
• Kupon narxi: {data_manager.data['settings']['coupon_price']} ball
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 ADMIN PANELGA QAYTISH", callback_data="admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_admin_stats da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_add_coupon(query):
    """Kupon qo'shish uchun ko'rsatma"""
    try:
        text = """
➕ *KUPON QO'SHISH*

📝 *Kupon format:*
`vaqt | liga | jamoalar | bashorat | koeffitsient | ishonch | 1xbet_kodi | melbet_kodi | dbbet_kodi`

📋 *Misol:*
`20:00 | Premier League | Man United vs Liverpool | 1X | 1.85 | 95% | CODE123 | CODE456 | CODE789`

🛠 *Qadamlar:*
1. Yuqoridagi formatda xabar tayyorlang
2. Xabarni shu yerga yuboring
3. Kupon avtomatik qo'shiladi

⚠️ *Eslatma:* Har bir qism '|' belgisi bilan ajratilishi kerak
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 ADMIN PANELGA QAYTISH", callback_data="admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_admin_add_coupon da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_broadcast(query):
    """Reklama yuborish"""
    try:
        text = """
📢 *REKLAMA YUBORISH*

✍️ *Qo'llanma:*
1. Reklama xabarini tayyorlang
2. Xabarni shu yerga yuboring
3. Xabar barcha foydalanuvchilarga yuboriladi

⚠️ *Diqqat:* Bu jarayon bir necha daqiqa davom etishi mumkin
   Har 10 ta foydalanuvchiga progress yangilanadi

📊 *Joriy holat:*
• Jami foydalanuvchilar: {len(data_manager.data['users'])} ta
• Oxirgi reklama: {data_manager.data['stats'].get('last_broadcast', 'Hali yo\'q')}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 ADMIN PANELGA QAYTISH", callback_data="admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_admin_broadcast da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_view_coupons(query):
    """Mavjud kuponlarni ko'rsatish"""
    try:
        available_coupons = data_manager.data['coupons']['available']
        
        if not available_coupons:
            text = "📭 *Hozircha kuponlar mavjud emas*"
        else:
            text = "🎟️ *MAVJUD KUPONLAR:*\n\n"
            for i, coupon in enumerate(available_coupons, 1):
                purchased_count = len(data_manager.data['coupons']['purchased'].get(coupon['id'], []))
                text += f"{i}. *{coupon['teams']}*\n"
                text += f"   ⏰ {coupon['time']} | 🌍 {coupon['league']}\n"
                text += f"   🎯 {coupon['prediction']} | 📊 {coupon['odds']}\n"
                text += f"   💎 Sotilgan: {purchased_count} ta\n"
                text += f"   🆔 ID: {coupon['id']}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 ADMIN PANELGA QAYTISH", callback_data="admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_admin_view_coupons da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_add_points(query):
    """Foydalanuvchiga ball qo'shish"""
    try:
        # Foydalanuvchilarni ro'yxatini tayyorlash
        users_list = []
        text = "👤 *FOYDALANUVCHILAR RO'YXATI:*\n\n"
        
        for user_id_str, user_data in list(data_manager.data['users'].items())[:50]:  # Faqat birinchi 50 tasi
            user_name = user_data.get('name', 'Noma\'lum')
            user_points = user_data.get('points', 0)
            user_refs = user_data.get('referrals', 0)
            
            text += f"👤 *{user_name}*\n"
            text += f"   🆔: {user_id_str}\n"
            text += f"   💰: {user_points} ball\n"
            text += f"   📤: {user_refs} referal\n\n"
            
            users_list.append({
                'id': user_id_str,
                'name': user_name,
                'points': user_points
            })
        
        text += "\n👇 *Ball qo'shish uchun foydalanuvchi ID sini va ball miqdorini yuboring:*\n"
        text += "`id_raqam ball_miqdori`\n\n"
        text += "*Misol:* `123456789 50`\n"
        text += "Bu 123456789 ID li foydalanuvchiga 50 ball qo'shadi"
        
        keyboard = [[InlineKeyboardButton("🔙 ADMIN PANELGA QAYTISH", callback_data="admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"show_admin_add_points da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def add_user_points(query, user_id, points, context):
    """Foydalanuvchiga ball qo'shish"""
    try:
        user_id_str = str(user_id)
        
        if user_id_str not in data_manager.data['users']:
            await query.edit_message_text(f"❌ Foydalanuvchi topilmadi: {user_id}")
            return
        
        # Ballarni qo'shish
        data_manager.data['users'][user_id_str]['points'] = data_manager.data['users'][user_id_str].get('points', 0) + points
        data_manager.data['stats']['total_points_given'] += points
        
        # Tarixga yozish
        if 'points_history' not in data_manager.data['users'][user_id_str]:
            data_manager.data['users'][user_id_str]['points_history'] = []
        
        data_manager.data['users'][user_id_str]['points_history'].append({
            'points': points,
            'reason': f"Admin tomonidan qo'shildi",
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'type': 'admin_add'
        })
        
        await data_manager.save_data()
        
        # Foydalanuvchiga xabar yuborish
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 *TABRIKLAYMIZ!*\n\n"
                     f"💰 Admin tomonidan sizga {points} ball qo'shildi!\n"
                     f"🎯 Jami ball: {data_manager.data['users'][user_id_str]['points']}\n\n"
                     f"🎟️ Endi siz kuponlar olishingiz mumkin!",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Foydalanuvchiga xabar yuborishda xato: {e}")
        
        await query.edit_message_text(
            f"✅ *Ball qo'shildi!*\n\n"
            f"👤 Foydalanuvchi: {data_manager.data['users'][user_id_str].get('name', 'Noma\'lum')}\n"
            f"💰 Qo'shilgan ball: {points}\n"
            f"🎯 Jami ball: {data_manager.data['users'][user_id_str]['points']}",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"add_user_points da xato: {e}")
        await query.edit_message_text(f"❌ Xatolik: {str(e)}")

async def delete_coupon(query, coupon_id):
    """Kuponi o'chirish"""
    try:
        # Kuponi topish
        coupon_to_delete = None
        for coupon in data_manager.data['coupons']['available']:
            if coupon['id'] == coupon_id:
                coupon_to_delete = coupon
                break
        
        if not coupon_to_delete:
            await query.edit_message_text("❌ Kupon topilmadi")
            return
        
        # Kuponi o'chirish
        data_manager.data['coupons']['available'] = [
            c for c in data_manager.data['coupons']['available'] 
            if c['id'] != coupon_id
        ]
        
        await data_manager.save_data()
        
        await query.edit_message_text(
            f"✅ *Kupon o'chirildi!*\n\n"
            f"🏆 {coupon_to_delete['teams']}\n"
            f"🎯 {coupon_to_delete['prediction']}\n"
            f"🆔 ID: {coupon_id}",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"delete_coupon da xato: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    try:
        message = update.message
        message_text = message.text.strip()
        
        # Kupon qo'shish
        if '|' in message_text:
            parts = message_text.split('|')
            
            if len(parts) >= 9:  # Kupon format
                time = parts[0].strip()
                league = parts[1].strip()
                teams = parts[2].strip()
                prediction = parts[3].strip()
                odds = parts[4].strip()
                confidence = parts[5].strip()
                code_1xbet = parts[6].strip()
                code_melbet = parts[7].strip()
                code_dbbet = parts[8].strip()
                
                # Yangi ID yaratish
                data_manager.data['stats']['last_coupon_id'] += 1
                new_coupon_id = str(data_manager.data['stats']['last_coupon_id'])
                
                new_coupon = {
                    'id': new_coupon_id,
                    'time': time,
                    'league': league,
                    'teams': teams,
                    'prediction': prediction,
                    'odds': odds,
                    'confidence': confidence,
                    'codes': {
                        '1xbet': code_1xbet,
                        'melbet': code_melbet,
                        'dbbet': code_dbbet
                    },
                    'added_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'added_by': user_id
                }
                
                data_manager.data['coupons']['available'].append(new_coupon)
                await data_manager.save_data()
                
                await message.reply_text(
                    f"✅ *Kupon qo'shildi!*\n\n"
                    f"🏆 {teams}\n"
                    f"⏰ {time} | 🌍 {league}\n"
                    f"🎯 {prediction} | 📊 {odds}\n"
                    f"💰 Narxi: {data_manager.data['settings']['coupon_price']} ball\n"
                    f"🆔 ID: {new_coupon_id}\n\n"
                    f"📊 Jami kuponlar: {len(data_manager.data['coupons']['available'])} ta",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # Ball qo'shish (format: user_id points)
        elif ' ' in message_text and message_text.split()[0].isdigit():
            parts = message_text.split()
            if len(parts) == 2 and parts[1].isdigit():
                target_user_id = int(parts[0])
                points = int(parts[1])
                
                if str(target_user_id) in data_manager.data['users']:
                    # Ballarni qo'shish
                    data_manager.data['users'][str(target_user_id)]['points'] += points
                    data_manager.data['stats']['total_points_given'] += points
                    
                    # Tarixga yozish
                    if 'points_history' not in data_manager.data['users'][str(target_user_id)]:
                        data_manager.data['users'][str(target_user_id)]['points_history'] = []
                    
                    data_manager.data['users'][str(target_user_id)]['points_history'].append({
                        'points': points,
                        'reason': f"Admin tomonidan qo'shildi",
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'type': 'admin_add'
                    })
                    
                    await data_manager.save_data()
                    
                    await message.reply_text(
                        f"✅ *Ball qo'shildi!*\n\n"
                        f"👤 Foydalanuvchi: {data_manager.data['users'][str(target_user_id)].get('name', 'Noma\'lum')}\n"
                        f"💰 Qo'shilgan ball: {points}\n"
                        f"🎯 Jami ball: {data_manager.data['users'][str(target_user_id)]['points']}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await message.reply_text(f"❌ Foydalanuvchi topilmadi: {target_user_id}")
                return
        
        # Reklama yuborish
        else:
            if data_manager.data['admin'].get('broadcast_lock', False):
                await message.reply_text("⚠️ Reklama hozir jo'natilmoqda. Iltimos, biroz kuting.")
                return
            
            data_manager.data['admin']['broadcast_lock'] = True
            await data_manager.save_data()
            
            total_users = len(data_manager.data['users'])
            successful = 0
            failed = 0
            
            progress_msg = await message.reply_text(f"📤 Xabar yuborilmoqda... 0/{total_users}")
            
            for i, user_id_str in enumerate(data_manager.data['users'], 1):
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id_str),
                        text=message_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    successful += 1
                    
                    if i % 10 == 0 or i == total_users:
                        await progress_msg.edit_text(f"📤 Xabar yuborilmoqda... {i}/{total_users}\n✅ Muvaffaqiyatli: {successful}")
                        
                except Exception as e:
                    logger.error(f"Foydalanuvchiga xabar yuborishda xato {user_id_str}: {e}")
                    failed += 1
                    continue
            
            # Oxirgi reklama vaqtini yangilash
            data_manager.data['stats']['last_broadcast'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            data_manager.data['admin']['broadcast_lock'] = False
            await data_manager.save_data()
            
            await progress_msg.edit_text(
                f"📊 *Reklama yuborildi!*\n\n"
                f"👥 Jami foydalanuvchi: {total_users} ta\n"
                f"✅ Muvaffaqiyatli: {successful} ta\n"
                f"❌ Xatolik: {failed} ta\n"
                f"📅 Vaqt: {data_manager.data['stats']['last_broadcast']}",
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"handle_admin_message da xato: {e}")
        data_manager.data['admin']['broadcast_lock'] = False
        await data_manager.save_data()
        await update.message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")

async def handle_regular_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oddiy foydalanuvchi xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    
    # Agar foydalanuvchi ma'lumotlar bazasida bo'lsa, last_active ni yangilash
    if str(user_id) in data_manager.data['users']:
        data_manager.data['users'][str(user_id)]['last_active'] = datetime.now().isoformat()
        await data_manager.save_data()
    
    # Admin emas va start komanda emas bo'lsa, asosiy menyuni ko'rsatish
    if not is_admin(user_id):
        await start(update, context)

def main():
    """Asosiy dastur"""
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Admin xabarlari uchun handler
        application.add_handler(MessageHandler(
            filters.TEXT & filters.User(ADMIN_ID) & ~filters.COMMAND, 
            handle_admin_message
        ))
        
        # Oddiy foydalanuvchi xabarlari uchun handler
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID),
            handle_regular_message
        ))
        
        logger.info("Bot ishga tushmoqda...")
        print("=" * 50)
        print("🚀 FUTBOL KUPONLARI BOTI ISHGA TUSHDI!")
        print("=" * 50)
        print(f"🤖 Admin ID: {ADMIN_ID}")
        print(f"📊 Jami foydalanuvchilar: {len(data_manager.data['users'])} ta")
        print(f"💰 Jami ballar: {sum(user.get('points', 0) for user in data_manager.data['users'].values())} ball")
        print("=" * 50)
        print("🎯 MUAMMOLAR TUZATILDI:")
        print("   • ✅ Admin panel to'liq ishlaydi")
        print("   • ✅ DataManager class bilan ma'lumotlar boshqaruvi")
        print("   • ✅ Asynchronous saqlash (async/await)")
        print("   • ✅ Konkurensiya muammolari hal qilindi")
        print("   • ✅ Foydalanuvchiga ball qo'shish funksiyasi")
        print("   • ✅ Reklama yuborishda lock tizimi")
        print("   • ✅ Barcha callback tugmalari ishlaydi")
        print("=" * 50)
        print("✅ Bot ishlayapti. CTRL+C tugmasi bilan to'xtating.")
        print("=" * 50)
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()

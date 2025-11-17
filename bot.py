import os
import json
import logging
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta

# Bot tokeni
TOKEN = "8114630640:AAHSCef-rcKE0E5Hz0501Lvvl0AltMh0-Jk"

# Admin ID
ADMIN_ID = 7081746531

# Ma'lumotlarni saqlash fayli
DATA_FILE = "data.json"

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
        "today": {
            "date": "",
            "matches": [],
            "description": "🎯 Bugungi Bepul Kuponlar",
            "active": True,
            "coupon_codes": {
                "1xbet": "",
                "melbet": "",
                "dbbet": ""
            }
        },
        "ball_coupons": {
            "available": [],
            "purchased": {},
            "price": 15,
            "last_update": ""
        }
    },
    "stats": {
        "total_users": 0,
        "premium_users": 0,
        "today_users": 0,
        "today_referrals": 0,
        "total_points_given": 0,
        "total_coupons_sold": 0,
        "total_exchanges": 0
    },
    "admin_state": {}
}

def load_data():
    """Ma'lumotlarni yuklash"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ma'lumotlarni yuklashda xato: {e}")
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data.copy()

def save_data(data):
    """Ma'lumotlarni saqlash"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Saqlash xatosi: {e}")
        return False

# Global data o'zgaruvchisini ishga tushirish
data = load_data()

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_user_points(user_id):
    user_data = data['users'].get(str(user_id), {})
    return user_data.get('points', 0)

def add_user_points(user_id, points, reason=""):
    """Foydalanuvchiga ball qo'shish"""
    if str(user_id) not in data['users']:
        return False
    
    if 'points' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points'] = 0
    
    data['users'][str(user_id)]['points'] += points
    data['stats']['total_points_given'] += points
    
    if 'points_history' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points_history'] = []
    
    data['users'][str(user_id)]['points_history'].append({
        'points': points,
        'reason': reason,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'type': 'add'
    })
    
    return save_data(data)

def remove_user_points(user_id, points, reason=""):
    """Foydalanuvchidan ball olib tashlash"""
    if str(user_id) not in data['users']:
        return False
    
    if data['users'][str(user_id)].get('points', 0) < points:
        return False
    
    data['users'][str(user_id)]['points'] -= points
    
    if 'points_history' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points_history'] = []
    
    data['users'][str(user_id)]['points_history'].append({
        'points': -points,
        'reason': reason,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'type': 'remove'
    })
    
    return save_data(data)

def set_admin_state(user_id, state, data=None):
    """Admin holatini saqlash"""
    data['admin_state'][str(user_id)] = {
        'state': state,
        'data': data if data else {},
        'timestamp': datetime.now().timestamp()
    }
    save_data(data)

def get_admin_state(user_id):
    """Admin holatini olish"""
    return data['admin_state'].get(str(user_id), {})

def clear_admin_state(user_id):
    """Admin holatini tozalash"""
    if str(user_id) in data['admin_state']:
        del data['admin_state'][str(user_id)]
        save_data(data)

def find_user_by_username_or_id(search_term):
    """Foydalanuvchini username yoki ID bo'yicha topish"""
    search_term = str(search_term).strip()
    
    # ID bo'yicha qidirish
    if search_term in data['users']:
        user_data = data['users'][search_term]
        return {
            'user_id': int(search_term),
            'name': user_data.get('name', 'Noma lum'),
            'username': user_data.get('username', ''),
            'points': user_data.get('points', 0),
            'referrals': user_data.get('referrals', 0)
        }
    
    # Username bo'yicha qidirish (@ belgisiz)
    if search_term.startswith('@'):
        search_term = search_term[1:]
    
    for user_id, user_data in data['users'].items():
        username = user_data.get('username', '')
        if username and username.lower() == search_term.lower():
            return {
                'user_id': int(user_id),
                'name': user_data.get('name', 'Noma lum'),
                'username': username,
                'points': user_data.get('points', 0),
                'referrals': user_data.get('referrals', 0)
            }
    
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"Start command from user {user_id} ({user.first_name})")
        
        global data
        data = load_data()
        
        if str(user_id) not in data['users']:
            data['users'][str(user_id)] = {
                'name': user.first_name,
                'username': user.username,
                'referrals': 0,
                'points': 0,
                'premium': False,
                'joined_date': datetime.now().strftime("%Y-%m-%d"),
                'last_active': datetime.now().timestamp(),
                'points_history': []
            }
            data['stats']['total_users'] += 1
            data['stats']['today_users'] += 1
            save_data(data)
        
        welcome_text = f"""
🎉 *SALOM {user.first_name}!* 🏆

⚽ *FUTBOL BAHOLARI BOTIGA XUSH KELIBSIZ!*

💰 *HAR KUNI YANGI KUPONLAR!*
• 🎯 Kunlik bepul kuponlar
• 💰 Ball evaziga kuponlar
• 🎁 Bonuslar

📊 *SIZNING HOLATINGIZ:*
👥 Referallar: {data['users'][str(user_id)]['referrals']} ta
💰 Ballar: {data['users'][str(user_id)]['points']} ball
"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons"),
                InlineKeyboardButton("💰 BALL ALMASHISH", callback_data="exchange_points")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses"),
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link"),
                InlineKeyboardButton("ℹ️ YORDAM", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Start commandda xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        global data
        data = load_data()
        
        if query.data == "get_coupons":
            await show_coupon_selection(query, user_id)
        elif query.data == "get_free_coupon":
            await send_today_coupons(query)
        elif query.data == "exchange_points":
            await show_exchange_points(query, user_id)
        elif query.data == "bonuses":
            await show_bonuses(query)
        elif query.data == "my_points":
            await show_my_points(query, user_id)
        elif query.data == "get_referral_link":
            await show_referral_link(query, user_id)
        elif query.data == "help":
            await show_help(query)
        elif query.data == "back":
            await back_to_main(query)
        
        # ADMIN HANDLERLARI
        elif query.data == "admin":
            if is_admin(user_id):
                await show_admin_panel(query)
        elif query.data == "admin_stats":
            await show_admin_stats(query)
        elif query.data == "admin_manage_points":
            await show_admin_manage_points(query)
        elif query.data == "admin_manage_coupons":
            await show_admin_manage_coupons(query)
        elif query.data == "admin_broadcast":
            await show_admin_broadcast(query)
        elif query.data == "admin_back":
            await show_admin_panel(query)
        
        # Ball boshqarish handlerlari
        elif query.data.startswith("admin_add_points_"):
            target_user_id = int(query.data.split("_")[3])
            set_admin_state(user_id, "add_points", {"target_user_id": target_user_id})
            await query.edit_message_text(
                f"💰 *Ball qo'shish*\n\n"
                f"Foydalanuvchi: {data['users'].get(str(target_user_id), {}).get('name', 'Noma lum')}\n"
                f"Username: @{data['users'].get(str(target_user_id), {}).get('username', 'Mavjud emas')}\n"
                f"Joriy ball: {get_user_points(target_user_id)}\n\n"
                f"Qo'shmoqchi bo'lgan ball miqdorini yuboring:",
                parse_mode='Markdown'
            )
        elif query.data.startswith("admin_remove_points_"):
            target_user_id = int(query.data.split("_")[3])
            set_admin_state(user_id, "remove_points", {"target_user_id": target_user_id})
            await query.edit_message_text(
                f"💰 *Ball olib tashlash*\n\n"
                f"Foydalanuvchi: {data['users'].get(str(target_user_id), {}).get('name', 'Noma lum')}\n"
                f"Username: @{data['users'].get(str(target_user_id), {}).get('username', 'Mavjud emas')}\n"
                f"Joriy ball: {get_user_points(target_user_id)}\n\n"
                f"Olib tashlamoqchi bo'lgan ball miqdorini yuboring:",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")
        try:
            await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        except:
            pass

# ADMIN PANELI - Soddalashtirilgan
async def show_admin_panel(query):
    """Admin panelini ko'rsatish"""
    try:
        stats = get_user_statistics()
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        
        text = f"""
👑 *ADMIN PANELI*

📊 **Statistika:**
👥 Foydalanuvchilar: {stats['total_users']} ta
💰 Jami ballar: {total_points} ball
🎯 Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
💰 Ball kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta
"""

        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("🎯 Kupon Boshqarish", callback_data="admin_manage_coupons")],
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_stats(query):
    """Statistika sahifasi"""
    try:
        stats = get_user_statistics()
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        total_referrals = sum(user.get('referrals', 0) for user in data['users'].values())
        
        text = f"""
📊 *BATAFSIL STATISTIKA*

👥 **Foydalanuvchilar:**
• Jami: {stats['total_users']} ta
• Bugungi yangi: {stats['today_users']} ta
• Aktiv (7 kun): {stats['active_users']} ta

💰 **Ball Tizimi:**
• Jami berilgan: {data['stats']['total_points_given']} ball
• Foydalanuvchilarda: {total_points} ball
• Sotilgan kuponlar: {data['stats']['total_coupons_sold']} ta

📈 **Referallar:**
• Jami referallar: {total_referrals} ta
• Bugungi referallar: {stats['today_referrals']} ta

⚽ **Kuponlar:**
• Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
• Ball kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_stats da xato: {e}")

async def show_admin_manage_points(query):
    """Ball boshqarish sahifasi"""
    try:
        text = """
💰 *BALL BOSHQARISH*

Foydalanuvchi ballarini boshqarish uchun:

1️⃣ *Foydalanuvchi username yoki ID sini yuboring*
   - Username: `@username`
   - ID: `123456789`

2️⃣ *Foydalanuvchi topilgach ball qo'shish/olib tashlash imkoniyati*

📝 **Misol:**
`@username` yoki `123456789`
"""

        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Admin holatini qidirish rejimiga o'rnatish
        set_admin_state(query.from_user.id, "search_user")
        
    except Exception as e:
        logger.error(f"show_admin_manage_points da xato: {e}")

async def show_admin_manage_coupons(query):
    """Kupon boshqarish sahifasi"""
    try:
        text = f"""
🎯 *KUPON BOSHQARISH*

📊 **Joriy holat:**
• Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
• Ball kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta

📝 **Yangi kupon qo'shish formati:**

Bepul kupon:
`sana|vaqt|liga|jamoalar|bashorat|koeffitsient|ishonch|1xbet_kodi|melbet_kodi|dbbet_kodi`

Ball kupon:
`vaqt|liga|jamoalar|bashorat|koeffitsient|ishonch|1xbet_kodi|melbet_kodi|dbbet_kodi`

📋 **Misol:**
`2024-01-20|20:00|Premier League|Man City vs Arsenal|1X|1.50|85%|CODE123|CODE456|CODE789`
"""

        keyboard = [
            [InlineKeyboardButton("🗑️ Ball Kuponlarni Tozalash", callback_data="admin_clear_coupons")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_manage_coupons da xato: {e}")

async def show_admin_broadcast(query):
    """Reklama yuborish sahifasi"""
    try:
        text = f"""
📢 *REKLAMA YUBORISH*

Barcha {len(data['users'])} ta foydalanuvchilarga xabar yuborish:

📨 **Matn xabar:** Oddiy matn yuboring
🖼️ **Rasm xabar:** Rasm + taglavha yuboring

Xabar barcha foydalanuvchilarga yuboriladi.
"""

        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_broadcast da xato: {e}")

# ADMIN XABARLARINI QAYTA ISHLASH
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    try:
        message = update.message
        admin_state = get_admin_state(user_id)
        
        # Foydalanuvchi qidirish holati
        if admin_state.get('state') == 'search_user':
            search_term = message.text.strip()
            
            # Foydalanuvchini topish
            user = find_user_by_username_or_id(search_term)
            
            if user:
                text = f"""
👤 *FOYDALANUVCHI TOPILDI*

🏷️ **Ism:** {user['name']}
📱 **Username:** @{user['username'] if user['username'] else 'Mavjud emas'}
🆔 **ID:** {user['user_id']}
💰 **Ballar:** {user['points']} ball
👥 **Referallar:** {user['referrals']} ta

Quyidagi amallardan birini tanlang:
"""
                keyboard = [
                    [
                        InlineKeyboardButton("➕ Ball Qo'shish", callback_data=f"admin_add_points_{user['user_id']}"),
                        InlineKeyboardButton("➖ Ball Olib Tashlash", callback_data=f"admin_remove_points_{user['user_id']}")
                    ],
                    [InlineKeyboardButton("💰 Boshqa Foydalanuvchi Qidirish", callback_data="admin_manage_points")],
                    [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
                    [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                clear_admin_state(user_id)
            else:
                await message.reply_text(
                    f"❌ *'{search_term}'* topilmadi!\n\n"
                    f"Qaytadan urinib ko'ring yoki boshqa username/ID kiriting.",
                    parse_mode='Markdown'
                )
            return
        
        # Ball qo'shish/olib tashlash holati
        elif admin_state.get('state') in ['add_points', 'remove_points']:
            try:
                points = int(message.text)
                target_user_id = admin_state['data']['target_user_id']
                
                if admin_state['state'] == 'add_points':
                    if add_user_points(target_user_id, points, f"Admin tomonidan qo'shildi"):
                        user_data = data['users'].get(str(target_user_id), {})
                        await message.reply_text(
                            f"✅ *Ball qo'shildi!*\n\n"
                            f"👤 Foydalanuvchi: {user_data.get('name', 'Noma lum')}\n"
                            f"💰 Qo'shildi: {points} ball\n"
                            f"🎯 Jami ball: {get_user_points(target_user_id)}",
                            parse_mode='Markdown'
                        )
                    else:
                        await message.reply_text("❌ Ball qo'shishda xatolik!")
                
                elif admin_state['state'] == 'remove_points':
                    if remove_user_points(target_user_id, points, f"Admin tomonidan olib tashlandi"):
                        user_data = data['users'].get(str(target_user_id), {})
                        await message.reply_text(
                            f"✅ *Ball olib tashlandi!*\n\n"
                            f"👤 Foydalanuvchi: {user_data.get('name', 'Noma lum')}\n"
                            f"💰 Olib tashlandi: {points} ball\n"
                            f"🎯 Qolgan ball: {get_user_points(target_user_id)}",
                            parse_mode='Markdown'
                        )
                    else:
                        await message.reply_text("❌ Ball olib tashlashda xatolik! Ball yetarli emas.")
                
                clear_admin_state(user_id)
                return
                
            except ValueError:
                await message.reply_text("❌ Iltimos, faqat raqam yuboring!")
                return
        
        # Kupon qo'shish
        if '|' in message.text:
            parts = message.text.split('|')
            
            if len(parts) == 10:  # Bepul kupon
                date, time, league, teams, prediction, odds, confidence, code_1xbet, code_melbet, code_dbbet = parts
                
                new_match = {
                    'time': time.strip(),
                    'league': league.strip(),
                    'teams': teams.strip(),
                    'prediction': prediction.strip(),
                    'odds': odds.strip(),
                    'confidence': confidence.strip()
                }
                
                data['coupons']['today']['matches'].append(new_match)
                data['coupons']['today']['date'] = date.strip()
                data['coupons']['today']['coupon_codes'] = {
                    "1xbet": code_1xbet.strip(),
                    "melbet": code_melbet.strip(),
                    "dbbet": code_dbbet.strip()
                }
                save_data(data)
                
                await message.reply_text(
                    f"✅ *Bepul kupon qo'shildi!*\n\n"
                    f"🏆 {teams.strip()}\n"
                    f"⏰ {time.strip()} | {league.strip()}\n"
                    f"🎯 {prediction.strip()} | 📊 {odds.strip()}\n\n"
                    f"📊 Jami bepul kuponlar: {len(data['coupons']['today']['matches'])} ta",
                    parse_mode='Markdown'
                )
                
            elif len(parts) == 9:  # Ball kupon
                time, league, teams, prediction, odds, confidence, code_1xbet, code_melbet, code_dbbet = parts
                
                new_coupon = {
                    'time': time.strip(),
                    'league': league.strip(),
                    'teams': teams.strip(),
                    'prediction': prediction.strip(),
                    'odds': odds.strip(),
                    'confidence': confidence.strip(),
                    'codes': {
                        '1xbet': code_1xbet.strip(),
                        'melbet': code_melbet.strip(),
                        'dbbet': code_dbbet.strip()
                    },
                    'added_date': datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                data['coupons']['ball_coupons']['available'].append(new_coupon)
                data['coupons']['ball_coupons']['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(data)
                
                await message.reply_text(
                    f"✅ *Ball kupon qo'shildi!*\n\n"
                    f"🏆 {teams.strip()}\n"
                    f"⏰ {time.strip()} | {league.strip()}\n"
                    f"🎯 {prediction.strip()} | 📊 {odds.strip()}\n"
                    f"💰 Narxi: 15 ball\n\n"
                    f"📊 Jami ball kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta",
                    parse_mode='Markdown'
                )
        
        # Reklama yuborish
        else:
            total_users = len(data['users'])
            successful = 0
            
            progress_msg = await message.reply_text(f"📤 Xabar yuborilmoqda... 0/{total_users}")
            
            for i, user_id_str in enumerate(data['users']):
                try:
                    if message.text:
                        await context.bot.send_message(
                            chat_id=int(user_id_str),
                            text=message.text,
                            parse_mode='Markdown'
                        )
                    elif message.photo:
                        await context.bot.send_photo(
                            chat_id=int(user_id_str),
                            photo=message.photo[-1].file_id,
                            caption=message.caption,
                            parse_mode='Markdown'
                        )
                    successful += 1
                    
                    if i % 10 == 0:
                        await progress_msg.edit_text(f"📤 Xabar yuborilmoqda... {i}/{total_users}")
                        
                except Exception as e:
                    logger.error(f"Foydalanuvchiga xabar yuborishda xato {user_id_str}: {e}")
                    continue
            
            await progress_msg.edit_text(
                f"📊 *Reklama yuborildi!*\n\n"
                f"👥 Jami foydalanuvchi: {total_users} ta\n"
                f"✅ Muvaffaqiyatli: {successful} ta\n"
                f"❌ Xatolik: {total_users - successful} ta",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"handle_admin_message da xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# YORDAMCHI FUNKSIYALAR
async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons"),
                InlineKeyboardButton("💰 BALL ALMASHISH", callback_data="exchange_points")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses"),
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link"),
                InlineKeyboardButton("ℹ️ YORDAM", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 *Asosiy Menyu*\n\nBall to'plang, kuponlar oling va yutuqlarga erishing! 🚀",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"back_to_main da xato: {e}")

def get_user_statistics():
    """Foydalanuvchi statistikasini hisoblash"""
    total_users = len(data['users'])
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_users = sum(1 for user in data['users'].values() if user.get('joined_date') == today)
    
    today_referrals = sum(user.get('referrals', 0) for user in data['users'].values() if user.get('joined_date') == today)
    
    active_users = 0
    week_ago = datetime.now().timestamp() - 7 * 24 * 60 * 60
    for user_id, user_data in data['users'].items():
        last_active = user_data.get('last_active', 0)
        if last_active > week_ago:
            active_users += 1
    
    return {
        'total_users': total_users,
        'today_users': today_users,
        'today_referrals': today_referrals,
        'active_users': active_users
    }

# QOLGAN FOYDALANUVCHI FUNKSIYALARI (qisqartirilgan)
async def show_coupon_selection(query, user_id):
    """Kupon olish sahifasi"""
    try:
        user_points = get_user_points(user_id)
        
        text = f"""
🎯 *KUPON OLISH*

💰 **Sizning balansingiz:** {user_points} ball

💎 *Quyidagi kuponlardan birini tanlang:*
"""

        keyboard = [
            [InlineKeyboardButton("🎯 BEPUL KUPON OLISH", callback_data="get_free_coupon")],
            [InlineKeyboardButton("💰 Ball Almashish", callback_data="exchange_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_coupon_selection da xato: {e}")

async def send_today_coupons(query):
    """Bepul kuponlarni yuborish"""
    try:
        today_coupons = data['coupons']['today']
        
        if not today_coupons['active'] or not today_coupons['matches']:
            await query.edit_message_text(
                "📭 *Hozircha bepul kuponlar mavjud emas*",
                parse_mode='Markdown'
            )
            return
        
        coupon_text = f"🎯 *{today_coupons['description']}*\n\n"
        
        for i, match in enumerate(today_coupons['matches'], 1):
            coupon_text += f"*{i}. {match['time']} - {match['league']}*\n"
            coupon_text += f"🏆 `{match['teams']}`\n"
            coupon_text += f"🎯 **Bashorat:** `{match['prediction']}`\n"
            coupon_text += f"📊 **Koeffitsient:** `{match['odds']}`\n\n"
        
        keyboard = [
            [InlineKeyboardButton("💰 Yana Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(coupon_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"send_today_coupons da xato: {e}")

# Qolgan foydalanuvchi funksiyalari...
async def show_exchange_points(query, user_id):
    await query.edit_message_text("💰 Ball almashish uchun @baxtga_olga ga murojaat qiling!", parse_mode='Markdown')

async def show_bonuses(query):
    await query.edit_message_text("🎁 Bonuslar bo'limi", parse_mode='Markdown')

async def show_my_points(query, user_id):
    user_data = data['users'].get(str(user_id), {})
    await query.edit_message_text(f"💰 Ballaringiz: {user_data.get('points', 0)} ball", parse_mode='Markdown')

async def show_referral_link(query, user_id):
    bot_username = (await query.message._bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    await query.edit_message_text(f"📤 Referal havolangiz:\n`{ref_link}`", parse_mode='Markdown')

async def show_help(query):
    await query.edit_message_text("ℹ️ Yordam bo'limi", parse_mode='Markdown')

# ASOSIY DASTUR
def main():
    """Asosiy dastur"""
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_admin_message))
        
        logger.info("Bot ishga tushmoqda...")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🤖 Bot ishlayapti...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()

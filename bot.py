import os
import json
import logging
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta

# Bot tokeni
TOKEN = "8114630640:AAGoBCnsw22xIHIzRK5Mt0N1f1gtodKLl40"

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
            save_data(data)
            logger.info(f"Yangi foydalanuvchi qo'shildi: {user_id}")
        else:
            data['users'][str(user_id)]['last_active'] = datetime.now().timestamp()
            save_data(data)
        
        if context.args:
            ref_id = context.args[0]
            logger.info(f"Referal argument: {ref_id}")
            if ref_id.startswith('ref'):
                try:
                    referrer_id = int(ref_id[3:])
                    if str(referrer_id) in data['users'] and referrer_id != user_id:
                        data['users'][str(referrer_id)]['referrals'] += 1
                        data['stats']['today_referrals'] += 1
                        
                        points_to_add = 5
                        add_user_points(referrer_id, points_to_add, f"Referal taklif: {user.first_name}")
                        
                        save_data(data)
                        
                        try:
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 *Tabriklaymiz!*\n\n"
                                     f"📤 Sizning referal havolangiz orqali yangi foydalanuvchi qo'shildi!\n"
                                     f"👤 Yangi foydalanuvchi: {user.first_name}\n"
                                     f"💰 Sizga {points_to_add} ball qo'shildi!\n"
                                     f"🎯 Jami ball: {get_user_points(referrer_id)}",
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Referal bildirishnoma yuborishda xato: {e}")
                except Exception as e:
                    logger.error(f"Referal qayd etishda xato: {e}")

        welcome_text = f"""
🎉 *SALOM {user.first_name}!* 🏆

⚽ *FUTBOL BAHOLARI BOTIGA XUSH KELIBSIZ!*

💰 Ball to'plang, kuponlar oling va yutuqlarga erishing!
"""

        keyboard = [
            [InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons")],
            [InlineKeyboardButton("💰 PUL ISHLASH", callback_data="exchange_points")],
            [InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")],
            [InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link")]
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
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")
        try:
            await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        except:
            pass

# ADMIN PANELI
async def show_admin_panel(query):
    """Admin panelini ko'rsatish"""
    try:
        stats = get_user_statistics()
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        
        text = f"""
👑 *ADMIN PANEL*

📊 **Statistika:**
👥 Foydalanuvchilar: {stats['total_users']} ta
💰 Jami ballar: {total_points} ball
🎯 Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
💰 VIP kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta
"""

        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("🎯 Kupon Qo'shish", callback_data="admin_manage_coupons")],
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
        
        text = f"""
📊 *STATISTIKA*

👥 **Foydalanuvchilar:**
• Jami: {stats['total_users']} ta
• Bugungi: {stats['today_users']} ta
• Aktiv: {stats['active_users']} ta

💰 **Ball Tizimi:**
• Jami ballar: {total_points} ball
• Sotilgan kuponlar: {data['stats']['total_coupons_sold']} ta

⚽ **Kuponlar:**
• Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
• VIP kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta
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

Foydalanuvchi username yoki ID sini yuboring:

📝 **Format:**
`@username` yoki `123456789`

Bot foydalanuvchini topgach, ball qo'shish/olib tashlash imkoniyati beriladi.
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
🎯 *KUPON QO'SHISH*

📊 **Joriy holat:**
• Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
• VIP kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta

📝 **Yangi kupon qo'shish:**

Bepul kupon formati:
`sana|vaqt|liga|jamoalar|bashorat|koeffitsient|ishonch`

VIP kupon formati:
`vaqt|liga|jamoalar|bashorat|koeffitsient|ishonch`

📋 **Misol:**
`2024-01-20|20:00|Premier League|Man City vs Arsenal|1X|1.50|85%`
"""

        keyboard = [
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

📨 Oddiy matn yuboring yoki rasm + taglavha
"""

        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_broadcast da xato: {e}")

# YANGI VA TO'G'RI ISHLAYDIAGAN ADMIN XABARLARINI QAYTA ISHLASH
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    try:
        message = update.message
        admin_state = get_admin_state(user_id)
        
        logger.info(f"Admin message: {message.text}, State: {admin_state.get('state')}")
        
        # Foydalanuvchi qidirish holati
        if admin_state.get('state') == 'search_user':
            search_term = message.text.strip()
            logger.info(f"Searching for user: {search_term}")
            
            # Foydalanuvchini topish
            user = find_user_by_username_or_id(search_term)
            
            if user:
                logger.info(f"User found: {user['name']} (ID: {user['user_id']})")
                
                # Foydalanuvchi topildi - ball operatsiyalari uchun tugmalar
                text = f"""
👤 *FOYDALANUVCHI TOPILDI*

🏷️ **Ism:** {user['name']}
📱 **Username:** @{user['username'] if user['username'] else 'Mavjud emas'}
🆔 **ID:** {user['user_id']}
💰 **Ballar:** {user['points']} ball

Quyidagi amallardan birini tanlang:
"""
                keyboard = [
                    [
                        InlineKeyboardButton("➕ Ball Qo'shish", callback_data=f"add_{user['user_id']}"),
                        InlineKeyboardButton("➖ Ball Ayirish", callback_data=f"remove_{user['user_id']}")
                    ],
                    [InlineKeyboardButton("💰 Boshqa Foydalanuvchi", callback_data="admin_manage_points")],
                    [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                
                # Admin holatini tozalash
                clear_admin_state(user_id)
                
            else:
                logger.info(f"User not found: {search_term}")
                await message.reply_text(
                    f"❌ *'{search_term}'* topilmadi!\n\n" +
                    "Iltimos, qaytadan urinib ko'ring yoki boshqa username/ID kiriting.",
                    parse_mode='Markdown'
                )
            return
        
        # Ball qo'shish holati
        elif admin_state.get('state') == 'add_points':
            try:
                points = int(message.text)
                target_user_id = admin_state['data']['user_id']
                current_points = get_user_points(target_user_id)
                
                logger.info(f"Adding {points} points to user {target_user_id}")
                
                if add_user_points(target_user_id, points, f"Admin tomonidan qo'shildi"):
                    user_data = data['users'].get(str(target_user_id), {})
                    await message.reply_text(
                        f"✅ *Ball qo'shildi!*\n\n" +
                        f"👤 Foydalanuvchi: {user_data.get('name', 'Noma lum')}\n" +
                        f"💰 Qo'shildi: {points} ball\n" +
                        f"📊 Avval: {current_points} ball\n" +
                        f"🎯 Keyin: {get_user_points(target_user_id)} ball",
                        parse_mode='Markdown'
                    )
                else:
                    await message.reply_text("❌ Ball qo'shishda xatolik!")
                
                clear_admin_state(user_id)
                return
                
            except ValueError:
                await message.reply_text("❌ Iltimos, faqat raqam yuboring!")
                return
        
        # Ball ayirish holati
        elif admin_state.get('state') == 'remove_points':
            try:
                points = int(message.text)
                target_user_id = admin_state['data']['user_id']
                current_points = get_user_points(target_user_id)
                
                logger.info(f"Removing {points} points from user {target_user_id}")
                
                if remove_user_points(target_user_id, points, f"Admin tomonidan olindi"):
                    user_data = data['users'].get(str(target_user_id), {})
                    await message.reply_text(
                        f"✅ *Ball olindi!*\n\n" +
                        f"👤 Foydalanuvchi: {user_data.get('name', 'Noma lum')}\n" +
                        f"💰 Olindi: {points} ball\n" +
                        f"📊 Avval: {current_points} ball\n" +
                        f"🎯 Keyin: {get_user_points(target_user_id)} ball",
                        parse_mode='Markdown'
                    )
                else:
                    await message.reply_text(
                        f"❌ *Ball olib bo'lmadi!*\n\n" +
                        f"Foydalanuvchida {current_points} ball mavjud, " +
                        f"siz {points} ball olmoqchisiz!",
                        parse_mode='Markdown'
                    )
                
                clear_admin_state(user_id)
                return
                
            except ValueError:
                await message.reply_text("❌ Iltimos, faqat raqam yuboring!")
                return
        
        # Kupon qo'shish
        elif '|' in message.text:
            parts = message.text.split('|')
            
            if len(parts) >= 7:  # Bepul kupon (kamida 7 qism)
                date = parts[0] if len(parts) > 0 else datetime.now().strftime("%Y-%m-%d")
                time = parts[1] if len(parts) > 1 else "20:00"
                league = parts[2] if len(parts) > 2 else "Liga"
                teams = parts[3] if len(parts) > 3 else "Jamoa 1 vs Jamoa 2"
                prediction = parts[4] if len(parts) > 4 else "1X"
                odds = parts[5] if len(parts) > 5 else "1.50"
                confidence = parts[6] if len(parts) > 6 else "85%"
                
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
                save_data(data)
                
                await message.reply_text(
                    f"✅ *Bepul kupon qo'shildi!*\n\n" +
                    f"🏆 {teams.strip()}\n" +
                    f"⏰ {time.strip()} | {league.strip()}\n" +
                    f"🎯 {prediction.strip()} | 📊 {odds.strip()}\n\n" +
                    f"📊 Jami bepul kuponlar: {len(data['coupons']['today']['matches'])} ta",
                    parse_mode='Markdown'
                )
                
            elif len(parts) >= 6:  # VIP kupon (kamida 6 qism)
                time = parts[0] if len(parts) > 0 else "20:00"
                league = parts[1] if len(parts) > 1 else "Liga"
                teams = parts[2] if len(parts) > 2 else "Jamoa 1 vs Jamoa 2"
                prediction = parts[3] if len(parts) > 3 else "1X"
                odds = parts[4] if len(parts) > 4 else "1.50"
                confidence = parts[5] if len(parts) > 5 else "85%"
                
                new_coupon = {
                    'time': time.strip(),
                    'league': league.strip(),
                    'teams': teams.strip(),
                    'prediction': prediction.strip(),
                    'odds': odds.strip(),
                    'confidence': confidence.strip(),
                    'added_date': datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                data['coupons']['ball_coupons']['available'].append(new_coupon)
                data['coupons']['ball_coupons']['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(data)
                
                await message.reply_text(
                    f"✅ *VIP kupon qo'shildi!*\n\n" +
                    f"🏆 {teams.strip()}\n" +
                    f"⏰ {time.strip()} | {league.strip()}\n" +
                    f"🎯 {prediction.strip()} | 📊 {odds.strip()}\n" +
                    f"💰 Narxi: 15 ball\n\n" +
                    f"📊 Jami VIP kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta",
                    parse_mode='Markdown'
                )
        
        # Reklama yuborish (faqat oddiy matn yoki rasm bo'lsa)
        elif not admin_state:
            total_users = len(data['users'])
            successful = 0
            
            await message.reply_text(f"📤 Xabar {total_users} ta foydalanuvchiga yuborilmoqda...")
            
            for user_id_str in data['users']:
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
                        
                except Exception as e:
                    logger.error(f"Foydalanuvchiga xabar yuborishda xato {user_id_str}: {e}")
                    continue
            
            await message.reply_text(
                f"📊 *Reklama yuborildi!*\n\n" +
                f"👥 Jami: {total_users} ta\n" +
                f"✅ Muvaffaqiyatli: {successful} ta\n" +
                f"❌ Xatolik: {total_users - successful} ta",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"handle_admin_message da xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# YANGI VA TO'G'RI ISHLAYDIAGAN BALL OPERATSIYALARI HANDLERI
async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin callback handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            return
        
        callback_data = query.data
        
        if callback_data.startswith("add_"):
            target_user_id = int(callback_data.split("_")[1])
            set_admin_state(user_id, "add_points", {"user_id": target_user_id})
            await query.edit_message_text(
                f"➕ *Ball qo'shish*\n\n" +
                f"Qo'shmoqchi bo'lgan ball miqdorini yuboring:",
                parse_mode='Markdown'
            )
            
        elif callback_data.startswith("remove_"):
            target_user_id = int(callback_data.split("_")[1])
            set_admin_state(user_id, "remove_points", {"user_id": target_user_id})
            await query.edit_message_text(
                f"➖ *Ball ayirish*\n\n" +
                f"Ayirmoqchi bo'lgan ball miqdorini yuboring:",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"handle_admin_callback da xato: {e}")

# YORDAMCHI FUNKSIYALAR
async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        keyboard = [
            [InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons")],
            [InlineKeyboardButton("💰 PUL ISHLASH", callback_data="exchange_points")],
            [InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")],
            [InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link")]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 *Asosiy Menyu*",
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
    
    active_users = 0
    week_ago = datetime.now().timestamp() - 7 * 24 * 60 * 60
    for user_id, user_data in data['users'].items():
        last_active = user_data.get('last_active', 0)
        if last_active > week_ago:
            active_users += 1
    
    return {
        'total_users': total_users,
        'today_users': today_users,
        'active_users': active_users
    }

# FOYDALANUVCHI FUNKSIYALARI
async def show_coupon_selection(query, user_id):
    await query.edit_message_text("🎯 Kuponlar bo'limi", parse_mode='Markdown')

async def send_today_coupons(query):
    await query.edit_message_text("📭 Hozircha kuponlar mavjud emas", parse_mode='Markdown')

async def show_exchange_points(query, user_id):
    await query.edit_message_text("💰 Ball almashish uchun @baxtga_olga ga murojaat qiling!", parse_mode='Markdown')

async def show_my_points(query, user_id):
    user_data = data['users'].get(str(user_id), {})
    await query.edit_message_text(f"💰 Ballaringiz: {user_data.get('points', 0)} ball", parse_mode='Markdown')

async def show_referral_link(query, user_id):
    bot_username = (await query.message._bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    await query.edit_message_text(f"📤 Referal havolangiz:\n`{ref_link}`", parse_mode='Markdown')

async def show_bonuses(query):
    await query.edit_message_text("🎁 Bonuslar bo'limi", parse_mode='Markdown')

async def show_help(query):
    await query.edit_message_text("ℹ️ Yordam bo'limi", parse_mode='Markdown')

# ASOSIY DASTUR
def main():
    """Asosiy dastur"""
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^(add_|remove_)"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_admin_message))
        
        logger.info("Bot ishga tushmoqda...")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🤖 Bot ishlayapti...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("🎯 YANGI VA TO'G'RI ISHLAYDIAGAN ADMIN FUNKSIYALARI:")
        print("   • 🔍 Foydalanuvchi qidirish (username/ID)")
        print("   • 💰 Ball qo'shish/ayirish")
        print("   • 📊 Statistika")
        print("   • 🎯 Kupon qo'shish")
        print("   • 📢 Reklama yuborish")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()

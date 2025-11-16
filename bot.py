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
        "premium": {
            "date": "",
            "matches": [],
            "description": "💎 VIP Premium Kuponlar",
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
    "settings": {
        "min_referrals": 20,
        "referral_points": 5,
        "coupon_price": 15,
        "premium_price": 100000,
        "currency": "so'm",
        "payment_details": "💳 *To'lov qilish uchun:*\n\n🏦 **HUMO:** `9860356622837710`\n📱 **Payme:** `mavjud emas`\n💳 **Uzumbank visa:** `4916990318695001`\n\n✅ To'lov qilgach, chek skrinshotini @baxtga_olga ga yuboring."
    },
    "stats": {
        "total_users": 0,
        "premium_users": 0,
        "today_users": 0,
        "today_referrals": 0,
        "total_points_given": 0,
        "total_coupons_sold": 0
    }
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

def is_premium(user_id):
    user_data = data['users'].get(str(user_id), {})
    return user_data.get('premium', False)

def get_user_points(user_id):
    user_data = data['users'].get(str(user_id), {})
    return user_data.get('points', 0)

def get_user_referrals(user_id):
    user_data = data['users'].get(str(user_id), {})
    return user_data.get('referrals', 0)

def add_user_points(user_id, points, reason=""):
    """Foydalanuvchiga ball qo'shish"""
    if str(user_id) not in data['users']:
        return False
    
    if 'points' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points'] = 0
    
    data['users'][str(user_id)]['points'] += points
    data['stats']['total_points_given'] += points
    
    # Ball tarixini saqlash
    if 'points_history' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points_history'] = []
    
    data['users'][str(user_id)]['points_history'].append({
        'points': points,
        'reason': reason,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    return save_data(data)

def get_random_ball_coupon():
    """Tasodifiy ball kuponini olish"""
    ball_coupons = data['coupons']['ball_coupons']['available']
    if not ball_coupons:
        return None
    return random.choice(ball_coupons)

def remove_ball_coupon(coupon):
    """Ball kuponini olib tashlash"""
    if coupon in data['coupons']['ball_coupons']['available']:
        data['coupons']['ball_coupons']['available'].remove(coupon)
        return save_data(data)
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"Start command from user {user_id} ({user.first_name})")
        
        # Ma'lumotlarni qayta yuklash
        global data
        data = load_data()
        
        # Yangi foydalanuvchi
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
            # Faollikni yangilash
            data['users'][str(user_id)]['last_active'] = datetime.now().timestamp()
            save_data(data)
        
        # Referal tekshirish
        if context.args:
            ref_id = context.args[0]
            logger.info(f"Referal argument: {ref_id}")
            if ref_id.startswith('ref'):
                try:
                    referrer_id = int(ref_id[3:])
                    if str(referrer_id) in data['users'] and referrer_id != user_id:
                        # Referal sonini oshirish
                        data['users'][str(referrer_id)]['referrals'] += 1
                        data['stats']['today_referrals'] += 1
                        
                        # Ball qo'shish
                        points_to_add = data['settings']['referral_points']
                        add_user_points(referrer_id, points_to_add, f"Referal: {user.first_name}")
                        
                        save_data(data)
                        
                        # Referal egasiga xabar berish
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
                            logger.info(f"Referal bildirishnoma yuborildi: {referrer_id}")
                        except Exception as e:
                            logger.error(f"Referal bildirishnoma yuborishda xato: {e}")
                except Exception as e:
                    logger.error(f"Referal qayd etishda xato: {e}")

        # Soddalashtirilgan tugmalar
        keyboard = [
            [
                InlineKeyboardButton("🎯 Kuponlar Olish", callback_data="get_coupons"),
                InlineKeyboardButton("💎 VIP Kuponlar", callback_data="premium_coupons")
            ],
            [
                InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points"),
                InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("ℹ️ Yordam", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Yangilangan start xabari
        welcome_text = f"""
🎉 *Salom {user.first_name}!* 👋

⚽ *Futbol Kuponlari Botiga Xush Kelibsiz!*

💰 *YANGI BALL TIZIMI:*
• 📤 Har bir referal = *{data['settings']['referral_points']} ball*
• 🎯 {data['settings']['coupon_price']} ball = *1 ta ekskluziv kupon*
• 💎 {data['settings']['min_referrals']} ta referal = *Bepul VIP*

📊 *Sizning holatingiz:*
👥 Referallar: {get_user_referrals(user_id)}/{data['settings']['min_referrals']} ta
💰 Ballar: {get_user_points(user_id)} ball

🎯 *Kupon olish usullari:*
1. 🎯 **Bepul kuponlar** - Har kuni yangilanadi
2. 💰 **Ball evaziga** - {data['settings']['coupon_price']} ball = 1 kupon
3. 💎 **VIP kuponlar** - Ekskluziv bashoratlar

*Ball to'plang va qimmat kuponlarga ega bo'ling!* 🚀
"""
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"Start xabari muvaffaqiyatli yuborildi: {user_id}")
        
    except Exception as e:
        logger.error(f"Start commandda xato: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            parse_mode='Markdown'
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        logger.info(f"Button handler: {query.data} from user {user_id}")
        
        # Ma'lumotlarni yangilash
        global data
        data = load_data()
        
        if query.data == "get_coupons":
            await show_coupon_selection(query, user_id)
        elif query.data == "get_free_coupon":
            await send_today_coupons(query)
        elif query.data == "get_ball_coupon":
            await get_ball_coupon(query, user_id)
        elif query.data == "premium_coupons":
            await handle_premium_coupons(query, user_id)
        elif query.data == "my_points":
            await show_my_points(query, user_id)
        elif query.data == "get_referral_link":
            await show_referral_link(query, user_id)
        elif query.data == "share_referral":
            await share_referral_link(query, user_id)
        elif query.data == "buy_premium":
            await show_premium_payment(query, user_id)
        elif query.data == "help":
            await show_help(query)
        elif query.data == "back":
            await back_to_main(query)
        elif query.data == "back_to_coupons":
            await back_to_coupon_selection(query)
        elif query.data == "admin":
            if is_admin(user_id):
                await show_admin_panel(query)
            else:
                await query.message.reply_text("❌ Siz admin emassiz!")
        else:
            await query.message.reply_text("❌ Noma'lum buyruq!")
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")
        try:
            await update.callback_query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        except:
            pass

async def show_coupon_selection(query, user_id):
    """Kupon olish sahifasi"""
    try:
        user_points = get_user_points(user_id)
        coupon_price = data['settings']['coupon_price']
        
        text = f"""
🎯 *KUPON OLISH*

💰 **Sizning balansingiz:** {user_points} ball
💵 **1 kupon narxi:** {coupon_price} ball

🎁 *Quyidagi usullardan kupon olishingiz mumkin:*
"""

        keyboard = [
            [InlineKeyboardButton("🎯 BEPUL KUPON OLISH", callback_data="get_free_coupon")],
        ]
        
        # Agar ball yetarli bo'lsa, ball kupon tugmasini ko'rsatish
        if user_points >= coupon_price:
            keyboard.append([InlineKeyboardButton(f"💰 BALL EVAZIGA KUPON OLISH ({coupon_price} ball)", callback_data="get_ball_coupon")])
        else:
            text += f"\n❌ *Ball yetarli emas!*\nBall to'plash uchun referal havolangizni tarqating."
            keyboard.append([InlineKeyboardButton("📤 BAL TO'PLASH", callback_data="get_referral_link")])
        
        keyboard.append([InlineKeyboardButton("💎 VIP KUPONLAR", callback_data="premium_coupons")])
        keyboard.append([InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_coupon_selection da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def get_ball_coupon(query, user_id):
    """Ball evaziga kupon olish"""
    try:
        user_points = get_user_points(user_id)
        coupon_price = data['settings']['coupon_price']
        
        if user_points < coupon_price:
            await query.message.reply_text(
                f"❌ Ballaringiz yetarli emas!\n"
                f"💰 Sizda: {user_points} ball\n"
                f"💵 Kerak: {coupon_price} ball\n\n"
                f"📤 Ball to'plash uchun referal havolangizni tarqating!",
                parse_mode='Markdown'
            )
            return await show_coupon_selection(query, user_id)
        
        # Tasodifiy kupon olish
        coupon = get_random_ball_coupon()
        if not coupon:
            await query.message.reply_text(
                "❌ Hozircha mavjud kuponlar yo'q. Tez orada yangilanadi! 🔄",
                parse_mode='Markdown'
            )
            return await show_coupon_selection(query, user_id)
        
        # Ballarni hisobdan olib tashlash
        data['users'][str(user_id)]['points'] -= coupon_price
        data['stats']['total_coupons_sold'] += 1
        
        # Kuponni foydalanuvchiga berish
        if 'purchased' not in data['coupons']['ball_coupons']:
            data['coupons']['ball_coupons']['purchased'] = {}
        
        if str(user_id) not in data['coupons']['ball_coupons']['purchased']:
            data['coupons']['ball_coupons']['purchased'][str(user_id)] = []
        
        data['coupons']['ball_coupons']['purchased'][str(user_id)].append({
            **coupon,
            'purchased_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'price_paid': coupon_price
        })
        
        # Kuponni ro'yxatdan olib tashlash
        remove_ball_coupon(coupon)
        
        save_data(data)
        
        # Kupon ma'lumotlarini yuborish
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

💰 **Qolgan ball:** {get_user_points(user_id)}
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
        
        await query.edit_message_text(coupon_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"get_ball_coupon da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def send_today_coupons(query):
    """Bepul kuponlarni yuborish"""
    try:
        today_coupons = data['coupons']['today']
        
        if not today_coupons['active'] or not today_coupons['matches']:
            await query.edit_message_text(
                "📭 *Hozircha bepul kuponlar mavjud emas*\n\n"
                "Kuponlar tez orada yangilanadi. Iltimos, keyinroq tekshiring! 🔄",
                parse_mode='Markdown'
            )
            return
        
        coupon_text = f"🎯 *{today_coupons['description']}*\n\n"
        coupon_text += f"📅 **Sana:** {today_coupons['date']}\n\n"
        
        # Har bir bukmeker uchun kodlar
        coupon_text += "🔑 *Kupon Kodlari:*\n"
        coupon_text += f"• 1xBet: `{today_coupons['coupon_codes'].get('1xbet', 'Kod mavjud emas')}`\n"
        coupon_text += f"• MelBet: `{today_coupons['coupon_codes'].get('melbet', 'Kod mavjud emas')}`\n"
        coupon_text += f"• DB Bet: `{today_coupons['coupon_codes'].get('dbbet', 'Kod mavjud emas')}`\n\n"
        
        coupon_text += "---\n\n"
        
        # Har bir o'yin uchun alohida koeffitsient
        for i, match in enumerate(today_coupons['matches'], 1):
            coupon_text += f"*{i}. {match['time']} - {match['league']}*\n"
            coupon_text += f"🏆 `{match['teams']}`\n"
            coupon_text += f"🎯 **Bashorat:** `{match['prediction']}`\n"
            coupon_text += f"📊 **Koeffitsient:** `{match['odds']}`\n"
            coupon_text += f"💎 **Ishonch:** {match['confidence']}\n\n"
        
        # Umumiy koeffitsientni hisoblash
        total_odds = 1.0
        for match in today_coupons['matches']:
            try:
                total_odds *= float(match['odds'])
            except:
                pass
        
        # Umumiy koeffitsientni alohida qator sifatida ko'rsatish
        coupon_text += "---\n\n"
        coupon_text += f"💰 *Umumiy Koeffitsient:* `{total_odds:.2f}` 🚀\n\n"
        coupon_text += "⏰ *Eslatma:* Stavkalarni o'yin boshlanishidan oldin qo'ying!\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🎰 1xBet", url=BUKMAKER_LINKS['1xbet']),
                InlineKeyboardButton("🎯 MelBet", url=BUKMAKER_LINKS['melbet']),
                InlineKeyboardButton("💰 DB Bet", url=BUKMAKER_LINKS['dbbet'])
            ],
            [InlineKeyboardButton("💰 Ball Evaziga Kupon", callback_data="get_coupons")],
            [InlineKeyboardButton("💎 VIP Kuponlar", callback_data="premium_coupons")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(coupon_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"send_today_coupons da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_my_points(query, user_id):
    """Foydalanuvchi ballari va statistikasi"""
    try:
        user_data = data['users'].get(str(user_id), {})
        points = user_data.get('points', 0)
        referrals = user_data.get('referrals', 0)
        required_refs = data['settings']['min_referrals']
        points_per_ref = data['settings']['referral_points']
        coupon_price = data['settings']['coupon_price']
        
        text = f"""
🏆 *MENING HISOBIM*

💰 **Ballar:** {points} ball
👥 **Referallar:** {referrals} ta
🎯 **VIP uchun:** {referrals}/{required_refs} ta

📊 **Statistika:**
• 1 referal = {points_per_ref} ball
• 1 kupon = {coupon_price} ball
• VIP uchun = {required_refs} referal

"""
        
        if points >= coupon_price:
            text += f"✅ **Sotib olishingiz mumkin:** {points // coupon_price} ta kupon\n\n"
        else:
            text += f"❌ **Yetarli ball yo'q.** {coupon_price - points} ball kerak\n\n"
        
        # Ball tarixi
        points_history = user_data.get('points_history', [])
        if points_history:
            text += "📅 **So'nggi operatsiyalar:**\n"
            for history in points_history[-3:]:
                sign = "+" if history['points'] > 0 else ""
                text += f"• {sign}{history['points']} ball - {history['reason']}\n"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")],
            [InlineKeyboardButton("💎 VIP Olish", callback_data="premium_coupons")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_my_points da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_referral_link(query, user_id):
    """Referal havolasini ko'rsatish"""
    try:
        bot_username = (await query.message._bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
        referrals_count = get_user_referrals(user_id)
        required_refs = data['settings']['min_referrals']
        points_per_ref = data['settings']['referral_points']
        user_points = get_user_points(user_id)
        
        text = f"""
📤 *BAL TO'PLASH USULI*

🔗 **Sizning referal havolangiz:**
`{ref_link}`

💰 **Ball to'plash formulasi:**
• Har bir do'st = {points_per_ref} ball
• {required_refs} ta do'st = Bepul VIP

📊 **Sizning holatingiz:**
• Do'stlar: {referrals_count} ta
• Ballar: {user_points} ball
• VIP uchun: {required_refs - referrals_count} ta qolgan

💡 **Qanday ball to'plasaniz:**
1. Havolani nusxalang
2. Do'stlaringizga yuboring  
3. Har bir yangi do'st = {points_per_ref} ball
4. Ballarni kuponlarga aylantiring!

🎯 Maqsad: {required_refs} ta do'st = {(required_refs - referrals_count) * points_per_ref} ball
"""

        keyboard = [
            [InlineKeyboardButton("🔗 TELEGRAMDA ULASHISH", callback_data="share_referral")],
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_referral_link da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def share_referral_link(query, user_id):
    """Havolani ulashish"""
    try:
        bot_username = (await query.message._bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
        
        share_text = f"""🎯 *Futbol Kuponlari Boti*

⚽ Kunlik bepul kuponlar
💰 Ball evaziga ekskluziv kuponlar
💎 VIP ekskluziv bashoratlar

🎁 Har bir do'st uchun 5 ball oling va bepul kuponlar sotib oling!

Botga kirib, daromad olishni boshlang:
{ref_link}"""

        keyboard = [
            [InlineKeyboardButton("📤 TELEGRAMDA ULASHISH", url=f"https://t.me/share/url?url={ref_link}&text={share_text}")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔗 *Havolani quyidagi tugma orqali osongina ulashing:*\n\n"
            "Tugmani bosing va do'stlaringizga yuboring!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"share_referral_link da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def handle_premium_coupons(query, user_id):
    """VIP kuponlarni ko'rsatish"""
    try:
        if is_premium(user_id):
            await send_premium_coupons(query)
        else:
            await show_premium_offer(query, user_id)
    except Exception as e:
        logger.error(f"handle_premium_coupons da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_premium_offer(query, user_id):
    """VIP taklifini ko'rsatish"""
    try:
        referrals_count = get_user_referrals(user_id)
        required_refs = data['settings']['min_referrals']
        user_points = get_user_points(user_id)
        
        text = f"""
💎 *VIP KUPONLARGA KIRISH*

📊 **Sizning holatingiz:**
👥 Referallar: {referrals_count}/{required_refs} ta
💰 Ballar: {user_points} ball
💵 To'lov: {data['settings']['premium_price']} {data['settings']['currency']}

🎯 *VIP afzalliklari:*
• ✅ Yuqori daromadli kuponlar
• ✅ Ekskluziv bashoratlar  
• ✅ 90-95% ishonchlilik
• ✅ Statistik tahlillar

💡 *VIP olish usullari:*
"""
        
        keyboard = []
        
        if referrals_count >= required_refs:
            keyboard.append([InlineKeyboardButton("🎁 BEPUL VIP OCHISH", callback_data="get_free_premium")])
            text += f"1. 🎁 **{required_refs} ta referal** - Bepul VIP!\n"
        else:
            text += f"1. 👥 **{required_refs} ta referal** to'plang\n"
        
        text += f"2. 💳 **{data['settings']['premium_price']} {data['settings']['currency']}** to'lov qiling\n\n"
        text += "💎 VIP orqali yuqori daromadli kuponlarga ega bo'ling!"
        
        keyboard.extend([
            [InlineKeyboardButton("👥 Referal Orqali", callback_data="get_referral_link")],
            [InlineKeyboardButton("💳 To'lov Orqali", callback_data="buy_premium")],
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_premium_offer da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def send_premium_coupons(query):
    """VIP kuponlarni yuborish"""
    try:
        premium_coupons = data['coupons']['premium']
        
        if not premium_coupons['active'] or not premium_coupons['matches']:
            await query.edit_message_text(
                "💎 *VIP kuponlar tez orada yangilanadi!*\n\n"
                "Biz yuqori daromadli ekskluziv kuponlar ustida ishlamoqdamiz. 🔄",
                parse_mode='Markdown'
            )
            return
        
        premium_text = f"💎 *{premium_coupons['description']}*\n\n"
        premium_text += f"📅 **Sana:** {premium_coupons['date']}\n\n"
        
        # Har bir bukmeker uchun kodlar
        premium_text += "🔑 *VIP Kupon Kodlari:*\n"
        premium_text += f"• 1xBet: `{premium_coupons['coupon_codes'].get('1xbet', 'Kod mavjud emas')}`\n"
        premium_text += f"• MelBet: `{premium_coupons['coupon_codes'].get('melbet', 'Kod mavjud emas')}`\n"
        premium_text += f"• DB Bet: `{premium_coupons['coupon_codes'].get('dbbet', 'Kod mavjud emas')}`\n\n"
        
        premium_text += "---\n\n"
        
        # Har bir o'yin uchun alohida koeffitsient
        for i, match in enumerate(premium_coupons['matches'], 1):
            premium_text += f"*{i}. {match['time']} - {match['league']}*\n"
            premium_text += f"🏆 `{match['teams']}`\n"
            premium_text += f"🎯 **Bashorat:** `{match['prediction']}`\n"
            premium_text += f"📊 **Koeffitsient:** `{match['odds']}`\n"
            premium_text += f"💎 **Ishonch:** {match['confidence']}\n\n"
        
        # Umumiy koeffitsientni hisoblash
        total_odds = 1.0
        for match in premium_coupons['matches']:
            try:
                total_odds *= float(match['odds'])
            except:
                pass
        
        # Umumiy koeffitsientni alohida qator sifatida ko'rsatish
        premium_text += "---\n\n"
        premium_text += f"💰 *Umumiy Koeffitsient:* `{total_odds:.2f}` 💰\n\n"
        premium_text += "✅ *VIP a'zo bo'lganingiz uchun rahmat!*\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🎰 1xBet", url=BUKMAKER_LINKS['1xbet']),
                InlineKeyboardButton("🎯 MelBet", url=BUKMAKER_LINKS['melbet']),
                InlineKeyboardButton("💰 DB Bet", url=BUKMAKER_LINKS['dbbet'])
            ],
            [InlineKeyboardButton("🔗 Ulashish", callback_data="share_referral")],
            [InlineKeyboardButton("🎯 Boshqa Kuponlar", callback_data="get_coupons")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(premium_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"send_premium_coupons da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_help(query):
    """Yordam sahifasi"""
    try:
        text = """
ℹ️ *BOTDAN FOYDALANISH QO'LLANMASI*

⚽ *Kuponlar:*
• **Bepul kuponlar** - Kunlik yangilanadigan bepul bashoratlar
• **Ball kuponlar** - Ballaringiz evaziga ekskluziv kuponlar
• **VIP kuponlar** - Yuqori daromadli ekskluziv kuponlar

💰 *Ball Tizimi:*
• **Har referal = 5 ball**
• **1 kupon = 15 ball**
• **20 ta referal = Bepul VIP**

💎 *VIP Olish:*
• **20 ta referal** to'plang
• **100 000 so'm** to'lov qiling
• VIP kuponlarga ega bo'ling

🔗 *Referal Tizimi:*
• Do'stlaringizni taklif qiling
• Har bir referal sizga +5 ball
• 20 ta referal = Bepul VIP

📞 *Qo'llab-quvvatlash:*
Murojaatlar uchun: @baxtga_olga

🚀 *Bot har kuni yangilanadi va yangi kuponlar qo'shiladi!*
"""
        
        keyboard = [
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_help da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_panel(query):
    """Admin panelini ko'rsatish"""
    try:
        text = """
👑 *ADMIN PANELI*

🎯 **Admin imkoniyatlari:**
• 📊 Statistikalarni ko'rish
• 📢 Xabar yuborish
• 🎯 Kupon qo'shish
• ⚙️ Sozlamalarni boshqarish

🚀 *Hozircha admin paneli ishlab chiqilmoqda...*

Tez orada barcha funksiyalar qo'shiladi!
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def back_to_coupon_selection(query):
    """Kupon tanlash sahifasiga qaytish"""
    user_id = query.from_user.id
    await show_coupon_selection(query, user_id)

async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        # Soddalashtirilgan tugmalar
        keyboard = [
            [
                InlineKeyboardButton("🎯 Kuponlar Olish", callback_data="get_coupons"),
                InlineKeyboardButton("💎 VIP Kuponlar", callback_data="premium_coupons")
            ],
            [
                InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points"),
                InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("ℹ️ Yordam", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 *Asosiy Menyu*\n\n"
            "Ball to'plang, kuponlar oling va yutuqlarga erishing! 🚀",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"back_to_main da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    # Hozircha oddiy admin xabarlari
    await update.message.reply_text("👑 Admin paneli tez orada ishga tushadi!")

def main():
    """Asosiy dastur"""
    try:
        # Application yaratish
        application = Application.builder().token(TOKEN).build()
        
        # Handlerlarni qo'shish
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        
        # Botni ishga tushirish
        logger.info("Bot ishga tushmoqda...")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🤖 Bot ishlayapti...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("🎯 YANGI TIZIM: Bepul + Ball kuponlari bitta tugmada!")
        print("💰 Ball yetarli bo'lsa - kupon, yetmasa - ball to'plash")
        print("📊 Soddalashtirilgan interfeys")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()

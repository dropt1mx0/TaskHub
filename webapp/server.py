# webapp/server.py
"""
Telegram Mini App backend server.
Provides REST API + serves static frontend.
Uses the same database as the bot via shared db module.
"""
import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from urllib.parse import unquote, parse_qs

from aiohttp import web
from loguru import logger
from sqlalchemy import select, func, desc

from config import config
from database.db import db
from database.models import (
    User, Task, CompletedTask, WheelSpin, Withdrawal,
    Referral, Bank, Deposit, SubscriptionCheck
)
from database.queries import (
    UserQueries, TaskQueries, WheelQueries,
    WithdrawalQueries, ReferralQueries, CompletedTaskQueries
)
from services.wheel_service import WheelService
from utils.helpers import format_number, generate_referral_link

# ──────────────────────────── Auth helpers ────────────────────────────

def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Validate Telegram WebApp initData.
    Returns parsed user dict on success, None on failure.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = dict(pair.split("=", 1) for pair in unquote(init_data).split("&"))
        check_hash = parsed.pop("hash", None)
        if not check_hash:
            return None

        # Build data-check-string (alphabetical order)
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()
        computed = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed, check_hash):
            return None

        # Optional: check auth_date freshness (allow 24h)
        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > 86400:
            return None

        user_data = json.loads(parsed.get("user", "{}"))
        return user_data
    except Exception as e:
        logger.error(f"initData validation error: {e}")
        return None


async def get_user_from_request(request: web.Request) -> tuple[dict | None, User | None]:
    """
    Extract and validate Telegram user from the Authorization header.
    Auto-creates user if they don't exist (first Mini App visit).
    Returns (tg_user_dict, db_user) or (None, None).
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("tma "):
        return None, None

    init_data = auth[4:]
    tg_user = validate_init_data(init_data, config.BOT_TOKEN)
    if not tg_user:
        return None, None

    user_id = tg_user.get("id")
    if not user_id:
        return None, None

    async with await db.get_session() as session:
        # get_or_create: auto-register users who open the Mini App
        user = await UserQueries.get_or_create(
            session,
            user_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
            is_premium=tg_user.get("is_premium", False),
            language=tg_user.get("language_code", "ru"),
        )

    return tg_user, user


def json_response(data, status=200):
    return web.json_response(data, status=status)


def error_response(msg, status=400):
    return web.json_response({"error": msg}, status=status)


# ──────────────────────────── Middleware ───────────────────────────────

@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return resp


# ──────────────────────────── API routes ──────────────────────────────

async def api_me(request: web.Request):
    """GET /api/me - current user profile"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    async with await db.get_session() as session:
        # Referral count
        ref_result = await session.execute(
            select(func.count(Referral.id)).where(Referral.referrer_id == user.user_id)
        )
        ref_count = ref_result.scalar() or 0

    bot_me = None
    try:
        import bot as bot_module
        if bot_module.bot is not None:
            bot_me = await bot_module.bot.get_me()
    except Exception:
        pass

    return json_response({
        "user_id": user.user_id,
        "username": user.username,
        "first_name": user.first_name,
        "balance": round(user.balance, 3),
        "on_hold": round(user.on_hold, 3),
        "total_earned": round(user.total_earned, 3),
        "tasks_completed": user.tasks_completed,
        "login_streak": user.login_streak,
        "referral_count": ref_count,
        "referral_link": generate_referral_link(
            bot_me.username if bot_me else "TaskHubBot", user.user_id
        ),
        "is_premium": user.is_premium,
        "is_admin": user.user_id in config.ADMIN_IDS,
        "wallet_address": user.wallet_address,
    })


async def api_tasks(request: web.Request):
    """GET /api/tasks - available tasks"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    async with await db.get_session() as session:
        tasks = await TaskQueries.get_available_tasks(session, user.user_id)
        result = []
        for t in tasks:
            result.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "reward": round(t.reward, 3),
                "type": t.task_type,
                "channel_username": t.channel_username,
                "channel_url": t.channel_url,
                "completions": t.total_completions,
            })

    return json_response({"tasks": result})


async def api_complete_task(request: web.Request):
    """POST /api/tasks/{id}/complete"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    task_id = int(request.match_info["id"])

    async with await db.get_session() as session:
        # Get the task first to know creator and reward
        task = await TaskQueries.get_task_by_id(session, task_id)
        if not task:
            return error_response("Task not found")

        reward = await TaskQueries.complete_task(session, user.user_id, task_id)
        if reward is None:
            return error_response("Task not found or already completed")

        # Charge the task creator
        await UserQueries.update_balance(
            session, task.created_by, -reward, hold=False
        )

        # Credit the user who completed it
        await UserQueries.update_balance(
            session, user.user_id, reward, hold=False, task_completed=True
        )

        # Process referral bonuses
        await ReferralQueries.update_referral_progress(session, user.user_id, reward)

        # Refresh user
        user = await UserQueries.get_user(session, user.user_id)

    return json_response({
        "success": True,
        "reward": round(reward, 3) if isinstance(reward, (int, float)) else 0,
        "balance": round(user.balance, 3),
        "on_hold": round(user.on_hold, 3),
    })


async def api_wheel_status(request: web.Request):
    """GET /api/wheel - wheel info"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    async with await db.get_session() as session:
        can_free, hours, minutes = await WheelService.can_spin_free(session, user.user_id)
        history = await WheelService.get_spin_history(session, user.user_id, limit=5)

    return json_response({
        "can_spin_free": can_free,
        "cooldown_hours": hours or 0,
        "cooldown_minutes": minutes or 0,
        "paid_cost": config.WHEEL_PAID_COST,
        "prizes": config.WHEEL_PRIZES,
        "history": [
            {"reward": round(s.reward, 3), "is_free": s.is_free,
             "time": s.spin_time.isoformat() if s.spin_time else None}
            for s in history
        ],
    })


async def api_wheel_spin(request: web.Request):
    """POST /api/wheel/spin  body: {"is_free": true}"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    body = await request.json()
    is_free = body.get("is_free", True)

    async with await db.get_session() as session:
        if is_free:
            can_free, _, _ = await WheelService.can_spin_free(session, user.user_id)
            if not can_free:
                return error_response("Free spin not available yet")

        success, reward, err = await WheelService.spin(session, user.user_id, is_free)
        if not success:
            return error_response(err or "Spin failed")

        # Add reward to on_hold (matching bot logic)
        user_obj = await UserQueries.get_user(session, user.user_id)
        if user_obj:
            user_obj.on_hold += reward
            user_obj.total_earned += reward
            await session.commit()

        user = await UserQueries.get_user(session, user.user_id)

    return json_response({
        "success": True,
        "reward": round(reward, 3),
        "balance": round(user.balance, 3),
        "on_hold": round(user.on_hold, 3),
    })


async def api_referrals(request: web.Request):
    """GET /api/referrals"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    async with await db.get_session() as session:
        stats = await ReferralQueries.get_referral_stats(session, user.user_id)

    return json_response(stats)


async def api_leaderboard(request: web.Request):
    """GET /api/leaderboard"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    async with await db.get_session() as session:
        result = await session.execute(
            select(
                User.user_id, User.username, User.first_name,
                User.total_earned
            )
            .where(User.total_earned > 0)
            .order_by(desc(User.total_earned))
            .limit(20)
        )

        leaders = []
        for row in result:
            name = row.username or row.first_name or f"User_{row.user_id}"
            leaders.append({
                "user_id": row.user_id,
                "name": name,
                "total_earned": round(row.total_earned, 3),
            })

    return json_response({"leaders": leaders, "my_id": user.user_id})


async def api_withdraw_request(request: web.Request):
    """POST /api/withdraw  body: {"amount": 1.0, "type": "usdt", "wallet": "UQ..."}"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    body = await request.json()
    amount = float(body.get("amount", 0))
    w_type = body.get("type", "usdt")
    wallet = body.get("wallet", "").strip()

    if amount < config.MIN_WITHDRAWAL:
        return error_response(f"Minimum withdrawal is {config.MIN_WITHDRAWAL} USDT")

    if not wallet:
        return error_response("Wallet address is required")

    async with await db.get_session() as session:
        user_obj = await UserQueries.get_user(session, user.user_id)
        if not user_obj or user_obj.balance < amount:
            return error_response("Insufficient balance")

        w = await WithdrawalQueries.create_withdrawal(
            session, user.user_id, amount, w_type, wallet
        )

        user_obj = await UserQueries.get_user(session, user.user_id)

    return json_response({
        "success": True,
        "withdrawal_id": w.id if w else None,
        "balance": round(user_obj.balance, 3),
    })


async def api_history(request: web.Request):
    """GET /api/history - withdrawal history"""
    tg_user, user = await get_user_from_request(request)
    if not user:
        return error_response("Unauthorized", 401)

    async with await db.get_session() as session:
        withdrawals = await WithdrawalQueries.get_user_withdrawals(session, user.user_id)

    return json_response({
        "withdrawals": [
            {
                "id": w.id,
                "amount": round(w.amount, 3),
                "type": w.withdrawal_type,
                "status": w.status,
                "wallet": w.wallet_address,
                "requested_at": w.requested_at.isoformat() if w.requested_at else None,
                "processed_at": w.processed_at.isoformat() if w.processed_at else None,
            }
            for w in withdrawals
        ]
    })


# ──────────────────────────── Admin helpers ───────────────────────────

async def get_admin_from_request(request: web.Request) -> tuple[dict | None, User | None]:
    """Like get_user_from_request but also verifies admin status."""
    tg_user, user = await get_user_from_request(request)
    if not user or user.user_id not in config.ADMIN_IDS:
        return None, None
    return tg_user, user


# ──────────────────────────── Admin API routes ────────────────────────

async def api_admin_stats(request: web.Request):
    """GET /api/admin/stats"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    async with await db.get_session() as session:
        from database.queries import AdminQueries
        stats = await AdminQueries.get_stats(session)

    return json_response(stats)


async def api_admin_tasks(request: web.Request):
    """GET /api/admin/tasks - all tasks"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    async with await db.get_session() as session:
        tasks = await TaskQueries.get_all_tasks(session)
        result = []
        for t in tasks:
            result.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "reward": round(t.reward, 3),
                "type": t.task_type,
                "channel_username": t.channel_username,
                "is_active": t.is_active,
                "total_completions": t.total_completions,
                "created_by": t.created_by,
            })

    return json_response({"tasks": result})


async def api_admin_create_task(request: web.Request):
    """POST /api/admin/tasks - create a new task"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    body = await request.json()
    title = body.get("title", "").strip()
    description = body.get("description", "").strip()
    reward = float(body.get("reward", 0))
    channel_username = body.get("channel_username", "").strip().lstrip("@")

    if not title:
        return error_response("Title is required")
    if reward < 0.001:
        return error_response("Minimum reward is 0.001 USDT")
    if not channel_username:
        return error_response("Channel username is required")

    async with await db.get_session() as session:
        task = await TaskQueries.create_task(
            session,
            title=title,
            description=description or title,
            reward=reward,
            created_by=user.user_id,
            channel_url=f"https://t.me/{channel_username}",
            channel_username=channel_username,
            task_type="channel_subscription",
        )
        logger.info(f"Admin {user.user_id} created task #{task.id} via webapp")

    return json_response({"success": True, "task_id": task.id})


async def api_admin_toggle_task(request: web.Request):
    """POST /api/admin/tasks/{id}/toggle"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    task_id = int(request.match_info["id"])

    async with await db.get_session() as session:
        task = await TaskQueries.get_task_by_id(session, task_id)
        if not task:
            return error_response("Task not found")
        task.is_active = not task.is_active
        await session.commit()
        logger.info(f"Admin {user.user_id} toggled task #{task_id} -> {'active' if task.is_active else 'inactive'}")

    return json_response({"success": True, "is_active": task.is_active})


async def api_admin_delete_task(request: web.Request):
    """DELETE /api/admin/tasks/{id}"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    task_id = int(request.match_info["id"])

    async with await db.get_session() as session:
        success = await TaskQueries.delete_task(session, task_id)
        if not success:
            return error_response("Task not found or cannot be deleted")
        logger.info(f"Admin {user.user_id} deleted task #{task_id} via webapp")

    return json_response({"success": True})


async def api_admin_withdrawals(request: web.Request):
    """GET /api/admin/withdrawals - pending withdrawals"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    async with await db.get_session() as session:
        withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
        result = []
        for w in withdrawals:
            user_info = await UserQueries.get_user(session, w.user_id)
            result.append({
                "id": w.id,
                "user_id": w.user_id,
                "username": user_info.username if user_info else None,
                "amount": round(w.amount, 3),
                "type": w.withdrawal_type,
                "wallet": w.wallet_address,
                "requested_at": w.requested_at.isoformat() if w.requested_at else None,
            })

    return json_response({"withdrawals": result})


async def api_admin_approve_withdrawal(request: web.Request):
    """POST /api/admin/withdrawals/{id}/approve"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    w_id = int(request.match_info["id"])

    async with await db.get_session() as session:
        withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
        withdrawal = next((w for w in withdrawals if w.id == w_id), None)

        if not withdrawal:
            return error_response("Withdrawal not found")

        bank_balance = await Bank.get_balance(session)
        if bank_balance < withdrawal.amount:
            return error_response("Insufficient bank funds")

        await WithdrawalQueries.update_withdrawal_status(
            session, w_id, 'completed', processed_by=user.user_id
        )
        await Bank.withdraw_funds(session, withdrawal.amount, f"Withdrawal #{w_id}")
        logger.info(f"Admin {user.user_id} approved withdrawal #{w_id} via webapp")

    return json_response({"success": True})


async def api_admin_reject_withdrawal(request: web.Request):
    """POST /api/admin/withdrawals/{id}/reject"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    w_id = int(request.match_info["id"])

    async with await db.get_session() as session:
        withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
        withdrawal = next((w for w in withdrawals if w.id == w_id), None)

        if not withdrawal:
            return error_response("Withdrawal not found")

        # Return funds to user
        await UserQueries.update_balance(session, withdrawal.user_id, withdrawal.amount, hold=False)
        await WithdrawalQueries.update_withdrawal_status(
            session, w_id, 'failed', processed_by=user.user_id
        )
        logger.info(f"Admin {user.user_id} rejected withdrawal #{w_id} via webapp")

    return json_response({"success": True})


async def api_admin_broadcast(request: web.Request):
    """POST /api/admin/broadcast  body: {"text": "..."}"""
    _, user = await get_admin_from_request(request)
    if not user:
        return error_response("Forbidden", 403)

    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        return error_response("Message text is required")

    import asyncio

    # Get all user IDs
    async with await db.get_session() as session:
        result = await session.execute(select(User.user_id))
        user_ids = result.scalars().all()

    # Send via bot
    success_count = 0
    failed_count = 0
    try:
        import bot as bot_module
        telegram_bot = bot_module.bot
        if telegram_bot is None:
            return error_response("Bot not initialized yet")
        for uid in user_ids:
            try:
                await telegram_bot.send_message(uid, text, parse_mode='HTML')
                success_count += 1
            except Exception as send_err:
                logger.debug(f"Broadcast send failed to {uid}: {send_err}")
                failed_count += 1
            await asyncio.sleep(0.05)
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return error_response(f"Broadcast error: {str(e)}")

    logger.info(f"Admin {user.user_id} broadcast: {success_count} sent, {failed_count} failed")
    return json_response({
        "success": True,
        "success_count": success_count,
        "failed_count": failed_count,
    })


# ──────────────────────────── App factory ─────────────────────────────

def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])

    # Static files directory
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    logger.info(f"Static dir: {static_dir}, exists: {os.path.isdir(static_dir)}")

    # Health check — Cron-Job.org pings this
    async def health_handler(request):
        return web.Response(text="OK", content_type="text/plain")

    app.router.add_get("/health", health_handler)

    # Serve index.html at root
    async def index_handler(request):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return web.FileResponse(index_path)
        return web.Response(text="TaskHub Mini App — index.html not found", status=500)

    app.router.add_get("/", index_handler)

    # API routes
    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/tasks", api_tasks)
    app.router.add_post("/api/tasks/{id}/complete", api_complete_task)
    app.router.add_get("/api/wheel", api_wheel_status)
    app.router.add_post("/api/wheel/spin", api_wheel_spin)
    app.router.add_get("/api/referrals", api_referrals)
    app.router.add_get("/api/leaderboard", api_leaderboard)
    app.router.add_post("/api/withdraw", api_withdraw_request)
    app.router.add_get("/api/history", api_history)

    # Admin API routes
    app.router.add_get("/api/admin/stats", api_admin_stats)
    app.router.add_get("/api/admin/tasks", api_admin_tasks)
    app.router.add_post("/api/admin/tasks", api_admin_create_task)
    app.router.add_post("/api/admin/tasks/{id}/toggle", api_admin_toggle_task)
    app.router.add_delete("/api/admin/tasks/{id}", api_admin_delete_task)
    app.router.add_get("/api/admin/withdrawals", api_admin_withdrawals)
    app.router.add_post("/api/admin/withdrawals/{id}/approve", api_admin_approve_withdrawal)
    app.router.add_post("/api/admin/withdrawals/{id}/reject", api_admin_reject_withdrawal)
    app.router.add_post("/api/admin/broadcast", api_admin_broadcast)

    # Serve static files (HTML/CSS/JS)
    if os.path.isdir(static_dir):
        app.router.add_static("/static", static_dir)

    return app


async def start_webapp(host: str = "0.0.0.0", port: int = 8080):
    """Start the web server (call from bot.py alongside polling)."""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.success(f"Mini App server started on http://{host}:{port}")
    return runner

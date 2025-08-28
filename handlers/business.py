# handlers/business.py
import logging
from aiogram import Router
from aiogram.types import Message, InputFile
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from core import database, helpers

logger = logging.getLogger("smartx_bot.handlers.business")
router = Router()


@router.message(commands=["invoice"])
async def cmd_invoice(message: Message):
    """
    /invoice <name>|<amount>|<description>
    Example: /invoice Acme Corp|499|Logo design
    Generates a simple PDF invoice and sends to user.
    """
    args = message.get_args()
    if not args or "|" not in args:
        await message.reply("Usage: /invoice <client_name>|<amount>|<description>")
        return
    try:
        name, amount, desc = [p.strip() for p in args.split("|", 2)]
        # generate PDF in-memory
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 800, "SmartX Assistance - Invoice")
        c.setFont("Helvetica", 12)
        c.drawString(50, 770, f"Client: {name}")
        c.drawString(50, 750, f"Description: {desc}")
        c.drawString(50, 730, f"Amount: ₹{amount}")
        c.drawString(50, 700, f"Issue Date: {helpers.now_utc().strftime('%Y-%m-%d')}")
        c.showPage()
        c.save()
        buf.seek(0)
        await message.reply_document(InputFile(buf, filename="invoice.pdf"), caption="Invoice generated.")
    except Exception as e:
        logger.exception("Invoice generation failed: %s", e)
        await message.reply("Failed to generate invoice.")


def register(dp):
    dp.include_router(router)

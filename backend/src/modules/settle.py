import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.db.session import get_session_factory
from src.db.tables import Auction, Bid, Deal, Event, Item, Ledger, Slip, User, Wallet
from src.modules import audit as audit_module
from src.modules.alias import display_alias
from src.modules.journal import Journal


def _db_now(session: Session) -> datetime:
    return session.scalar(select(func.clock_timestamp()))


def _next_event_sequence(session: Session, auction_id: uuid.UUID) -> int:
    current = session.scalar(select(func.coalesce(func.max(Event.sequence), 0)).where(Event.auction_id == auction_id))
    return int(current) + 1


def _prev_event_hash(session: Session, auction_id: uuid.UUID) -> str:
    row = session.scalar(
        select(Event.event_hash).where(Event.auction_id == auction_id).order_by(Event.sequence.desc()).limit(1)
    )
    return row if row else audit_module.genesis_event_hash()


async def close_one(session: Session, journal: Journal, auction_id: uuid.UUID, hub=None) -> None:
    if journal.blocked:
        return
    if journal.pending_prepare() is not None:
        return
    existing_deal = session.scalar(select(Deal).where(Deal.auction_id == auction_id))
    if existing_deal:
        return

    settings = get_settings()
    operation_id = uuid.uuid4()

    async with journal._async_lock:
        if session.scalar(select(Deal).where(Deal.auction_id == auction_id)):
            return
        await asyncio.to_thread(
            journal.append_prepare, {"operation_id": str(operation_id), "event": {"type": "AUCTION_CLOSED"}}
        )
        try:
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            auction = session.scalar(select(Auction).where(Auction.id == auction_id).with_for_update())
            if auction is None or auction.status != "OPEN":
                session.rollback()
                await asyncio.to_thread(journal.append_abort, operation_id)
                return
            now = _db_now(session)
            if now < auction.ends_at:
                session.rollback()
                await asyncio.to_thread(journal.append_abort, operation_id)
                return

            winning_bid = session.scalar(
                select(Bid).where(Bid.auction_id == auction_id).order_by(Bid.sequence.desc()).limit(1)
            )
            wallet_user_ids: list[uuid.UUID] = []
            if winning_bid:
                wallet_user_ids.append(winning_bid.bidder_id)
                wallet_user_ids.append(auction.seller_id)
            wallet_user_ids = sorted(set(wallet_user_ids))
            wallets: dict[uuid.UUID, Wallet] = {}
            for uid in wallet_user_ids:
                w = session.scalar(select(Wallet).where(Wallet.user_id == uid).with_for_update())
                if w:
                    wallets[uid] = w

            prev_version = auction.version
            auction.version += 1
            auction.status = "CLOSED"
            auction.closed_at = now

            ledger_rows: list[dict[str, Any]] = []
            deal_id: uuid.UUID | None = None
            slip_id: uuid.UUID | None = None
            winner_id = None
            winning_bid_id = None
            amount_cents = 0

            if winning_bid:
                winner_id = winning_bid.bidder_id
                winning_bid_id = winning_bid.id
                amount_cents = winning_bid.amount_cents
                winner_wallet = wallets[winner_id]
                seller_wallet = wallets[auction.seller_id]
                winner_wallet.total_cents -= amount_cents
                winner_wallet.committed_cents -= amount_cents
                seller_wallet.total_cents += amount_cents
                deal_id = uuid.uuid4()
                session.add(
                    Deal(
                        id=deal_id,
                        auction_id=auction_id,
                        winner_id=winner_id,
                        winning_bid_id=winning_bid_id,
                        amount_cents=amount_cents,
                        closed_at=now,
                    )
                )
                session.add(
                    Ledger(
                        wallet_id=winner_wallet.id,
                        operation_id=operation_id,
                        type="SETTLEMENT_DEBIT",
                        auction_id=auction_id,
                        settlement_id=deal_id,
                        total_delta_cents=-amount_cents,
                        committed_delta_cents=-amount_cents,
                    )
                )
                session.add(
                    Ledger(
                        wallet_id=seller_wallet.id,
                        operation_id=operation_id,
                        type="SETTLEMENT_CREDIT",
                        auction_id=auction_id,
                        settlement_id=deal_id,
                        total_delta_cents=amount_cents,
                        committed_delta_cents=0,
                    )
                )
                ledger_rows = [
                    {
                        "alias": display_alias(auction_id, winner_id, "BIDDER"),
                        "committed_delta_cents": -amount_cents,
                        "total_delta_cents": -amount_cents,
                        "type": "SETTLEMENT_DEBIT",
                    },
                    {
                        "alias": display_alias(auction_id, auction.seller_id, "SELLER"),
                        "committed_delta_cents": 0,
                        "total_delta_cents": amount_cents,
                        "type": "SETTLEMENT_CREDIT",
                    },
                ]

            event_sequence = _next_event_sequence(session, auction_id)
            prev_hash = _prev_event_hash(session, auction_id)
            seller = session.get(User, auction.seller_id)
            alias = display_alias(auction_id, auction.seller_id, seller.role if seller else "SELLER")
            occurred_at = datetime.now(UTC)
            extra: dict[str, Any] = {
                "deal_id": str(deal_id) if deal_id else None,
                "ledger": ledger_rows,
                "slip_id": None,
                "slip_public": None,
                "winning_bid_id": str(winning_bid_id) if winning_bid_id else None,
                "winner_id": str(winner_id) if winner_id else None,
            }
            payload = audit_module.build_event_payload(
                deployment_id=settings.deployment_id,
                operation_id=operation_id,
                auction_id=auction_id,
                sequence=event_sequence,
                event_type="AUCTION_CLOSED",
                prev_event_hash=prev_hash,
                prev_auction_version=prev_version,
                auction_version=auction.version,
                actor_id=auction.seller_id,
                actor_alias=alias,
                occurred_at=occurred_at,
                extra=extra,
            )
            event_hash = audit_module.sign_event(payload, prev_hash)
            audit_module.persist_event(
                session,
                auction_id=auction_id,
                sequence=event_sequence,
                event_type="AUCTION_CLOSED",
                operation_id=operation_id,
                payload=payload,
                prev_hash=prev_hash,
                event_hash=event_hash,
            )

            if deal_id:
                slip_id = uuid.uuid4()
                item = session.get(Item, auction.item_id)
                meta = item.metadata_json if item else {}
                begin = meta.get("object_begin_date") if isinstance(meta, dict) else None
                snapshot = {
                    "amount": {"cents": amount_cents, "currency": "USD"},
                    "amount_cents": amount_cents,
                    "artist": item.artist if item else None,
                    "auction_id": str(auction_id),
                    "currency": "USD",
                    "display_no": auction.display_no,
                    "external_id": item.external_id if item else None,
                    "object_begin_date": begin,
                    "object_url": item.object_url if item else None,
                    "public_code": f"HZ-2026-{auction.display_no:04d}",
                    "settled_at": now.isoformat(),
                    "title": item.title if item else "Lot",
                    "winner_alias": display_alias(auction_id, winner_id, "BIDDER"),
                }
                session.add(
                    Slip(id=slip_id, settlement_id=deal_id, snapshot_json=snapshot, close_event_hash=event_hash)
                )
                payload["slip_id"] = str(slip_id)
                payload["slip_public"] = str(slip_id)

            session.commit()
            await asyncio.to_thread(journal.append_commit, operation_id)
            if hub is not None:
                from src.modules import auctions as auctions_module

                item = session.get(Item, auction.item_id)
                seller = session.get(User, auction.seller_id)
                if item and seller:
                    now = _db_now(session)
                    snap = auctions_module.auction_snapshot(session, auction, item, seller, now)
                    await hub.publish(
                        str(auction_id),
                        {
                            "auction_id": str(auction_id),
                            "server_time": snap["server_time"],
                            "snapshot": snap,
                            "type": "auction.closed",
                            "version": snap["version"],
                        },
                    )
        except Exception:
            session.rollback()
            await asyncio.to_thread(journal.append_abort, operation_id)
            raise


async def close_due_auctions(journal: Journal, hub=None) -> None:
    if journal.blocked or journal.pending_prepare() is not None:
        return
    with get_session_factory()() as session:
        now = _db_now(session)
        ids = session.scalars(select(Auction.id).where(Auction.status == "OPEN", Auction.ends_at <= now)).all()
    for aid in ids:
        with get_session_factory()() as session:
            await close_one(session, journal, aid, hub=hub)

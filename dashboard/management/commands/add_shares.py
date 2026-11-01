import logging

from django.core.management.base import BaseCommand, CommandError

from dashboard.models import Share
from dashboard.services.market_data import MarketDataError, get_shares

logger = logging.getLogger("main")


class Command(BaseCommand):
    help = "Загрузить справочник акций из Tinkoff Invest API"

    def handle(self, *args, **options):
        try:
            instruments = get_shares()
        except MarketDataError as exc:
            raise CommandError(str(exc)) from exc

        created = 0
        updated = 0
        skipped = 0
        for instrument in instruments:
            try:
                _, was_created = Share.objects.update_or_create(
                    figi=instrument.figi,
                    defaults={
                        "name": instrument.name,
                        "isin": instrument.isin,
                        "ticker": instrument.ticker,
                        "currency": instrument.currency,
                        "uid": instrument.uid,
                    },
                )
            except Exception as exc:
                skipped += 1
                logger.warning(
                    "Не удалось сохранить акцию %s: %s", instrument.figi, exc
                )
                self.stderr.write(
                    f"Пропущена акция {instrument.figi}: {exc}"
                )
                continue

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: создано {created}, обновлено {updated}, "
                f"пропущено {skipped}."
            )
        )

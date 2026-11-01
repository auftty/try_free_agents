from django.core.management.base import BaseCommand

from config.settings import TINKOFF_TOKEN, logger
from dashboard.models import Share


class Command(BaseCommand):
    help = "Загружает список акций из Tinkoff Invest API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--token",
            type=str,
            default=TINKOFF_TOKEN,
            help="Токен Tinkoff Invest API",
        )

    def handle(self, *args, **options):
        token = options["token"]
        if not token:
            self.stdout.write(self.style.ERROR("TINKOFF_TOKEN не указан"))
            return

        try:
            from tinkoff.invest import Client

            with Client(token) as client:
                shares = client.instruments.shares()
                count = 0
                for share in shares.instruments:
                    Share.objects.get_or_create(
                        figi=share.figi,
                        defaults={
                            "name": share.name,
                            "isin": share.isin,
                            "ticker": share.ticker,
                            "currency": share.currency,
                            "uid": share.uid,
                        },
                    )
                    count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Успешно загружено акций: {count}")
                )
        except Exception as e:
            logger.exception("Ошибка загрузки акций")
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))

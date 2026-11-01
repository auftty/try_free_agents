import uuid

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from dashboard.models import Share


class ShareSerializer(serializers.ModelSerializer):
    # uid отсутствовал в исходном API. Оставляем его необязательным для
    # совместимости: при создании генерируется UUID, при обновлении значение
    # сохраняется, если клиент его не передал.
    uid = serializers.CharField(
        max_length=255,
        required=False,
        validators=[UniqueValidator(queryset=Share.objects.all())],
    )

    class Meta:
        model = Share
        fields = (
            "id",
            "figi",
            "isin",
            "name",
            "ticker",
            "currency",
            "uid",
            "last_price",
            "is_trend_high",
            "updated_at",
        )
        read_only_fields = ("id", "updated_at")

    def create(self, validated_data):
        validated_data.setdefault("uid", str(uuid.uuid4()))
        return super().create(validated_data)

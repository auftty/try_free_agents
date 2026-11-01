from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import ShareModelForm
from .models import Share
from .services.graph import get_graph
from .services.price_history import (
    PERIOD_CHOICES,
    build_history_graph,
    calculate_statistics,
    get_history,
    get_period_days,
)


class ShareListView(ListView):
    """Список акций."""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]


class ShareDetailView(DetailView):
    """Детальная информация об акции с графиком."""

    model = Share
    template_name = "dashboard/detail.html"
    context_object_name = "share"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plot_div"] = get_graph(self.object)
        return context


class ShareHistoryView(DetailView):
    """История накопленных цен акции с графиком и статистикой."""

    model = Share
    template_name = "dashboard/history.html"
    context_object_name = "share"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        days = get_period_days(self.request.GET.get("days"))
        records = list(get_history(self.object, days))
        context.update(
            {
                "days": days,
                "period_choices": PERIOD_CHOICES,
                "statistics": calculate_statistics(records),
                "plot_div": build_history_graph(records, self.object),
                "recent_records": list(reversed(records[-20:])),
            }
        )
        return context


class ShareFormMixin(LoginRequiredMixin):
    """Общие настройки форм создания и редактирования акции."""

    model = Share
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareCreateView(ShareFormMixin, CreateView):
    """Добавление акции."""

    template_name = "dashboard/create.html"


class ShareUpdateView(ShareFormMixin, UpdateView):
    """Редактирование акции."""

    template_name = "dashboard/create.html"


class ShareDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление акции."""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")

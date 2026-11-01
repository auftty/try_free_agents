from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from .forms import ShareModelForm
from .models import Share
from .services.graph import get_graph
from django.contrib.auth.mixins import UserPassesTestMixin


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    """Миксин для ограничения доступа авторизованным пользователям."""

    def test_func(self):
        return self.request.user.is_authenticated

    def handle_no_permission(self):
        return redirect("dashboard:index")


class ShareListView(ListView):
    """Список акций с пагинацией."""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]


class ShareDetailView:
    """Детальная информация об акции с историческим графиком."""

    @staticmethod
    def get(request, pk):
        share = Share.objects.get(id=pk)
        plot_div = get_graph(share)
        return render(
            request,
            "dashboard/detail.html",
            {"plot_div": plot_div, "share": share},
        )


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление инструмента."""

    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Редактирование инструмента."""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление инструмента."""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")

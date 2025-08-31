import django_filters
from .models import User
from trading_bot.constants import USER_ROLES
from django.db.models import Q

class UserFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="date_joined",
        lookup_expr="gte",
        label="Date d'inscription (après ou égale, format ISO 8601)"
    )
    end_date = django_filters.DateFilter(
        field_name="date_joined",
        lookup_expr="lte",
        label="Date d'inscription (avant ou égale, format ISO 8601)"
    )
    search = django_filters.CharFilter(
        method="filter_by_search",
        label="Recherche (nom, prénom, email, phone)"
    )
    role = django_filters.ChoiceFilter(choices=USER_ROLES)
    is_verified = django_filters.BooleanFilter()

    class Meta:
        model = User
        fields = ['start_date', 'end_date', 'search', 'role', 'is_verified']

    def filter_by_search(self, queryset, name, value):
        """
        Recherche dans les champs : prénom, nom, email, phone.
        """
        return queryset.filter(
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(email__icontains=value) |
            Q(phone__icontains=value)
        )
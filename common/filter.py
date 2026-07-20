from django_filters import rest_framework as filters

class PaginationParamsFilter(filters.FilterSet):
    page = filters.NumberFilter(method='filter_page', required=False)
    per_page = filters.NumberFilter(method='filter_per_page', required=False)
    
    class Meta:
        fields = ['page', 'per_page']
    
    def filter_page(self, queryset, name, value):
        return queryset
    
    def filter_per_page(self, queryset, name, value):
        return queryset
    


class ApproveClaimParamsQuery(filters.FilterSet):
    claim_id = filters.NumberFilter(field_name='claim_id', lookup_expr='exact', required=True)
    email = filters.CharFilter(field_name='email', lookup_expr='exact', required=True)
    
    class Meta:
        fields = ['claim_id', 'email']
    

class CategorizedListingsFilter(filters.FilterSet):
    section = filters.CharFilter(field_name='section', lookup_expr='exact', required=True)
    page = filters.NumberFilter(method='filter_page', required=False)
    per_page = filters.NumberFilter(method='filter_per_page', required=False)
    
    class Meta:
        fields = ['section', 'page', 'per_page']
    
    def filter_page(self, queryset, name, value):
        return queryset
    
    def filter_per_page(self, queryset, name, value):
        return queryset
    


class PointPackagesFilter(filters.FilterSet):
    is_transaction = filters.BooleanFilter(method='filter_is_transaction', required=False)
    is_purchase = filters.BooleanFilter(method='filter_is_purchase', required=False)
    page = filters.NumberFilter(method='filter_page', required=False)
    per_page = filters.NumberFilter(method='filter_per_page', required=False)
    
    class Meta:
        fields = ['is_transaction', 'is_purchase', 'page', 'per_page']
    
    def filter_is_transaction(self, queryset, name, value):
        return queryset
    
    def filter_is_purchase(self, queryset, name, value):
        return queryset
    
    def filter_page(self, queryset, name, value):
        return queryset
    
    def filter_per_page(self, queryset, name, value):
        return queryset
    
class TokenQueryParam(filters.FilterSet):
    token = filters.NumberFilter(field_name='token', lookup_expr='exact', required=True)

    class Meta:
        fields = ['token']


class ListingsFilter(filters.FilterSet):
    filter = filters.CharFilter(field_name='filter', required=False)
    page = filters.NumberFilter(method='filter_page', required=False)
    per_page = filters.NumberFilter(method='filter_per_page', required=False)
    
    class Meta:
        fields = ['filter', 'page', 'per_page']


from django.urls import path
from . import views

urlpatterns = [
    path(
    "route-stations/",
    views.test_route_stations,
    name="test_route_stations",
    ),
    path("fuel-stations/", views.test_fuel_data, name="test_fuel_data"),
    path("geocoding/", views.test_geocoding, name="test_geocoding"),
    path("route/", views.calculate_route, name="calculate_route"),
]

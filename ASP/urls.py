from django.contrib import admin
from django.urls import re_path

from Core.lazy_dispatch import lazy_viewset
from Core.probes import root_probe
from Core.views import BaseAuthView, CurrentUserView, HealthView


urlpatterns = [
    re_path(r"^$", root_probe),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^api/login/account$", BaseAuthView.as_view({"post": "create"})),
    re_path(r"^api/currentUser$", CurrentUserView.as_view({"get": "list"})),
    re_path(r"^api/health$", HealthView.as_view({"get": "list"})),
    re_path(
        r"^api/local-dev/overview$",
        lazy_viewset("Core.localdev_views", "LocalDevOverviewView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/alerts$",
        lazy_viewset("Core.localdev_views", "LocalDevAlertsView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/alerts/(?P<pk>[^/]+)$",
        lazy_viewset("Core.localdev_views", "LocalDevAlertsView", {"get": "retrieve"}),
    ),
    re_path(
        r"^api/local-dev/assets$",
        lazy_viewset("Core.localdev_views", "LocalDevAssetsView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/assets/(?P<pk>[^/]+)$",
        lazy_viewset("Core.localdev_views", "LocalDevAssetsView", {"get": "retrieve"}),
    ),
    re_path(
        r"^api/local-dev/campaigns$",
        lazy_viewset("Core.localdev_views", "LocalDevCampaignsView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/cases$",
        lazy_viewset("Core.localdev_views", "LocalDevCasesView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/cases/(?P<pk>[^/]+)$",
        lazy_viewset("Core.localdev_views", "LocalDevCasesView", {"get": "retrieve"}),
    ),
    re_path(
        r"^api/local-dev/case-workflow$",
        lazy_viewset("Core.localdev_views", "LocalDevCaseWorkflowView", {"post": "create"}),
    ),
    re_path(
        r"^api/local-dev/playbooks$",
        lazy_viewset("Core.localdev_views", "LocalDevPlaybooksView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/playbooks/(?P<pk>[^/]+)$",
        lazy_viewset("Core.localdev_views", "LocalDevPlaybooksView", {"get": "retrieve"}),
    ),
    re_path(
        r"^api/local-dev/messages$",
        lazy_viewset("Core.localdev_views", "LocalDevMessagesView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/audit$",
        lazy_viewset("Core.localdev_views", "LocalDevAuditView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/response-jobs$",
        lazy_viewset("Core.localdev_views", "LocalDevResponseJobsView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/respond$",
        lazy_viewset("Core.localdev_views", "LocalDevResponseActionsView", {"post": "create"}),
    ),
    re_path(
        r"^api/local-dev/demo-alerts$",
        lazy_viewset("Core.localdev_views", "LocalDevDemoAlertsView", {"post": "create"}),
    ),
    re_path(
        r"^api/local-dev/fim-scan$",
        lazy_viewset("Core.localdev_views", "LocalDevFIMScanView", {"post": "create"}),
    ),
    re_path(
        r"^api/local-dev/vulnerability-scan$",
        lazy_viewset("Core.localdev_views", "LocalDevVulnerabilityScanView", {"post": "create"}),
    ),
]

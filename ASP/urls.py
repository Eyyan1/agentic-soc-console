import os

from django.contrib import admin
from django.urls import re_path

from Core.lazy_dispatch import lazy_viewset
from Core.probes import root_probe
from Core.views import BaseAuthView, CurrentUserView, HealthView


LOCAL_DEV_VIEW_MODULE = "Core.localdev_fast_views" if os.getenv("ASF_LOCAL_SIRP", "0") == "1" and os.getenv("ASF_ENABLE_BACKGROUND_SERVICES", "0") != "1" else "Core.localdev_views"


urlpatterns = [
    re_path(r"^$", root_probe),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^api/login/account$", BaseAuthView.as_view({"post": "create"})),
    re_path(r"^api/currentUser$", CurrentUserView.as_view({"get": "list"})),
    re_path(r"^api/health$", HealthView.as_view({"get": "list"})),
    re_path(
        r"^api/local-dev/overview$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevOverviewView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/alerts$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevAlertsView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/alerts/(?P<pk>[^/]+)$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevAlertsView", {"get": "retrieve"}),
    ),
    re_path(
        r"^api/local-dev/assets$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevAssetsView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/assets/(?P<pk>[^/]+)$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevAssetsView", {"get": "retrieve"}),
    ),
    re_path(
        r"^api/local-dev/campaigns$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevCampaignsView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/cases$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevCasesView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/cases/(?P<pk>[^/]+)$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevCasesView", {"get": "retrieve"}),
    ),
    re_path(
        r"^api/local-dev/case-workflow$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevCaseWorkflowView", {"post": "create"}),
    ),
    re_path(
        r"^api/local-dev/playbooks$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevPlaybooksView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/playbooks/(?P<pk>[^/]+)$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevPlaybooksView", {"get": "retrieve"}),
    ),
    re_path(
        r"^api/local-dev/messages$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevMessagesView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/audit$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevAuditView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/response-jobs$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevResponseJobsView", {"get": "list"}),
    ),
    re_path(
        r"^api/local-dev/respond$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevResponseActionsView", {"post": "create"}),
    ),
    re_path(
        r"^api/local-dev/demo-alerts$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevDemoAlertsView", {"post": "create"}),
    ),
    re_path(
        r"^api/local-dev/fim-scan$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevFIMScanView", {"post": "create"}),
    ),
    re_path(
        r"^api/local-dev/vulnerability-scan$",
        lazy_viewset(LOCAL_DEV_VIEW_MODULE, "LocalDevVulnerabilityScanView", {"post": "create"}),
    ),
]

from django.contrib import admin
from django.urls import re_path, include
from rest_framework import routers

from Core.localdev_views import (
    LocalDevAlertsView,
    LocalDevAssetsView,
    LocalDevAuditView,
    LocalDevCampaignsView,
    LocalDevCaseWorkflowView,
    LocalDevCasesView,
    LocalDevDemoAlertsView,
    LocalDevFIMScanView,
    LocalDevMessagesView,
    LocalDevOverviewView,
    LocalDevPlaybooksView,
    LocalDevResponseActionsView,
    LocalDevResponseJobsView,
    LocalDevVulnerabilityScanView,
)
from Core.probes import root_probe
from Core.views import BaseAuthView, CurrentUserView, HealthView


router = routers.DefaultRouter(trailing_slash=False)
router.register(r'api/login/account', BaseAuthView, basename="BaseAuth")
router.register(r'api/currentUser', CurrentUserView, basename="CurrentUser")
router.register(r'api/health', HealthView, basename="Health")
router.register(r'api/local-dev/overview', LocalDevOverviewView, basename="LocalDevOverview")
router.register(r'api/local-dev/alerts', LocalDevAlertsView, basename="LocalDevAlerts")
router.register(r'api/local-dev/assets', LocalDevAssetsView, basename="LocalDevAssets")
router.register(r'api/local-dev/campaigns', LocalDevCampaignsView, basename="LocalDevCampaigns")
router.register(r'api/local-dev/cases', LocalDevCasesView, basename="LocalDevCases")
router.register(r'api/local-dev/case-workflow', LocalDevCaseWorkflowView, basename="LocalDevCaseWorkflow")
router.register(r'api/local-dev/playbooks', LocalDevPlaybooksView, basename="LocalDevPlaybooks")
router.register(r'api/local-dev/messages', LocalDevMessagesView, basename="LocalDevMessages")
router.register(r'api/local-dev/audit', LocalDevAuditView, basename="LocalDevAudit")
router.register(r'api/local-dev/response-jobs', LocalDevResponseJobsView, basename="LocalDevResponseJobs")
router.register(r'api/local-dev/respond', LocalDevResponseActionsView, basename="LocalDevResponseActions")
router.register(r'api/local-dev/demo-alerts', LocalDevDemoAlertsView, basename="LocalDevDemoAlerts")
router.register(r'api/local-dev/fim-scan', LocalDevFIMScanView, basename="LocalDevFIMScan")
router.register(r'api/local-dev/vulnerability-scan', LocalDevVulnerabilityScanView, basename="LocalDevVulnerabilityScan")


urlpatterns = [
    re_path(r'^$', root_probe),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^', include(router.urls)),
]
